from module.logger import logger
from module.db.models import base_model
from module.base import utils
import module.db.models as models
import struct
import importlib
import os
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional
from collections import defaultdict
from time import sleep
import random
import orjson
import threading
import sys
import portalocker

from dotenv import load_dotenv
load_dotenv()

REDIS_JN_MEGA_KEY = "jellyneo_itemdb"
REDIS_JN_KEY_PREFIX = "jellyneo_itemdb:"
REDIS_GLOBAL_KEY_PREFIX = "nechouli_globals:"
REDIS_LOCK_PREFIX = "nechouli_lock:"
REDIS_CACHE_URL = os.getenv("REDIS_CACHE", None)

CACHE_FILE = "cache/items.json"
JN_CACHE_TTL = 60 * 60 * 24 * 7  # default 7 days

DB_LOCK = Lock()
_GLOBAL_FILE = Path('.nch_globals.json')
ItemDatabase: Dict[str, dict] = {}

RedisConn = None
RedisFactory = None
if REDIS_CACHE_URL:
    import redis
    from redlock import RedLockFactory
    RedisConn = redis.Redis.from_url(REDIS_CACHE_URL, decode_responses=True)
    RedisFactory = RedLockFactory(connection_details=[{'url': REDIS_CACHE_URL}])


def _redis_enabled() -> bool:
    return RedisConn is not None


def _redis_key(iname: str) -> str:
    return f"{REDIS_JN_KEY_PREFIX}{iname}"

# ────────────────────────────────────────────────────────────────────────────────
# Single-item helpers
# ────────────────────────────────────────────────────────────────────────────────
def _redis_get_item(iname: str) -> Optional[dict]:
    if not _redis_enabled():
        return None
    try:
        data = RedisConn.get(_redis_key(iname))
        if data:
            obj = orjson.loads(data)
            with DB_LOCK:
                ItemDatabase[iname] = obj
            return obj
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis GET failed (%s): %s", iname, exc)
    return None


def _redis_set_item(item: dict, ttl: int = 0) -> None:
    if not _redis_enabled() or not item or "name" not in item:
        return
    ttl = ttl or JN_CACHE_TTL
    try:
        RedisConn.setex(_redis_key(item["name"].lower()), ttl, orjson.dumps(item))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis SETEX failed (%s): %s", item.get("name"), exc)

# ────────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────────
def load_item_cache(force_local: bool = False) -> dict:
    """
    Hydrate the in-memory `Database` dict from Redis (preferred) or local JSON.
    """
    global ItemDatabase  # noqa: PLW0603

    if _redis_enabled() and not force_local:
        logger.info("Loading cache from Redis...")
        try:
            prefix, total, cursor = REDIS_JN_KEY_PREFIX, 0, 0
            while True:
                cursor, keys = RedisConn.scan(cursor=cursor, match=f"{prefix}*", count=20_000)
                if keys:
                    values = RedisConn.mget(keys)
                    for k, v in zip(keys, values):
                        if v:
                            ItemDatabase[k[len(prefix):]] = orjson.loads(v)
                            total += 1
                if cursor == 0:
                    break
            logger.info("Redis warm-up complete (%d items)", total)
            return ItemDatabase
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis scan failed: %s", exc)

    # Fallback – local JSON
    if os.path.exists(CACHE_FILE):
        logger.info("Loading item cache from %s", CACHE_FILE)
        with open(CACHE_FILE, "rb") as fh:
            ItemDatabase = orjson.loads(fh.read())
    logger.info("Loaded %d cached items", len(ItemDatabase))
    return ItemDatabase

def save_cache(item: Optional[dict] = None, *, to_file: bool = False) -> None:
    """
    Persist a single `item` to Redis/in-mem, or dump the whole DB to disk.
    """
    if item:
        _redis_set_item(item)
        with DB_LOCK:
            ItemDatabase[item["name"].lower()] = item

    if to_file:
        with DB_LOCK, open(CACHE_FILE, "wb") as fh:
            fh.write(orjson.dumps(ItemDatabase, option=orjson.OPT_INDENT_2))


def is_cached(iname: str) -> bool:
    """
    True if item exists *and* its market-price timestamp is still within TTL.
    """
    iname = iname.lower()
    obj = ItemDatabase.get(iname) or _redis_get_item(iname)
    if not obj:
        return False

    if obj.get("rarity", 0) > 300:  # NC item, never refresh
        return True

    ts = obj.get("price_timestamp")
    if not ts:
        return False
    age = (datetime.now() - datetime.fromtimestamp(ts)).total_seconds()
    return age <= JN_CACHE_TTL


def update_item_market_price(iname: str, price: int) -> bool:
    """
    Patch `market_price` + timestamp for a single item, wherever it lives.
    """
    iname = iname.lower()
    if iname not in ItemDatabase:
        return False
    item = ItemDatabase[iname]
    item["market_price"] = price
    item["price_timestamp"] = datetime.now().timestamp()
    save_cache(item)
    return True


def clear_cache() -> None:
    """Delete everything from memory, Redis and local JSON file."""
    global ItemDatabase  # noqa: PLW0603
    ItemDatabase = {}

    if _redis_enabled():
        logger.info("Wiping Redis keys %s*", REDIS_JN_KEY_PREFIX)
        for key in RedisConn.scan_iter(f"{REDIS_JN_KEY_PREFIX}*"):
            RedisConn.delete(key)

    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)

    logger.info("Cache cleared")


_path_lock = defaultdict(threading.RLock)

@contextmanager
def file_lock(path, open_mode="r+b", exclusive=True, timeout=60):
    st = datetime.now()
    while True:
        with _path_lock[path]:
            flags = portalocker.LOCK_EX if exclusive else portalocker.LOCK_SH
            try:
                with open(path, open_mode) as fp:
                    portalocker.lock(fp, flags)
                    try:
                        yield fp
                    finally:
                        portalocker.unlock(fp)
                    break
            except portalocker.exceptions.AlreadyLocked as e:
                logger.error(f"Error locking {path}: {e}")
                sleep(random.uniform(0.5, 3))
                if datetime.now() >= st+timedelta(seconds=timeout):
                    raise e

@contextmanager
def redis_lock(name, timeout=600):
    global RedisFactory, REDIS_LOCK_PREFIX
    if not _redis_enabled():
        raise RuntimeError("Redis not enabled")
    n = int(timeout / 0.2) # delay 200ms per retry
    with RedisFactory.create_lock(REDIS_LOCK_PREFIX + name, retry_times=n):
        yield

@contextmanager
def dlock(name, timeout=600, open_mode="r+b", exclusive=True):
    """
    Distributed lock using Redis or file-based locking.

    Args:
        name (str): Lock name.
        timeout (int): Lock timeout in seconds.
        open_mode (str): File open mode if using file lock.
        exclusive (bool): Exclusive lock if True, shared if False.
    """
    global RedisFactory
    if not _redis_enabled():
        with file_lock(Path(f'.{name}.lock'), open_mode, exclusive, timeout) as fp:
            yield fp
        return
    if type(name) == type(Path('.')):
        name = name.stem
    name = name.replace('/', '_').replace('\\', '_')
    with redis_lock(name, timeout):
        yield

def global_set(key: str, value: str) -> None:
    """
    Write a key-value pair, cross-process safe.
    Redis if available, else file+flock.
    """
    if _redis_enabled():
        RedisConn.set(REDIS_GLOBAL_KEY_PREFIX + key, value)
        return

    _GLOBAL_FILE.touch(exist_ok=True)
    with file_lock(_GLOBAL_FILE, "rb+") as fp:
        try:
            data = orjson.loads(fp.read()) or {}
        except orjson.JSONDecodeError:
            data = {}
        data[key] = value
        fp.seek(0)
        fp.truncate()
        fp.write(orjson.dumps(data))

def global_get(key: str) -> Optional[str]:
    """
    Read back a value previously saved by `global_set`.
    Returns `None` if key not found.
    """
    if _redis_enabled():
        val = RedisConn.get(REDIS_GLOBAL_KEY_PREFIX + key)
        return val if val is not None else None

    if not _GLOBAL_FILE.exists():
        return None

    with file_lock(_GLOBAL_FILE, "rb") as fp:
        try:
            data = orjson.loads(fp.read()) or {}
        except orjson.JSONDecodeError:
            return None
    return data.get(key)



class DataManager:

    def __init__(self,
            name, backend,
            save_path=''
        ):
        self.name = name
        self.backend = backend
        self.save_path = save_path
        self.data = {}

    def save(self):
        getattr(self, f'save_{self.backend}')()

    def load(self):
        getattr(self, f'load_{self.backend}')()

    def save_local(self):
        page_size = 0x100
        with open(self.save_path, 'wb') as file:
            for key, dat in self.data.items():
                if not issubclass(type(dat), base_model.BaseModel):
                    raise ValueError(f"Only models can be saved")
                blob = dat.serialize()
                blk_size = len(blob)
                entry_bytes  = key.encode() + b'\x00'
                entry_bytes += dat.__module__.encode() + b'\x00'
                entry_bytes += type(dat).__name__.encode() + b'\x00'
                entry_bytes += struct.pack('I', blk_size)
                paddings = page_size - (blk_size + len(entry_bytes)) % page_size
                file.write(entry_bytes + blob + b'\x00' * paddings)

    def load_local(self):
        self.data = {}
        with open(self.save_path, 'rb') as file:
            while True:
                key_bytes = []
                while True:
                    byte = file.read(1)
                    if byte == b'\x00':
                        if key_bytes:
                            break
                        else: # skip padding
                            continue
                    if not byte:  # EOF reached
                        return
                    key_bytes.append(byte)

                key = b''.join(key_bytes).decode()  # Decode key name
                # Read module name
                module_bytes = []
                while (byte := file.read(1)) != b'\x00':
                    module_bytes.append(byte)
                module_name = b''.join(module_bytes).decode()
                # Read class name
                class_bytes = []
                while (byte := file.read(1)) != b'\x00':
                    class_bytes.append(byte)
                class_name = b''.join(class_bytes).decode()
                # Read block size
                blk_size = struct.unpack('I', file.read(4))[0]

                # Read compressed data
                logger.info(f"Loading {key} -> {module_name}.{class_name} ({blk_size} bytes)")
                compressed_data = file.read(blk_size)

                try:
                    module = importlib.import_module(module_name)
                    cls = getattr(module, class_name)
                except (ModuleNotFoundError, AttributeError) as e:
                    raise ImportError(f"Failed to import {module_name}.{class_name}: {e}")

                # Reconstruct and store object
                if hasattr(cls, "deserialize"):
                    obj = cls.deserialize(compressed_data)
                    self.data[key] = obj
                else:
                    raise ValueError(f"Class {class_name} does not implement `deserialize()`")

