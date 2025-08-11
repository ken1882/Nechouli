import re
import os
from module.base.utils import str2int
from module.logger import logger
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
from threading import Thread, Lock
from urllib.parse import quote
from dotenv import load_dotenv
import json
import requests

load_dotenv()

HTTP_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
}

WORKER_COUNT = 20
DB_LOCK = Lock()
WorkerThreads:list[Thread] = []
WorkerFlags   = [False] * WORKER_COUNT

Agent = requests.Session()
Agent.headers.update(HTTP_HEADERS)

AgentPool:list[requests.Session] = []
for i in range(WORKER_COUNT):
    AgentPool.append(requests.Session())
    AgentPool[-1].headers.update(HTTP_HEADERS)

REDIS_MEGA_KEY = "jellyneo_itemdb"  # Redis HASH key; each field is an item name (lowercased)
REDIS_CACHE = os.getenv("REDIS_CACHE", None)

redis_conn = None
if REDIS_CACHE:
    import redis
    # decode_responses=True so we get str instead of bytes
    redis_conn = redis.Redis.from_url(REDIS_CACHE, decode_responses=True)

CACHE_FILE = "cache/items.json"
CACHE_TTL  = 60*60*24*7

# In-memory hot cache (optional; we lazily hydrate from Redis when needed)
Database = {}


def _redis_enabled() -> bool:
    return redis_conn is not None


def _redis_hget_item(iname: str):
    """Fetch a single item JSON from Redis HASH and load into memory cache."""
    if not _redis_enabled():
        return None
    try:
        data = redis_conn.hget(REDIS_MEGA_KEY, iname)
        if not data:
            return None
        obj = json.loads(data)
        with DB_LOCK:
            Database[iname] = obj
        return obj
    except Exception as e:
        logger.warning(f"Redis HGET failed for {iname}: {e}")
        return None


def _redis_hset_item(item: dict):
    """Write a single item JSON into Redis HASH."""
    if not _redis_enabled() or not item or "name" not in item:
        return
    try:
        iname = item["name"].lower()
        redis_conn.hset(REDIS_MEGA_KEY, iname, json.dumps(item))
    except Exception as e:
        logger.warning(f"Redis HSET failed for {item.get('name')}: {e}")


def get_item_details_by_name(item_name, force=False, agent=None):
    item_name = item_name.lower()
    global Database, Agent
    if not agent:
        agent = Agent
    if not force and is_cached(item_name):
        return Database[item_name]

    logger.info(f"Getting item details for {item_name}")
    qname = quote(item_name)
    url = f"https://items.jellyneo.net/search?name={qname}&name_type=3"
    response = agent.get(url)
    page = BS(response.content, "html.parser")
    ret = {
        "id": "",
        "description": "",
        "name": "",
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
    try:
        reg = re.search(r"items\.jellyneo\.net\/item\/(\d+)", str(page))
        ret["id"] = reg.group(1)
        link = f"https://{reg.group()}"
    except Exception as e:
        logger.exception(e)
        return ret
    try:
        pn = page.select('.price-history-link')[0]
        ret["market_price"] = str2int(pn.text)
        ret["price_timestamp"] = datetime.strptime(pn.attrs['title'], "%B %d, %Y").timestamp()
    except Exception:
        logger.warning(f"Failed to get price for {item_name}, probably cash item or heavily inflated")
        ret["market_price"] = 999999
        ret["price_timestamp"] = datetime.now().timestamp()

    res = agent.get(link)
    doc = BS(res.content, "html.parser")
    try:
        ret["name"] = doc.select('h1')[0].text.strip()
        ul = doc.select('.small-block-grid-2')[0]
        grids = ul.select('.text-center')
        ret["rarity"] = str2int(grids[0].text.strip())
        ret["category"] = grids[1].text.strip()
        ret["restock_price"] = str2int(grids[2].text.strip())
        ret["image"] = grids[-1].select('a')[0]['href']
        ret["description"] = doc.select('div > p > em')[0].text.strip()
    except Exception as e:
        logger.exception(e)
        return ret

    try:
        rows = doc.select('.special-categories-row')
        effect_row_started = False
        for row in rows:
            if row.text.strip().lower() == 'effects':
                effect_row_started = True
                continue
            if not effect_row_started:
                continue
            try:
                ret["effects"].append(row.select('.special-categories-title')[0].text.strip().lower())
            except Exception:
                pass
    except Exception as e:
        logger.exception(e)
        return ret

    save_cache(ret)  # will HSET single field
    return ret


def load_cache(force_local=False):
    global Database
    if _redis_enabled() and not force_local:
        try:
            if redis_conn.exists(REDIS_MEGA_KEY):
                # bulk load
                raw = redis_conn.hgetall(REDIS_MEGA_KEY)
                with DB_LOCK:
                    Database = {k: json.loads(v) for k, v in raw.items()}
                return Database
        except Exception as e:
            logger.warning(f"Redis HGETALL failed: {e}")

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                with DB_LOCK:
                    Database = json.loads(f.read())
        except Exception:
            pass
    return Database


def save_cache(item=None, padding=True, save_local=False):
    global Database, DB_LOCK

    if item:
        with DB_LOCK:
            Database[item["name"].lower()] = item
        if _redis_enabled():
            _redis_hset_item(item)
            if not save_local:
                return
    else:
        if _redis_enabled():
            try:
                mapping = {}
                with DB_LOCK:
                    for k, v in Database.items():
                        mapping[k] = json.dumps(v)
                if mapping:
                    redis_conn.hset(REDIS_MEGA_KEY, mapping=mapping)
                if not save_local:
                    return
            except Exception as e:
                logger.warning(f"Redis bulk HSET failed: {e}")

    # Local file persistence (optional)
    with DB_LOCK:
        with open(CACHE_FILE, 'w') as f:
            if padding:
                json.dump(Database, f, indent=4)
            else:
                json.dump(Database, f)


def is_cached(item_name):
    iname = item_name.lower()
    obj = Database.get(iname)
    if obj is None and _redis_enabled():
        obj = _redis_hget_item(iname)
    if obj is None:
        return False

    # rarity > 300 => always accept cached
    if obj.get("rarity", 0) > 300:
        return True

    ts = obj.get("price_timestamp")
    if not ts:
        return False
    if (datetime.now() - datetime.fromtimestamp(ts)).total_seconds() > CACHE_TTL:
        return False
    return True


def batch_search_worker(items, ret, worker_id):
    global AgentPool, Database, WorkerFlags
    logger.info(f"Worker#{worker_id} started: {items}")
    try:
        for item in items:
            ret_idx = next((i for i, x in enumerate(ret) if x["name"] == item), 0)
            if is_cached(item):
                ret[ret_idx] = Database[item.lower()]
            else:
                ret[ret_idx] = get_item_details_by_name(item, agent=AgentPool[worker_id])
    finally:
        WorkerFlags[worker_id] = False
        logger.info(f"Worker#{worker_id} finished: {items}")


def is_busy():
    global WorkerFlags
    return any(WorkerFlags)


def batch_search(items, join=True):
    '''
    Multi-threaded batch search for item details. Note that if `join=False`,
    the function will return immediately and you'll need to fetch the results later using  `is_busy()`.
    '''
    global Database, WorkerThreads, WorkerFlags
    if is_busy():
        logger.warning("Search workers are busy")
        return None
    ret = [{'name': item} for item in items]
    thread_args = [[] for _ in range(WORKER_COUNT)]
    for i, item in enumerate(items):
        thread_args[i % WORKER_COUNT].append(item)
    for i in range(WORKER_COUNT):
        if thread_args[i]:
            WorkerThreads.append(Thread(target=batch_search_worker, args=(thread_args[i], ret, i)))
            WorkerFlags[i] = True
            WorkerThreads[-1].start()
    if join:
        for t in WorkerThreads:
            t.join()
    return ret


def update_item_price(item, price):
    global Database
    logger.info(f"Updating price for {item} to {price}")
    iname = item.lower()
    if iname in Database:
        Database[iname]["price"] = price
        Database[iname]["price_timestamp"] = datetime.now().timestamp()
        # Persist only this item to Redis
        save_cache(Database[iname])
        return True
    else:
        obj = get_item_details_by_name(iname)
        if obj:
            obj["price"] = price
            obj["price_timestamp"] = datetime.now().timestamp()
            save_cache(obj)
            return True
    return False

def clear_cache():
    global Database
    Database = {}
    if _redis_enabled():
        try:
            redis_conn.delete(REDIS_MEGA_KEY)
        except Exception as e:
            logger.warning(f"Redis DELETE failed: {e}")
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    logger.info("Cache cleared")

load_cache()
