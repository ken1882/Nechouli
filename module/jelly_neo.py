# frozen_string_literal: true
import os
import re
import json
import base64
import hashlib
from datetime import datetime
from threading import Thread
from time import sleep, time
from urllib.parse import quote
from http.cookies import SimpleCookie

import requests
from bs4 import BeautifulSoup as BS
from module.base.utils import str2int
from module.config.utils import deep_get
from module.db import data_manager as dm
from module.logger import logger

from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────  Env / constants  ──────────────────────────────
HTTP_HEADERS = {
    "Host": "itemdb.com.br",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) "
        "Gecko/20100101 Firefox/152.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,zh-TW;q=0.9,ja;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://itemdb.com.br/search",
    "X-itemdb-Proof": os.getenv("ITEMDB_PROOF", ""),
    "X-Requested-With": "itemdb-web",
    "sentry-trace": "5230530c415b480091a5b0d48bba1142-a74f027ea5545e53-0",
    "baggage": "sentry-environment=production,sentry-release=703d3ed455e18a0faa8d7d180b10d5f403e61a1c,sentry-public_key=d093bca7709346a6a45966764e1b1988,sentry-trace_id=5230530c415b480091a5b0d48bba1142,sentry-org_id=1042114,sentry-transaction=%2F%5Blocale%5D%2Fsearch,sentry-sampled=false,sentry-sample_rand=0.9282883936322245,sentry-sample_rate=0.1",
    "Connection": "keep-alive",
    "Cookie": os.getenv("ITEMDB_COOKIES", ""),
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
}

JELLYNEO_HEADERS = {
    "Host": "items.jellyneo.net",
    "User-Agent": HTTP_HEADERS["User-Agent"],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": HTTP_HEADERS["Accept-Language"],
    "Referer": "https://items.jellyneo.net/",
}

WORKER_COUNT = 20
WorkerThreads: list[Thread] = []
WorkerFlags = [False] * WORKER_COUNT
_ProofCache: dict[str, str] = {}
ItemDB_RateLimitTime = 0
ITEMDB_RATE_LIMIT_COOLDOWN = 60 * 60

def _itemdb_query_enabled() -> bool:
    value = (os.getenv("ENABLE_ITEMDB_QUERY") or "").strip().lower()
    return value not in ("0", "false")

# ───────────────────────────   HTTP session pool   ────────────────────────────
Agent = requests.Session()
Agent.headers.update(HTTP_HEADERS)

AgentPool: list[requests.Session] = [
    requests.Session() for _ in range(WORKER_COUNT)
]
for sess in AgentPool:
    sess.headers.update(HTTP_HEADERS)

def jellyneo_agent() -> requests.Session:
    agent = requests.Session()
    agent.headers.update(JELLYNEO_HEADERS)
    return agent

def get_retry(agent, url, max_retries=5, backoff_factor=1, timeout=10):
    depth = 0
    while True:
        try:
            response = agent.get(url, timeout=timeout)
            return response
        except Exception as exc:  # noqa: BLE001
            depth += 1
            logger.warning("GET %s failed (%s) - retry %d", url, exc, depth)
            if depth >= max_retries:
                raise
            sleep(backoff_factor * (2 ** (depth - 1)))

def post_retry(agent, url, *, json=None, max_retries=5, backoff_factor=1, timeout=10):
    depth = 0
    while True:
        try:
            response = agent.post(url, json=json, timeout=timeout)
            return response
        except Exception as exc:  # noqa: BLE001
            depth += 1
            logger.warning("POST %s failed (%s) - retry %d", url, exc, depth)
            if depth >= max_retries:
                raise
            sleep(backoff_factor * (2 ** (depth - 1)))

# ─────────────────────────────  Core scraper  ─────────────────────────────────


def get_item_details_by_name(
    item_name: str, *,
    force: bool = False,
    agent: requests.Session | None = None,
    timeout: int = 10
) -> dict:
    """
    Scrape item details; honour dm.is_cached unless `force=True`.
    """
    item_name = item_name.lower()
    agent = agent or Agent
    if not force and dm.is_cached(item_name):
        return dm.ItemDatabase.get(item_name) or dm._redis_get_item(item_name)  # type: ignore[attr-defined]
    try:
        data = get_itemdb(item_name, agent=agent, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_itemdb failed for %s: %s", item_name, exc)
        data = _empty_item()
    if data["id"]:
        dm.save_cache(data)
        return data
    else:
        logger.info(f"Item {item_name} not found in itemdb (got {data}), trying Jellyneo...")
    return get_jellyneo_item_details(item_name, agent=agent, timeout=timeout)


def get_jellyneo_item_details(
    item_name: str, *,
    agent: requests.Session | None = None,
    timeout: int = 10
) -> dict:
    agent = jellyneo_agent()
    logger.info("Fetching item %s from Jellyneo...", item_name)
    url = f"https://items.jellyneo.net/search?name={quote(item_name)}&name_type=3"
    response = get_retry(agent, url, timeout=timeout)
    if response.status_code != 200:
        logger.warning(
            "Jellyneo search failed for %s: status=%s, response=%s",
            item_name,
            response.status_code,
            _response_excerpt(response),
        )
        return _empty_item()
    page = BS(response.content, "html.parser")
    data = _parse_search_page(page)
    if not data["id"]:
        logger.warning(
            "Jellyneo search had no parseable result for %s: status=%s, response=%s",
            item_name,
            response.status_code,
            _response_excerpt(response),
        )
        return data

    detail_url = f"https://items.jellyneo.net/item/{data['id']}"
    res = get_retry(agent, detail_url, timeout=timeout)
    if res.status_code != 200:
        logger.warning(
            "Jellyneo detail failed for %s: item_id=%s, status=%s, response=%s",
            item_name,
            data["id"],
            res.status_code,
            _response_excerpt(res),
        )
        return data
    doc = BS(res.content, "html.parser")
    _populate_from_detail_page(doc, data)
    if not data["market_price"]:
        logger.warning("No price history for %s", data["name"])
        data["market_price"] = 999_999
        # set to expire after a day
        data["price_timestamp"] = datetime.now().timestamp() - dm.JN_CACHE_TTL + 60*60*24
    dm.save_cache(data)
    return data


# ─────────────────────────────  HTML helpers  ─────────────────────────────────
def _empty_item() -> dict:
    return {
        "id": "",
        "name": "",
        "description": "",
        "market_price": 0,
        "restock_price": 0,
        "price_timestamp": datetime(1999, 11, 15).timestamp(),
        "recent_prices": [],
        "price_dates": [],
        "rarity": 0,
        "category": "",
        "image": "",
        "restock_shop_link": "",
        "effects": [],
    }


def _parse_search_page(page: BS) -> dict:
    ret = _empty_item()
    match = re.search(r"items\.jellyneo\.net\/item\/(\d+)", str(page))
    if not match:
        return ret
    ret["id"] = match.group(1)

    try:
        pn = page.select(".price-history-link")[0]
        ret["market_price"] = str2int(pn.text)
    except Exception:
        logger.debug("No price detected")
    ret["price_timestamp"] = datetime.now().timestamp()

    return ret


def _populate_from_detail_page(doc: BS, ret: dict) -> None:
    try:
        ret["market_price"] = str2int(doc.select(".price-row")[0].text.split('NP')[0])
    except Exception as e:
        logger.warning("Failed to parse market price: %s", e)
    try:
        ret["name"] = doc.select("h1")[0].text.strip()
        grids = doc.select(".small-block-grid-2")[0].select(".text-center")
        ret["rarity"] = str2int(grids[0].text.strip())
        ret["category"] = grids[1].text.strip()
        ret["restock_price"] = str2int(grids[2].text.strip())
        ret["image"] = grids[-1].select("a")[0]["href"]
        ret["description"] = doc.select("div > p > em")[0].text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse detail page: %s", exc)

    # effects
    for row in doc.select(".special-categories-row"):
        if row.text.strip().lower() == "effects":
            continue
        try:
            ret["effects"].append(
                row.select(".special-categories-title")[0].text.strip().lower()
            )
        except Exception:
            pass


# ──────────────────────────  Batch-search workers  ────────────────────────────
def batch_search_worker(items: list[str], ret: list[dict], wid: int) -> None:
    logger.info("Worker#%d → %s", wid, items)
    try:
        missing = []
        for item in items:
            idx = next((i for i, x in enumerate(ret) if x["name"] == item), 0)
            if dm.is_cached(item):
                ret[idx] = dm.ItemDatabase[item.lower()]
            else:
                missing.append(item)

        itemdb_results = get_many_itemdb(missing, agent=AgentPool[wid]) if missing else {}
        for item in missing:
            idx = next((i for i, x in enumerate(ret) if x["name"] == item), 0)
            data = itemdb_results.get(item.lower())
            if data and data["id"]:
                dm.save_cache(data)
                ret[idx] = data
                continue

            logger.info("Item %s not found in itemdb bulk response, trying Jellyneo...", item)
            data = get_jellyneo_item_details(item, agent=AgentPool[wid])
            ret[idx] = data
    finally:
        WorkerFlags[wid] = False
        logger.info("Worker#%d done", wid)


def is_busy() -> bool:
    return any(WorkerFlags)


def batch_search(items: list[str], *, join: bool = True) -> list[dict] | None:
    if is_busy():
        logger.warning("Workers busy, batch_search aborted")
        return None

    ret = [{"name": item} for item in items]
    buckets = [list(items)] + [[] for _ in range(WORKER_COUNT - 1)]

    for i, bucket in enumerate(buckets):
        if bucket:
            t = Thread(target=batch_search_worker, args=(bucket, ret, i))
            WorkerThreads.append(t)
            WorkerFlags[i] = True
            t.start()

    if join:
        for t in WorkerThreads:
            t.join()
    return ret


# ─────────────────────────── Convenience wrappers ────────────────────────────
def update_item_market_price(item_name: str, price: int) -> bool:
    return dm.update_item_market_price(item_name, price)

def load_cache() -> None:
    dm.load_item_cache()

def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)

def _itemdb_results(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    content = payload.get("content", payload.get("items", []))
    return content if isinstance(content, list) else []

def _response_excerpt(response: requests.Response, limit: int = 300) -> str:
    return response.text.replace("\n", " ").replace("\r", " ").strip()[:limit]

def _itemdb_candidate_names(items: list[dict], limit: int = 5) -> list[str]:
    return [
        str(item.get("name", ""))
        for item in items[:limit]
        if item.get("name")
    ]

def _find_itemdb_result(payload, item_name: str) -> dict | None:
    item_name = item_name.lower()
    items = _itemdb_results(payload)
    return next(
        (
            item for item in items
            if str(item.get("name", "")).lower() == item_name
        ),
        items[0] if len(items) == 1 else None,
    )

def _populate_from_itemdb_result(ret: dict, result: dict) -> None:
    ret["id"] = str(result.get("item_id") or result.get("internal_id") or result.get("id") or "")
    ret["name"] = result.get("name", "")
    ret["description"] = result.get("description", "")
    ret["rarity"] = result.get("rarity") or 0
    ret["market_price"] = deep_get(result, "price.value") or result.get("price") or 999999
    ret["category"] = result.get("category", "")
    ret["image"] = result.get("image", "")
    ret["restock_price"] = result.get("estVal") or result.get("restock_price") or 0
    ret["restock_shop_link"] = deep_get(result, "findAt.restockShop") or ""
    ret["price_timestamp"] = datetime.now().timestamp()

    use_types = result.get("useTypes") or {}
    if _truthy(use_types.get("canEat")):
        ret["effects"].append("edible")
    if _truthy(use_types.get("canPlay")):
        ret["effects"].append("playable")
    if _truthy(use_types.get("canOpen")):
        ret["effects"].append("openable")
    if _truthy(use_types.get("canRead")):
        ret["effects"].append("readable")
    if _truthy(result.get("isWearable")):
        ret["effects"].append("wearable")

def _item_from_itemdb_result(result: dict) -> dict:
    ret = _empty_item()
    _populate_from_itemdb_result(ret, result)
    return ret

def _itemdb_many_results(payload) -> list[dict]:
    if isinstance(payload, dict):
        return [item for item in payload.values() if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []

def _itemdb_rate_limit_remaining() -> int:
    return max(0, int(ItemDB_RateLimitTime - time()))

def _is_itemdb_rate_limited() -> bool:
    remaining = _itemdb_rate_limit_remaining()
    if remaining:
        logger.warning("Skipping itemdb request; rate limit cooldown has %d seconds remaining", remaining)
        return True
    return False

def _mark_itemdb_rate_limited() -> None:
    global ItemDB_RateLimitTime
    ItemDB_RateLimitTime = time() + ITEMDB_RATE_LIMIT_COOLDOWN
    logger.warning(
        "itemdb returned 429; suppressing itemdb requests for %d seconds",
        ITEMDB_RATE_LIMIT_COOLDOWN,
    )

def get_many_itemdb(
    item_names: list[str],
    agent=None,
    timeout: int = 10
) -> dict[str, dict]:
    ret = {}
    if not _itemdb_query_enabled():
        return ret
    item_names = [name for name in item_names if name]
    if not item_names:
        return ret
    if _is_itemdb_rate_limited():
        return ret

    agent = agent or Agent
    refresh_itemdb_proof_header(agent, "/api/v1/items/many", method="POST")
    res = post_retry(
        agent,
        "https://itemdb.com.br/api/v1/items/many",
        json={"name": item_names},
        timeout=timeout
    )
    if res.status_code != 200:
        if res.status_code == 429:
            _mark_itemdb_rate_limited()
        logger.warning(
            "itemdb bulk search failed: items=%d, status=%s, response=%s",
            len(item_names),
            res.status_code,
            _response_excerpt(res),
        )
        return ret
    try:
        payload = res.json()
    except ValueError as exc:
        logger.warning(
            "itemdb bulk search returned invalid JSON: items=%d, status=%s, error=%s, response=%s",
            len(item_names),
            res.status_code,
            exc,
            _response_excerpt(res),
        )
        return ret

    for result in _itemdb_many_results(payload):
        data = _item_from_itemdb_result(result)
        if data["id"] and data["name"]:
            ret[data["name"].lower()] = data

    missing = [name for name in item_names if name.lower() not in ret]
    if missing:
        logger.info(
            "itemdb bulk search missing %d/%d items: sample=%s",
            len(missing),
            len(item_names),
            missing[:5],
        )
    return ret

def get_itemdb(item_name: str, agent=None, timeout: int = 10) -> dict:
    global Agent
    ret = _empty_item()
    if not _itemdb_query_enabled():
        return ret
    if _is_itemdb_rate_limited():
        return ret
    agent = agent or Agent
    refresh_itemdb_proof_header(agent, "/api/v1/search")
    res = get_retry(
        agent,
        f"https://itemdb.com.br/api/v1/search?skipStats=true&s={quote(item_name)}",
        timeout=timeout
    )
    if res.status_code != 200:
        if res.status_code == 429:
            _mark_itemdb_rate_limited()
        logger.warning(
            "itemdb search failed for %s: status=%s, response=%s",
            item_name,
            res.status_code,
            _response_excerpt(res),
        )
        return ret
    try:
        payload = res.json()
    except ValueError as exc:
        logger.warning(
            "itemdb search returned invalid JSON for %s: status=%s, error=%s, response=%s",
            item_name,
            res.status_code,
            exc,
            _response_excerpt(res),
        )
        return ret
    result = _find_itemdb_result(payload, item_name)
    if not result:
        items = _itemdb_results(payload)
        logger.info(
            "itemdb search had no exact match for %s: status=%s, candidates=%d, sample=%s",
            item_name,
            res.status_code,
            len(items),
            _itemdb_candidate_names(items),
        )
        return ret
    _populate_from_itemdb_result(ret, result)
    return ret

_CycleIndex = 0
def update_agent_headers(headers: dict | None = None, cycle=True) -> None:
    global Agent, AgentPool, _CycleIndex
    if not _itemdb_query_enabled():
        return
    headers = headers or {}
    Agent.headers.update(headers)
    refresh_itemdb_proof_header(Agent, "/api/v1/search")
    if cycle:
        _CycleIndex = (_CycleIndex + 1) % WORKER_COUNT
        AgentPool[_CycleIndex].headers.update(headers)
        refresh_itemdb_proof_header(AgentPool[_CycleIndex], "/api/v1/search")
    else:
        for sess in AgentPool:
            sess.headers.update(headers)
            refresh_itemdb_proof_header(sess, "/api/v1/search")


def _decode_jwt_payload(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode()))
    except Exception:
        return {}


def _has_leading_zero_bits(digest: bytes, difficulty: int) -> bool:
    remaining = difficulty
    for byte in digest:
        if remaining <= 0:
            break
        if remaining >= 8:
            if byte != 0:
                return False
            remaining -= 8
            continue
        return byte >> (8 - remaining) == 0
    return True


def _itemdb_cookie_from_header(cookie_header: str) -> str:
    if not cookie_header:
        return ""
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except Exception:
        return ""
    morsel = cookie.get("itemdb-proof")
    return morsel.value if morsel else ""


def _cookie_header_from_jar(cookie_jar) -> str:
    return "; ".join(
        f"{cookie.name}={cookie.value}"
        for cookie in cookie_jar
        if cookie.name and cookie.value is not None
    )


def _itemdb_cookie_is_expiring(cookie_value: str, skew: int = 30) -> bool:
    payload = _decode_jwt_payload(cookie_value)
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        return False
    return expires_at <= time() + skew


def ensure_itemdb_cookie(agent: requests.Session) -> str:
    cookie = _itemdb_cookie_from_header(agent.headers.get("Cookie", ""))
    if cookie and not _itemdb_cookie_is_expiring(cookie):
        return cookie

    try:
        agent.get("https://itemdb.com.br/", timeout=10)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to refresh itemdb session cookie: %s", exc)
        return cookie

    cookie_header = _cookie_header_from_jar(agent.cookies)
    if cookie_header:
        agent.headers.update({"Cookie": cookie_header})
    return _itemdb_cookie_from_header(agent.headers.get("Cookie", ""))


def make_itemdb_proof(cookie_value: str, method: str = "GET", path: str = "/") -> str:
    payload = _decode_jwt_payload(cookie_value)
    difficulty = payload.get("difficulty")
    if not isinstance(difficulty, int) or difficulty < 0 or difficulty > 24:
        return ""

    method = method.upper()
    cache_key = f"{cookie_value}:{method}:{path}"
    cached = _ProofCache.get(cache_key)
    if cached:
        return cached

    limit = max(1, min(2 ** (difficulty + 4), 10_000_000))
    for nonce in range(limit):
        candidate = f"{cookie_value}.{method}.{path}.{nonce}"
        digest = hashlib.sha256(candidate.encode()).digest()
        if _has_leading_zero_bits(digest, difficulty):
            proof = f"{cookie_value}:{nonce}"
            _ProofCache[cache_key] = proof
            return proof
    return ""


def refresh_itemdb_proof_header(agent: requests.Session, path: str, method: str = "GET") -> None:
    cookie = ensure_itemdb_cookie(agent)
    if not cookie:
        cookie = _itemdb_cookie_from_header(os.getenv("ITEMDB_COOKIES", ""))
    proof = make_itemdb_proof(cookie, method=method, path=path)
    if proof:
        agent.headers.update({
            "X-itemdb-Proof": proof,
            "X-Requested-With": "itemdb-web",
        })


def update_agent_headers_from_page(page, cycle=False) -> None:
    if not _itemdb_query_enabled():
        return
    cookies = page.context.cookies("https://itemdb.com.br/")
    cookie_header = "; ".join(
        f"{cookie['name']}={cookie['value']}"
        for cookie in cookies
        if cookie.get("name") and cookie.get("value") is not None
    )
    if "itemdb-proof=" not in cookie_header:
        logger.warning("itemdb-proof cookie not found in browser session")
    headers = {
        "Referer": "https://itemdb.com.br/search",
        "Cookie": cookie_header,
    }
    try:
        headers["User-Agent"] = page.evaluate("navigator.userAgent")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read browser user agent: %s", exc)
    update_agent_headers(headers, cycle=cycle)
