#!/usr/bin/env python3
"""Sync curated star list and total starred repository counts into README.md and AGENTS.md."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

USERNAME = "ridloabelian"
USER_AGENT = f"{USERNAME}-profile-sync/1.0"

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    starredRepositories { totalCount }
    lists(first: 50) {
      totalCount
      nodes {
        slug
        items { totalCount }
      }
    }
  }
}
""".strip()


def resolve_token() -> str | None:
    """Resolve a GitHub token from environment variables or the gh CLI."""
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if token:
        return token
    try:
        output = subprocess.check_output(
            ["gh", "auth", "token"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return output or None
    except (OSError, subprocess.CalledProcessError):
        return None


def fetch_via_graphql(token: str) -> tuple[int, dict[str, int]]:
    """Fetch total stars and star list counts using GitHub GraphQL API."""
    payload = json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if body.get("errors"):
        raise RuntimeError(f"GraphQL returned errors: {body['errors']}")

    user = (body.get("data") or {}).get("user")
    if not user:
        raise RuntimeError("GraphQL response missing user data")

    total_stars = int(user["starredRepositories"]["totalCount"])
    lists_data = user.get("lists") or {}
    nodes = lists_data.get("nodes") or []
    lists_by_slug = {
        node["slug"]: int(node["items"]["totalCount"])
        for node in nodes
        if node and node.get("slug")
    }
    if not lists_by_slug:
        raise RuntimeError("GraphQL returned no star lists")

    return total_stars, lists_by_slug


def fetch_via_public_fallback() -> tuple[int, dict[str, int]]:
    """Fallback to REST starred Link header and public GitHub stars HTML."""
    star_req = urllib.request.Request(
        f"https://api.github.com/users/{USERNAME}/starred?per_page=1",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(star_req, timeout=20) as resp:
        link_header = resp.headers.get("Link", "")
        raw_items = json.loads(resp.read().decode("utf-8"))

    match = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link_header)
    if match:
        total_stars = int(match.group(1))
    elif isinstance(raw_items, list):
        total_stars = len(raw_items)
    else:
        total_stars = 0

    html_req = urllib.request.Request(
        f"https://github.com/{USERNAME}?tab=stars",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(html_req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    pattern = re.compile(
        rf'href="/stars/{re.escape(USERNAME)}/lists/([a-z0-9-]+)"(?:(?!</a>).)*?(\d+)\s+repositories',
        re.DOTALL,
    )
    lists_by_slug = {slug: int(count) for slug, count in pattern.findall(html)}
    return total_stars, lists_by_slug


def fetch_star_stats() -> tuple[int, dict[str, int]]:
    """Fetch star counts via GraphQL first, falling back to public REST + HTML."""
    token = resolve_token()
    if token:
        try:
            return fetch_via_graphql(token)
        except (urllib.error.URLError, RuntimeError, KeyError, ValueError) as exc:
            print(f"GraphQL fetch failed ({exc}); using public fallback.", file=sys.stderr)

    return fetch_via_public_fallback()


def replace_required(text: str, pattern: str, replacement: str, label: str) -> str:
    """Apply a regex replacement and fail loudly if the target marker was not found."""
    updated, count = re.subn(pattern, replacement, text)
    if count == 0:
        raise RuntimeError(f"Expected pattern not found while updating {label}: {pattern}")
    return updated


def update_readme(readme_path: Path, total_stars: int, lists_by_slug: dict[str, int]) -> bool:
    """Update star counts in README.md and return True if the file changed."""
    original = readme_path.read_text(encoding="utf-8")
    list_count = len(lists_by_slug)
    categorized_total = sum(lists_by_slug.values())
    stars_comma = f"{total_stars:,}"
    stars_badge = stars_comma.replace(",", "%2C")
    cat_comma = f"{categorized_total:,}"

    updated = original
    updated = replace_required(
        updated,
        r"(https://img\.shields\.io/badge/Star_Lists-)\d+(_Lists_%C2%B7_)(?:[0-9]|%2C|,)+(%E2%98%85-d97706)",
        rf"\g<1>{list_count}\g<2>{stars_badge}\g<3>",
        "README header Star Lists badge",
    )
    updated = replace_required(
        updated,
        rf"\[\d+ Star Lists \([0-9,]+★\)\]\(https://github\.com/{re.escape(USERNAME)}\?tab=stars\)",
        f"[{list_count} Star Lists ({stars_comma}★)](https://github.com/{USERNAME}?tab=stars)",
        "README About Me Star Lists link",
    )
    updated = replace_required(
        updated,
        rf"\*\*\[\d+ Curated Star Lists \([0-9,]+ Categorized · [0-9,]+ Total Starred Repositories\)\]\(https://github\.com/{re.escape(USERNAME)}\?tab=stars\)\*\*",
        f"**[{list_count} Curated Star Lists ({cat_comma} Categorized · {stars_comma} Total Starred Repositories)](https://github.com/{USERNAME}?tab=stars)**",
        "README Curated Research summary",
    )

    for slug, count in lists_by_slug.items():
        list_pattern = rf"(\(https://github\.com/stars/{re.escape(USERNAME)}/lists/{re.escape(slug)}\)\s*\|\s*`)\d+(`\s*\|)"
        updated, _ = re.subn(list_pattern, rf"\g<1>{count}\g<2>", updated)

    if updated != original:
        readme_path.write_text(updated, encoding="utf-8")
        return True
    return False


def update_agents_md(agents_path: Path, total_stars: int, lists_by_slug: dict[str, int]) -> bool:
    """Update star counts in AGENTS.md and return True if the file changed."""
    original = agents_path.read_text(encoding="utf-8")
    list_count = len(lists_by_slug)
    categorized_total = sum(lists_by_slug.values())
    stars_comma = f"{total_stars:,}"
    cat_comma = f"{categorized_total:,}"

    updated = replace_required(
        original,
        r"\(\d+ lists / [0-9,]+ categorized / [0-9,]+ total starred repos",
        f"({list_count} lists / {cat_comma} categorized / {stars_comma} total starred repos",
        "AGENTS.md Curated Star Lists summary",
    )

    if updated != original:
        agents_path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    readme_path = repo_root / "README.md"
    agents_path = repo_root / "AGENTS.md"

    total_stars, lists_by_slug = fetch_star_stats()
    list_count = len(lists_by_slug)
    categorized_total = sum(lists_by_slug.values())

    if total_stars <= 0 or list_count == 0:
        print(
            f"Sanity check failed: total_stars={total_stars}, list_count={list_count}",
            file=sys.stderr,
        )
        return 1

    changed_files: list[str] = []
    if update_readme(readme_path, total_stars, lists_by_slug):
        changed_files.append("README.md")
    if agents_path.exists() and update_agents_md(agents_path, total_stars, lists_by_slug):
        changed_files.append("AGENTS.md")

    print(
        f"Fetched star stats: total_stars={total_stars}, "
        f"list_count={list_count}, categorized_total={categorized_total}"
    )
    if changed_files:
        print(f"Updated files: {', '.join(changed_files)}")
    else:
        print("No file changes needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
