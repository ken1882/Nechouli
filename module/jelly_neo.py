import re
import os
from module.base.utils import str2int
from module.logger import logger
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
from threading import Thread, Lock
from urllib.parse import quote
from dotenv import load_dotenv
from time import sleep
import orjson
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
REDIS_KEY_PREFIX = "jellyneo_itemdb:"
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


def _redis_key(iname: str) -> str:
    return f"{REDIS_KEY_PREFIX}{iname}"

def _redis_get_item(iname: str):
    """GET the JSON value for one item; add to in-memory DB."""
    if not _redis_enabled():
        return None
    try:
        data = redis_conn.get(_redis_key(iname))
        if not data:
            return None
        obj = orjson.loads(data)
        with DB_LOCK:
            Database[iname] = obj
        return obj
    except Exception as e:
        logger.warning(f"Redis GET failed for {iname}: {e}")
        return None

def _redis_set_item(item: dict, ttl: int = 0):
    """SETEX one item with per-key TTL."""
    if not _redis_enabled() or not item or "name" not in item:
        return
    if not ttl:
        ttl = CACHE_TTL
    try:
        iname = item["name"].lower()
        redis_conn.setex(_redis_key(iname), ttl, orjson.dumps(item))
    except Exception as e:
        logger.warning(f"Redis SETEX failed for {item.get('name')}: {e}")

def get_item_details_by_name(item_name, force=False, agent=None):
    item_name = item_name.lower()
    global Database, Agent
    if not agent:
        agent = Agent
    if not force and is_cached(item_name):
        return _redis_get_item(item_name) or Database.get(item_name)

    logger.info(f"Getting item details for {item_name}")
    qname = quote(item_name)
    url = f"https://items.jellyneo.net/search?name={qname}&name_type=3"
    depth = 0
    while True:
        try:
            response = agent.get(url)
            break
        except Exception as e:
            logger.warning(f"Failed to get item details for {item_name}: {e}")
            depth += 1
            sleep(2 ** depth)
            if depth >= 3:
                raise e
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

    save_cache(ret)
    return ret


def load_cache(force_local=False):
    global Database
    if _redis_enabled() and not force_local:
        logger.info("Loading cache from Redis (batch SCAN/MGET)…")
        try:
            prefix   = REDIS_KEY_PREFIX
            cursor   = 0
            batch_sz = 20_000          # SCAN hint
            total    = 0
            while True:
                cursor, keys = redis_conn.scan(
                    cursor=cursor,
                    match=f"{REDIS_KEY_PREFIX}*",
                    count=batch_sz
                )
                if keys:
                    # bulk fetch values for this batch
                    values = redis_conn.mget(keys)
                    for k, v in zip(keys, values):
                        if v is None:
                            continue
                        iname = k[len(prefix):]
                        try:
                            Database[iname] = orjson.loads(v)
                            total += 1
                        except orjson.JSONDecodeError:
                            logger.debug("Bad JSON in key %s", k)
                    logger.info("Loaded %d items so far...", total)
                if cursor == 0:
                    break
            logger.info("Finished Redis warm-up: %d items loaded", total)
            return Database
        except Exception as e:
            logger.warning("Redis SCAN/MGET failed: %s", e)
    elif os.path.exists(CACHE_FILE):
        logger.info("Loading item cache from local file")
        try:
            with open(CACHE_FILE, "r") as f:
                Database = orjson.load(f)
        except Exception:
            pass
    logger.info(f"Loaded {len(Database)} items")
    return Database


def save_cache(item=None, to_file=False, padding=True):
    global Database, DB_LOCK

    if item:
        if _redis_enabled():
            _redis_set_item(item)
        else:
            with DB_LOCK:
                Database[item["name"].lower()] = item
    if not to_file:
        return
    # local file persistence
    with DB_LOCK:
        with open(CACHE_FILE, "w") as f:
            orjson.dump(Database, f, indent=4 if padding else None)


def is_cached(item_name):
    iname = item_name.lower()
    obj = Database.get(iname)
    if obj is None and _redis_enabled():
        obj = _redis_get_item(iname)   # ← uses GET instead of HGET
    if obj is None:
        return False

    # cash item (rarity > 300) never refreshes
    if obj.get("rarity", 0) > 300:
        return True

    # staleness check vs. our TTL window
    ts = obj.get("price_timestamp")
    if not ts:
        return False
    return (datetime.now() - datetime.fromtimestamp(ts)).total_seconds() <= CACHE_TTL


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


def update_item_market_price(item_name, price):
    global Database
    logger.info(f"Updating market price for {item_name} to {price}")
    iname = item_name.lower()
    if iname in Database:
        Database[iname]["market_price"] = price
        Database[iname]["price_timestamp"] = datetime.now().timestamp()
        save_cache(Database[iname])
        return True
    else:
        obj = get_item_details_by_name(iname)
        if obj:
            obj["market_price"] = price
            obj["price_timestamp"] = datetime.now().timestamp()
            save_cache(obj)
            return True
    return False

def clear_cache():
    global Database
    Database = {}
    if _redis_enabled():
        try:
            logger.info("Deleting all item keys from Redis …")
            for k in redis_conn.scan_iter(f"{REDIS_KEY_PREFIX}*"):
                redis_conn.delete(k)
        except Exception as e:
            logger.warning(f"Redis delete scan failed: {e}")
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    logger.info("Cache cleared")

load_cache()
