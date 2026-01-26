# frozen_string_literal: true
import os
import re
from datetime import datetime
from threading import Thread
from time import sleep
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup as BS
from module.base.utils import str2int
from module.db import data_manager as dm
from module.logger import logger

# ─────────────────────────────  Env / constants  ──────────────────────────────
HTTP_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ),
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/58.0.3029.110 Safari/537.3"
    ),
}

WORKER_COUNT = 20
WorkerThreads: list[Thread] = []
WorkerFlags = [False] * WORKER_COUNT

# ───────────────────────────   HTTP session pool   ────────────────────────────
Agent = requests.Session()
Agent.headers.update(HTTP_HEADERS)

AgentPool: list[requests.Session] = [
    requests.Session() for _ in range(WORKER_COUNT)
]
for sess in AgentPool:
    sess.headers.update(HTTP_HEADERS)

def get_retry(agent, url, max_retries=5, backoff_factor=1):
    depth = 0
    while True:
        try:
            response = agent.get(url, timeout=10)
            return response
        except Exception as exc:  # noqa: BLE001
            depth += 1
            logger.warning("GET %s failed (%s) - retry %d", url, exc, depth)
            if depth >= max_retries:
                raise
            sleep(backoff_factor * (2 ** (depth - 1)))

# ─────────────────────────────  Core scraper  ─────────────────────────────────


def get_item_details_by_name(
    item_name: str, *, force: bool = False, agent: requests.Session | None = None
) -> dict:
    """
    Scrape item details; honour dm.is_cached unless `force=True`.
    """
    item_name = item_name.lower()
    agent = agent or Agent
    if not force and dm.is_cached(item_name):
        return dm.ItemDatabase.get(item_name) or dm._redis_get_item(item_name)  # type: ignore[attr-defined]

    logger.info("Fetching item %s from Jellyneo...", item_name)
    url = f"https://items.jellyneo.net/search?name={quote(item_name)}&name_type=3"
    response = get_retry(agent, url)
    page = BS(response.content, "html.parser")
    data = _parse_search_page(page)
    if not data["id"]:
        return data

    detail_url = f"https://items.jellyneo.net/item/{data['id']}"
    res = get_retry(agent, detail_url)
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
        for item in items:
            idx = next((i for i, x in enumerate(ret) if x["name"] == item), 0)
            if dm.is_cached(item):
                ret[idx] = dm.ItemDatabase[item.lower()]
            else:
                ret[idx] = get_item_details_by_name(
                    item, agent=AgentPool[wid]
                )
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
    buckets = [[] for _ in range(WORKER_COUNT)]
    for i, item in enumerate(items):
        buckets[i % WORKER_COUNT].append(item)

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
