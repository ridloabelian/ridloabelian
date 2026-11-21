#!/usr/bin/env python3
"""Categorize uncategorized GitHub starred repositories into ridloabelian's 12 Star Lists."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
USER_AGENT = "ridloabelian-star-categorizer/1.0"
BATCH_SIZE = 25

LIST_DESCRIPTIONS: dict[str, str] = {
    "ai-agents-coding-assistants": "Agentic coding, Antigravity, Claude Code, MCP servers, Hermes, OpenCode, virtual agent offices & skill registries",
    "llms-local-inference-rag": "Local LLM engines (llama.cpp, MLX, Ollama, OpenVINO), Jev/System-1 decision models, AI gateways & vector/graph RAG",
    "creative-multimodal-ai": "AI video & motion graphics skills (Remotion, HyperFrames, GSAP), Whisper/TTS dubbing, 3D/Blender & pure-Rust creative apps",
    "business-fintech-career": "Quant & IDX/crypto trading bots, open-source CRM/billing/ERP (Odoo, Twenty, Hyperswitch), WhatsApp Cloud & career ops",
    "cybersecurity-osint-red-team": "Autonomous pentesting & bug-hunting agents, AI skill/code security scanners, OSINT engines, Nuclei & red-team payloads",
    "devops-cloud-self-hosted": "Cloudflare Workers/D1/R2 edge apps, Docker & PaaS (Dokploy, Arcane), observability, mail servers & self-hosted homelabs",
    "awesome-lists-resources": "Curated developer directories, engineering roadmaps, system design handbooks, free LLM/cloud tiers & open-source books",
    "automation-bots-growth": "AI browser automation (Skyvern, Stagehand, Playwright), multi-channel publishing, growth/ads intelligence & web scrapers",
    "os-utilities-macos-mobile": "macOS utilities & launchers, Android cloud/remote control (scrcpy, redroid), computer-use sandboxes & cross-device tools",
    "modern-web-dev-ui-design": "Modern React/Next.js SaaS stacks, AI UI builders, Three.js/WebGL renderers, animation engines & design systems",
    "devtools-cli-terminal": "High-performance editors (Zed), Git & codebase search (tgrep), database/API clients, developer environments & CLI tools",
    "data-science-ml-foundations": "Data manipulation libraries, statistical computing, mathematical modeling, GPU training orchestration & ML foundations",
}

OVERRIDES: dict[str, str] = {
    "EnriqueKhai/JaneStreetETC22": "business-fintech-career",
    "Aran404/SpotAPI": "automation-bots-growth",
    "ViceVerse-cz/Serein": "os-utilities-macos-mobile",
    "Tracer-Cloud/opensre": "devops-cloud-self-hosted",
    "XiaoYouChR/Ghost-Downloader-3": "os-utilities-macos-mobile",
    "thareekanvar/replyloom": "business-fintech-career",
    "hieunc229/mailflare": "devops-cloud-self-hosted",
    "gylive/google-ultra": "automation-bots-growth",
    "mmdoctor/google-pro-helper": "automation-bots-growth",
    "tradingview/lightweight-charts": "business-fintech-career",
    "hrydgard/ppsspp": "os-utilities-macos-mobile",
    "gmkurtzer/ginux": "os-utilities-macos-mobile",
    "nodejs/node": "devtools-cli-terminal",
    "we-promise/sure": "business-fintech-career",
    "boykopovar/AnyPS5": "os-utilities-macos-mobile",
    "anefzaoui/misterdownloadmanager": "os-utilities-macos-mobile",
    "remoteintech/remote-jobs": "business-fintech-career",
    "Jakeschincariol/founder-skill": "business-fintech-career",
    "siddharthvaddem/openscreen": "creative-multimodal-ai",
    "CapSoftware/Cap": "creative-multimodal-ai",
    "InukaAsith/TwinDesk": "os-utilities-macos-mobile",
    "getfider/fider": "business-fintech-career",
    "freescout-help-desk/freescout": "business-fintech-career",
    "growthbook/growthbook": "business-fintech-career",
    "solidtime-io/solidtime": "business-fintech-career",
    "teableio/teable": "business-fintech-career",
    "juspay/hyperswitch": "business-fintech-career",
    "ellite/Wallos": "business-fintech-career",
    "akaunting/akaunting": "business-fintech-career",
    "kortix-ai/CompanyOS": "business-fintech-career",
    "dittofeed/dittofeed": "business-fintech-career",
    "dubinc/dub.link": "business-fintech-career",
    "keygen-sh/keygen-api": "business-fintech-career",
    "getlago/lago": "business-fintech-career",
    "ridloabelian/awesome-one-person-company": "awesome-lists-resources",
    "formbricks/formbricks": "business-fintech-career",
    "umami-software/umami": "devops-cloud-self-hosted",
    "invoiceninja/invoiceninja": "business-fintech-career",
    "polarsource/polar": "business-fintech-career",
    "documenso/documenso": "business-fintech-career",
    "twentyhq/twenty": "business-fintech-career",
    "net-merge/net-merge": "os-utilities-macos-mobile",
    "lbjlaq/Antigravity-Manager": "ai-agents-coding-assistants",
    "TaobotX11/nusacoin": "business-fintech-career",
    "bitcoin/bitcoin": "business-fintech-career",
    "raymondchins/Bridgeplay": "os-utilities-macos-mobile",
    "pierpaolo28/Awesome-FDE-Roadmap": "awesome-lists-resources",
    "Jakeschincariol/day-trader-skill": "business-fintech-career",
    "raymondchins/tokengratis-id": "awesome-lists-resources",
    "shiyu-coder/Kronos": "business-fintech-career",
    "0xrsydn/idx-cli": "business-fintech-career",
    "google-research/harness2": "ai-agents-coding-assistants",
    "12britz/awesome-free-models": "awesome-lists-resources",
    "nejib1/Free-LLM": "awesome-lists-resources",
    "open-free-llm-api/awesome-freellm-apis": "awesome-lists-resources",
    "iamlukethedev/Claw3D": "modern-web-dev-ui-design",
    "freqtrade/freqtrade": "business-fintech-career",
    "hugoguerrap/crypto-claude-desk": "business-fintech-career",
    "coinpaprika/dexpaprika-mcp": "business-fintech-career",
    "hirotomasato/dramsi": "creative-multimodal-ai",
    "hirotomasato/openlab": "automation-bots-growth",
    "hirotomasato/qoder-creator": "automation-bots-growth",
    "hirotomasato/pelerproxy": "automation-bots-growth",
    "hirotomasato/autoclawpi": "llms-local-inference-rag",
    "hirotomasato/harbor": "automation-bots-growth",
    "hirotomasato/unifarm": "automation-bots-growth",
    "hirotomasato/msplayiptv": "automation-bots-growth",
    "hirotomasato/sportku": "automation-bots-growth",
    "hirotomasato/Qwenpi": "llms-local-inference-rag",
    "hirotomasato/duckapi": "llms-local-inference-rag",
    "hirotomasato/scbz": "business-fintech-career",
    "hirotomasato/hiroto": "ai-agents-coding-assistants",
    "hirotomasato/yowes": "ai-agents-coding-assistants",
    "storytold/craft-repo-status-app": "devtools-cli-terminal",
    "storytold/craft-libs": "devtools-cli-terminal",
    "storytold/craft-launcher": "os-utilities-macos-mobile",
    "storytold/craft-fonts": "creative-multimodal-ai",
    "storytold/artcraft-services": "modern-web-dev-ui-design",
    "storytold/gridcraft": "business-fintech-career",
    "storytold/wordcraft": "os-utilities-macos-mobile",
    "storytold/pdfcraft": "os-utilities-macos-mobile",
    "storytold/deckcraft": "creative-multimodal-ai",
    "storytold/cadcraft": "creative-multimodal-ai",
    "rvdleun/onoffice": "modern-web-dev-ui-design",
    "mrzh7/scam-with-your-friends-web": "modern-web-dev-ui-design",
    "NandhaKishorM/vegaml": "data-science-ml-foundations",
    "robbietilton/Compositor": "creative-multimodal-ai",
    "wuzzstoreservice/muse-proxy": "llms-local-inference-rag",
    "Mathieu2301/TradingView-API": "business-fintech-career",
    "amirsohail100/Market-Economic-Predictor-App": "business-fintech-career",
    "snowfluke/sentimeter": "business-fintech-career",
    "snowfluke/paperium": "business-fintech-career",
    "NeaByteLab/IDX-API": "business-fintech-career",
    "FutureisinPast/antigravity-conversation-fix": "ai-agents-coding-assistants",
    "fulldiagnose/antigravity-fixer": "ai-agents-coding-assistants",
    "gokapso/whatsapp-spend-tracker": "business-fintech-career",
    "gokapso/whatsapp-broadcasts-example": "automation-bots-growth",
    "gokapso/whatsapp-cloud-api-js": "business-fintech-career",
    "gokapso/whatsapp-cloud-inbox": "business-fintech-career",
    "gokapso/flowso": "devtools-cli-terminal",
    "gokapso/kapso-workflows": "automation-bots-growth",
    "gokapso/chat": "devtools-cli-terminal",
    "gokapso/chat-sdk-adapter": "devtools-cli-terminal",
    "Decentralised-AI/CL4R1T4S-SYSTEM-PROMPT-TRANSPARENCY-FOR-ALL": "llms-local-inference-rag",
    "jimmylpx/telemarketbot": "business-fintech-career",
    "aurora-develop/Duck2api": "llms-local-inference-rag",
    "aurorax-neo/chat2api": "llms-local-inference-rag",
    "lanqian528/chat2api": "llms-local-inference-rag",
    "liuw1535/antigravity2api-nodejs": "llms-local-inference-rag",
    "znlsl/Antigravity2Api": "llms-local-inference-rag",
    "Quorinex/Freebuff2API": "llms-local-inference-rag",
    "vinnylarouge/jevlike": "llms-local-inference-rag",
    "pablostanley/yoinks": "creative-multimodal-ai",
    "ashemag/human-atlas": "modern-web-dev-ui-design",
    "anthropics/financial-services": "business-fintech-career",
    "paperless-ngx/paperless-ngx": "devops-cloud-self-hosted",
    "higgsfield-ai/higgsfield": "data-science-ml-foundations",
    "Open-Dev-Society/OpenStock": "business-fintech-career",
    "melgarafael/DeskcommCRM": "business-fintech-career",
    "rafiindistira/Atria-bot": "automation-bots-growth",
    "zahirnurdin1/atriagen": "automation-bots-growth",
    "herliansyah/9router-auto-free": "automation-bots-growth",
    "permissionlesstech/bitchat": "os-utilities-macos-mobile",
    "genspark-ai/genoffice": "business-fintech-career",
    "ente/ente": "devops-cloud-self-hosted",
    "gorhill/uBlock": "cybersecurity-osint-red-team",
    "jihe520/MathModelAgent": "data-science-ml-foundations",
    "p1neappleXpress/OpenFlux": "cybersecurity-osint-red-team",
    "AppFlowy-IO/AppFlowy": "business-fintech-career",
    "TryGhost/Ghost": "modern-web-dev-ui-design",
    "calcom/cal.diy": "business-fintech-career",
    "papermark/papermark": "business-fintech-career",
    "reactive-resume/reactive-resume": "business-fintech-career",
    "ZhuLinsen/daily_stock_analysis": "business-fintech-career",
    "virattt/ai-hedge-fund": "business-fintech-career",
    "Suwayomi/Suwayomi-Server": "os-utilities-macos-mobile",
    "imputnet/cobalt": "creative-multimodal-ai",
    "iptv-org/iptv": "awesome-lists-resources",
    "freeCodeCamp/freeCodeCamp": "awesome-lists-resources",
    "EbookFoundation/free-programming-books": "awesome-lists-resources",
    "nilbuild/developer-roadmap": "awesome-lists-resources",
    "cporter202/apis-that-find-your-next-clients": "awesome-lists-resources",
    "Anil-matcha/awesome-muse-connectors": "awesome-lists-resources",
    "frankxai/awesome-motion-design-agent-skills": "awesome-lists-resources",
    "reacher-z/Awesome-REA": "cybersecurity-osint-red-team",
    "aicodeking/leanrea": "cybersecurity-osint-red-team",
    "morluto/rea": "cybersecurity-osint-red-team",
    "LaurieWired/GhidraMCP": "cybersecurity-osint-red-team",
    "MG1937/ASC": "cybersecurity-osint-red-team",
    "openRin/Rin": "devops-cloud-self-hosted",
    "miantiao-me/Sink": "devops-cloud-self-hosted",
    "modelcontextprotocol/servers": "ai-agents-coding-assistants",
}


def resolve_token() -> str:
    """Resolve a GitHub token with user list scopes from env or gh CLI."""
    token = (os.environ.get("STAR_LISTS_PAT") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if token:
        return token
    try:
        output = subprocess.check_output(
            ["gh", "auth", "token"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if output:
            return output
    except (OSError, subprocess.CalledProcessError):
        pass
    raise RuntimeError("No GitHub token available via STAR_LISTS_PAT, GITHUB_TOKEN, GH_TOKEN, or gh auth token.")


def graphql(token: str, query: str, variables: dict | None = None) -> dict:
    """Execute a GitHub GraphQL request with retries on transient 5xx/network errors."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    for attempt in range(3):
        req = urllib.request.Request(
            GRAPHQL_ENDPOINT,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in (429, 502, 503, 504) and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"GraphQL HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"GraphQL network error: {exc}") from exc

    if body.get("errors"):
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]


def fetch_lists_and_memberships(token: str) -> tuple[dict[str, dict], dict[str, list[str]]]:
    """Fetch all viewer UserLists and paginate each list's items sequentially."""
    lists_query = """
    query {
      viewer {
        lists(first: 50) {
          nodes {
            id
            name
            slug
            description
            items { totalCount }
          }
        }
      }
    }
    """
    items_query = """
    query($listId: ID!, $cursor: String) {
      node(id: $listId) {
        ... on UserList {
          items(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes { ... on Repository { id nameWithOwner } }
          }
        }
      }
    }
    """
    data = graphql(token, lists_query)
    lists_by_slug: dict[str, dict] = {}
    repo_list_ids: dict[str, list[str]] = defaultdict(list)

    for lst in data["viewer"]["lists"]["nodes"]:
        if not lst:
            continue
        slug = lst["slug"]
        total_count = int(lst["items"]["totalCount"])
        lists_by_slug[slug] = {
            "id": lst["id"],
            "name": lst["name"],
            "slug": slug,
            "description": lst.get("description") or "",
            "totalCount": total_count,
        }
        if total_count == 0:
            continue

        cursor: str | None = None
        while True:
            page = graphql(token, items_query, {"listId": lst["id"], "cursor": cursor})["node"]["items"]
            for repo in page["nodes"]:
                if repo and "nameWithOwner" in repo:
                    repo_list_ids[repo["nameWithOwner"]].append(lst["id"])
            page_info = page["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

    return lists_by_slug, dict(repo_list_ids)


def fetch_starred_repos(token: str) -> list[dict]:
    """Fetch all starred repositories for the authenticated viewer."""
    query = """
    query($cursor: String) {
      viewer {
        starredRepositories(first: 100, after: $cursor, orderBy: {field: STARRED_AT, direction: DESC}) {
          totalCount
          pageInfo { hasNextPage endCursor }
          edges {
            node {
              id
              nameWithOwner
              description
              primaryLanguage { name }
              repositoryTopics(first: 12) { nodes { topic { name } } }
            }
          }
        }
      }
    }
    """
    repos: list[dict] = []
    cursor: str | None = None
    while True:
        conn = graphql(token, query, {"cursor": cursor})["viewer"]["starredRepositories"]
        for edge in conn["edges"]:
            node = edge["node"]
            repos.append({
                "id": node["id"],
                "repo": node["nameWithOwner"],
                "lang": (node.get("primaryLanguage") or {}).get("name") or "",
                "topics": [t["topic"]["name"].lower() for t in node["repositoryTopics"]["nodes"]],
                "desc": (node.get("description") or "").replace("\n", " ").strip(),
            })
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
    return repos


def classify_repo(repo_info: dict) -> str:
    """Deterministically map a repository to one of the 12 Star List slugs."""
    repo = repo_info["repo"]
    if repo in OVERRIDES:
        return OVERRIDES[repo]

    blob = f"{repo} {' '.join(repo_info['topics'])} {repo_info['desc']}".lower()

    if any(k in blob for k in [
        "pentest", "penetration", "osint", "darkweb", "red-team", "red team", "bug-bounty", "bugbounty",
        "bug hunting", "bughunter", "jailbreak", "vulnerability", "nuclei", "wazuh", "gitleaks",
        "mitmproxy", "port scanner", "rustscan", "rubber ducky", "badusb", "hacking", "ai-cybersecurity",
        "skillspector", "codex-security", "security-audit", "threat modeling", "blue defense", "adversarial-ai",
        "curl-impersonate",
    ]):
        return "cybersecurity-osint-red-team"

    if any(k in blob for k in [
        "video", "short-drama", "film", "ffmpeg", "whisper", "tts", "speech-to-text", "text-to-speech",
        "subtitle", "dubbing", "voice ai", "vibevoice", "voiceover", "sound effects", "sound-design",
        "motion-design", "motion-graphics", "motion design", "motion graphics", "remotion", "hyperframes",
        "lottie", "gsap", "explainer", "comfyui", "veo", "seedance", "sora", "opentoonz", "photogimp",
        "photo editor", "photocraft", "lightcraft", "filmcraft", "vectorcraft", "effectcraft", "designcraft",
        "soundcraft", "artcraft", "blender", "gallery-dl", "youtube-to-markdown", "pipecat",
    ]):
        return "creative-multimodal-ai"

    if any(k in blob for k in [
        "trading", "stock", "ihsg", "idx", "fintech", "crypto", "defi", "bitcoin", "billing", "invoice",
        "accounting", "crm", "odoo", "job-search", "job application", "career", "paid-media", "meta-ads",
        "facebook-ads", "google-ads", "claude-ads", "marketing-skills", "claude-seo",
    ]):
        return "business-fintech-career"

    if re.search(r"\bawesome[- ]", blob) or any(k in blob for k in ["cheat-sheet", "roadmap", "free-programming-books"]):
        if "agentic-awesome-skills" not in repo:
            return "awesome-lists-resources"

    if any(k in blob for k in [
        "macos", "android", "scrcpy", "redroid", "termux", "ios", "launcher", "homebrew", "virtualization",
        "titanium-browser", "tinycast", "codenotch", "mobile-mcp", "opendroid", "hermes-mobile", "ares (",
        "mobile-agent", "android_world",
    ]):
        return "os-utilities-macos-mobile"

    if any(k in blob for k in [
        "docker", "kubernetes", "self-hosted", "homelab", "cloudflare-workers", "cloudflare-pages",
        "cloudflare_temp_email", "edgetunnel", "vless", "trojan", "uptime", "status-page", "beszel",
        "dokploy", "mail-server", "postal", "listmonk", "archivebox", "archivy", "searxng", "startpage",
        "gethomepage", "kong", "leapp", "dagu", "codespaces-hermes-server",
    ]) and not any(k in blob for k in [
        "hermes-agent", "open-webui", "langfuse", "supermemory", "classifier-dev", "amrouter",
        "vertex2openai", "chatgpt-telegram-workers",
    ]):
        return "devops-cloud-self-hosted"

    if any(k in blob for k in [
        "scraper", "scraping", "crawlee", "scrapy", "autoscraper", "mediacrawler", "rsshub",
        "social media scheduler", "social-media-automation", "postiz", "autosocial", "maitian",
        "reverse-engineer-marketing", "auto-gmail", "changedetection", "unlisted youtube",
        "invisible playwright", "skyvern", "stagehand", "chatgpt-telegram-workers", "antigravity-cli-telegram",
    ]):
        return "automation-bots-growth"

    if any(k in blob for k in [
        "llama.cpp", "llamacpp", "mlx", "openvino", "gpt4all", "localai", "textgen", "open-webui",
        "janhq/jan", "exo-explore", "lightrag", "pageindex", "qanything", "rag", "vector-search",
        "jev", "typed-decision", "typed decision", "decision-model", "decision model", "system-one", "system one",
        "system 1", "llm gateway", "ai gateway", "new-api", "amrouter", "clawrouter", "vertex2openai", "muse2api",
        "gpt4free", "python-genai", "gemini-api", "chat-demo", "rig", "mem0", "supermemory", "headroom",
        "docling", "llm_wiki", "libretranslate", "langfuse", "classifier-dev", "opencodex", "n9router",
    ]):
        return "llms-local-inference-rag"

    if any(k in blob for k in ["pandas", "statistics", "mathematical", "machine-learning", "data-science"]):
        return "data-science-ml-foundations"

    if any(k in blob for k in [
        "threejs", "three.js", "react-three", "design-system", "astryx", "magicui", "fumadocs",
        "headless-cms", "directus", "payload", "saas-boilerplate", "open-saas", "react-email",
        "onlook", "dyad", "m3e-canvas", "anime", "scroll-craft", "motiondivision/motion", "copilotkit",
    ]):
        return "modern-web-dev-ui-design"

    if any(k in blob for k in [
        "zed-industries/zed", "tgrep", "dbx", "jsoncrack", "gitdiagram", "openreplay", "coder/coder",
        "better-auth", "trailbase", "larksuite/cli", "nango",
    ]):
        return "devtools-cli-terminal"

    if any(k in blob for k in [
        "agent", "claude", "codex", "antigravity", "mcp", "opencode", "hermes", "skill", "aichat",
        "forgecode", "cline", "aider", "autogpt", "langchain", "letta", "khoj", "botmux",
        "windmill", "treg", "humanizer", "impeccable", "craft-anything", "cua",
    ]):
        return "ai-agents-coding-assistants"

    lang = repo_info["lang"]
    if lang in ("Python", "Jupyter Notebook"):
        return "data-science-ml-foundations"
    if lang in ("TypeScript", "JavaScript", "CSS", "HTML", "Svelte", "Vue"):
        return "modern-web-dev-ui-design"
    if lang in ("Swift", "Kotlin", "Dart"):
        return "os-utilities-macos-mobile"
    if lang in ("Go", "Shell", "Dockerfile"):
        return "devops-cloud-self-hosted"
    return "devtools-cli-terminal"


def apply_list_assignments(
    token: str,
    assignments: list[tuple[dict, str, list[str]]],
    lists_by_slug: dict[str, dict],
) -> int:
    """Assign uncategorized repositories to their target Star Lists in GraphQL batches."""
    applied = 0
    for start in range(0, len(assignments), BATCH_SIZE):
        batch = assignments[start : start + BATCH_SIZE]
        var_defs = []
        mutations = []
        variables: dict[str, object] = {}

        for idx, (repo_info, target_slug, existing_ids) in enumerate(batch):
            assert not existing_ids, f"Refusing to overwrite existing list memberships on {repo_info['repo']}"
            target_id = lists_by_slug[target_slug]["id"]
            new_list_ids = list(dict.fromkeys([*existing_ids, target_id]))
            var_name = f"input{idx}"
            var_defs.append(f"${var_name}: UpdateUserListsForItemInput!")
            mutations.append(
                f"m{idx}: updateUserListsForItem(input: ${var_name}) {{ item {{ ... on Repository {{ nameWithOwner }} }} }}"
            )
            variables[var_name] = {
                "itemId": repo_info["id"],
                "listIds": new_list_ids,
            }

        query = f"mutation({', '.join(var_defs)}) {{ {' '.join(mutations)} }}"
        graphql(token, query, variables)
        applied += len(batch)
        print(f"Applied batch {start // BATCH_SIZE + 1}: {applied}/{len(assignments)} repositories categorized.")
        if start + BATCH_SIZE < len(assignments):
            time.sleep(0.25)

    return applied


def update_list_descriptions(token: str, lists_by_slug: dict[str, dict]) -> int:
    """Update Star List descriptions via GraphQL updateUserList where changed."""
    updated = 0
    for slug, desired_desc in LIST_DESCRIPTIONS.items():
        if slug not in lists_by_slug:
            raise RuntimeError(f"Expected Star List slug missing on GitHub: {slug}")
        if len(desired_desc) > 160:
            raise RuntimeError(f"Description for {slug} exceeds 160 chars ({len(desired_desc)})")
        lst = lists_by_slug[slug]
        if lst["description"] == desired_desc:
            continue
        mutation = """
        mutation($input: UpdateUserListInput!) {
          updateUserList(input: $input) {
            list { slug description }
          }
        }
        """
        graphql(token, mutation, {"input": {"listId": lst["id"], "description": desired_desc}})
        updated += 1
        print(f"Updated description for {slug}")
        time.sleep(0.15)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Categorize uncategorized GitHub starred repositories.")
    parser.add_argument("--dry-run", action="store_true", help="Preview categorization counts without mutating GitHub.")
    parser.add_argument("--apply", action="store_true", help="Assign uncategorized starred repositories into Star Lists.")
    parser.add_argument(
        "--update-descriptions",
        action="store_true",
        help="Update descriptions on the 12 Star Lists to clean English summaries.",
    )
    args = parser.parse_args()

    token = resolve_token()
    lists_by_slug, repo_list_ids = fetch_lists_and_memberships(token)
    starred = fetch_starred_repos(token)

    uncategorized = [r for r in starred if not repo_list_ids.get(r["repo"])]
    assignments: list[tuple[dict, str, list[str]]] = []
    additions_by_slug: dict[str, int] = defaultdict(int)

    for repo_info in uncategorized:
        target_slug = classify_repo(repo_info)
        if target_slug not in lists_by_slug:
            raise RuntimeError(f"Target Star List slug '{target_slug}' not found for {repo_info['repo']}")
        assignments.append((repo_info, target_slug, repo_list_ids.get(repo_info["repo"], [])))
        additions_by_slug[target_slug] += 1

    print(f"Total starred: {len(starred)} | Already categorized: {len(starred) - len(uncategorized)} | Uncategorized: {len(uncategorized)}")
    print("Per-list projection (existing + new = final):")
    for slug in sorted(lists_by_slug, key=lambda s: -(lists_by_slug[s]["totalCount"] + additions_by_slug[s])):
        existing = lists_by_slug[slug]["totalCount"]
        added = additions_by_slug[slug]
        print(f"  {slug:32s} {existing:3d} + {added:3d} = {existing + added:3d}")

    if not args.apply and not args.update_descriptions:
        print("Dry-run complete (no mutations performed).")
        return 0

    if args.apply and assignments:
        apply_list_assignments(token, assignments, lists_by_slug)
    elif args.apply:
        print("No uncategorized repositories to assign.")

    if args.update_descriptions:
        desc_count = update_list_descriptions(token, lists_by_slug)
        print(f"List descriptions updated: {desc_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
