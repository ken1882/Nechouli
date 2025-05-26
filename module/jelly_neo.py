import re
import os
from module.base.utils import str2int
from module.logger import logger
from module.db.models.item import NeoItem
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
from threading import Thread, Lock
from urllib.parse import quote
import json
import requests

HTTP_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
}

WORKER_COUNT = 20
DB_LOCK = Lock()
WorkerThreads = []
WorkerFlags   = [False] * WORKER_COUNT

Agent = requests.Session()
Agent.headers.update(HTTP_HEADERS)

AgentPool:list[requests.Session] = []
for i in range(WORKER_COUNT):
    AgentPool.append(requests.Session())
    AgentPool[-1].headers.update(HTTP_HEADERS)

REDIS_MEGA_KEY = "jellyneo_itemdb"
REDIS_CACHE = os.getenv("REDIS_CACHE", None)
if REDIS_CACHE:
    import redis

CACHE_FILE = "cache/items.json"
CACHE_TTL  = 60*60*24*7

Database = {}

def get_item_details_by_name(item_name, forced=False, agent=None):
    item_name = item_name.lower()
    global Database, Agent
    if not agent:
        agent = Agent
    if not forced and is_cached(item_name):
        return Database[item_name]
    logger.info(f"Getting item details for {item_name}")
    item_name = quote(item_name)
    url = f"https://items.jellyneo.net/search?name={item_name}&name_type=3"
    response = agent.get(url)
    page = BS(response.content, "html.parser")
    ret = NeoItem(name=item_name)
    try:
        reg = re.search(r"items\.jellyneo\.net\/item\/(\d+)", str(page))
        ret.id = reg.group(1)
        link = f"https://{reg.group()}"
    except Exception as e:
        logger.exception(e)
        return ret
    try:
        pn = page.select('.price-history-link')[0]
        ret.price = str2int(pn.text)
        ret.price_timestamp = datetime.strptime(pn.attrs['title'], "%B %d, %Y").timestamp()
    except Exception:
        logger.warning(f"Failed to get price for {item_name}, probably cash item or heavily inflated")
        ret.price = 10**10
        ret.price_timestamp = datetime.now().timestamp()
    res = agent.get(link)
    doc = BS(res.content, "html.parser")
    try:
        ret.name = doc.select('h1')[0].text.strip()
        ul = doc.select('.small-block-grid-2')[0]
        grids = ul.select('.text-center')
        ret.rarity = str2int(grids[0].text.strip())
        ret.category = grids[1].text.strip()
        ret.restock_price = str2int(grids[2].text.strip())
        ret.image = grids[-1].select('a')[0]['href']
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
            except Exception as e:
                pass
    except Exception as e:
        logger.exception(e)
        return ret
    save_cache(ret)
    return ret

def load_cache(force_local=False):
    global Database
    if REDIS_CACHE and not force_local:
        redis_conn = redis.Redis.from_url(REDIS_CACHE)
        if redis_conn.exists(REDIS_MEGA_KEY):
            Database = json.loads(redis_conn.get(REDIS_MEGA_KEY))
            return Database
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                Database = json.loads(f.read())
        except Exception as e:
            pass
    return Database

def save_cache(item=None, padding=True, save_local=False):
    global Database, DB_LOCK
    if REDIS_CACHE:
        if item:
            Database[item["name"].lower()] = item
        redis_conn = redis.Redis.from_url(REDIS_CACHE)
        redis_conn.set(REDIS_MEGA_KEY, json.dumps(Database))
        if not save_local:
            return
    with DB_LOCK:
        if item:
            Database[item["name"].lower()] = item
        with open(CACHE_FILE, 'w') as f:
            if padding:
                json.dump(Database, f, indent=4)
            else:
                json.dump(Database, f)

def is_cached(item_name):
    iname = item_name.lower()
    if iname not in Database:
        return False
    if Database[iname]["rarity"] > 300:
        return True
    if (datetime.now() - datetime.fromtimestamp(Database[iname]["price_timestamp"])).total_seconds() > CACHE_TTL:
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
    item = item.lower()
    if item in Database:
        Database[item]["price"] = price
        Database[item]["price_timestamp"] = datetime.now().timestamp()
        save_cache()
        return True
    else:
        item = get_item_details_by_name(item)
        if item:
            item["price"] = price
            item["price_timestamp"] = datetime.now().timestamp()
            save_cache(item)
            return True
    return False
