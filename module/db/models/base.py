from __future__ import annotations

import gzip
import json
import os
import pathlib
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime
from typing import Any, ClassVar, Iterable, List, Mapping, MutableMapping, Optional, Protocol, Type, TypeVar

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None  # noqa: N816 – keep sentinel for typing

try:
    import pymongo  # type: ignore
except ImportError:  # pragma: no cover
    pymongo = None  # noqa: N816

T = TypeVar("T", bound="BaseModel")

# ---------------------------------------------------------------------------
# Storage back‑ends
# ---------------------------------------------------------------------------

class StorageBackend(ABC):
    """Minimal persistence contract."""

    @abstractmethod
    def save(self, model: "BaseModel", *, ttl: Optional[int] = None) -> None:  # noqa: D401 – read as imperative
        """Persist *model* under ``model.key``."""

    @abstractmethod
    def load(self, model_cls: Type[T], key: str) -> Optional[T]:
        """Return a model previously saved under *key* or ``None``."""

    @abstractmethod
    def delete(self, key: str) -> None:  # noqa: D401
        """Remove the entry if it exists."""


class LocalBackend(StorageBackend):
    """Gzip‑JSON files under *root* / <model> / <key>.json.gz"""

    def __init__(self, root: os.PathLike | str = "./data") -> None:
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # helpers --------------------------------------------------
    def _path(self, model: str, key: str) -> pathlib.Path:
        return self.root / model / f"{key}.json.gz"

    # API ------------------------------------------------------
    def save(self, model: "BaseModel", *, ttl: int | None = None) -> None:  # ttl ignored
        path = self._path(model.__class__.__name__, model.key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(model.serialize())

    def load(self, model_cls: Type[T], key: str) -> Optional[T]:
        path = self._path(model_cls.__name__, key)
        if not path.exists():
            return None
        return model_cls.deserialize(path.read_bytes())

    def delete(self, key: str) -> None:  # unused for local – requires model name
        raise NotImplementedError("Use model.delete() which knows the model name.")


class RedisBackend(StorageBackend):
    """Store gzipped JSON under key  <ModelName>:<pk>  (binary)."""

    def __init__(self, client: "redis.Redis | None" = None, **redis_kwargs: Any) -> None:
        if redis is None:
            raise ImportError("redis-py is not installed")
        self.client = client or redis.Redis(**redis_kwargs)  # type: ignore[arg-type]

    def _key(self, model: str, key: str) -> str:  # noqa: A003 – clash with attr name OK
        return f"{model}:{key}"

    def save(self, model: "BaseModel", *, ttl: int | None = None) -> None:
        rkey = self._key(model.__class__.__name__, model.key)
        if ttl:
            self.client.setex(rkey, ttl, model.serialize())  # type: ignore[attr-defined]
        else:
            self.client.set(rkey, model.serialize())  # type: ignore[attr-defined]

    def load(self, model_cls: Type[T], key: str) -> Optional[T]:
        data = self.client.get(self._key(model_cls.__name__, key))  # type: ignore[attr-defined]
        return model_cls.deserialize(data) if data else None

    def delete(self, key: str) -> None:
        self.client.delete(key)  # type: ignore[attr-defined]


class MongoBackend(StorageBackend):
    """One MongoDB collection per model."""

    def __init__(self, database: "pymongo.database.Database | None" = None, **mongo_kwargs: Any) -> None:
        if pymongo is None:
            raise ImportError("pymongo is not installed")
        if database is not None:
            self.db = database
        else:
            client = pymongo.MongoClient(**mongo_kwargs)  # type: ignore[misc]
            self.db = client["nechouli"]

    def _coll(self, model_cls: Type["BaseModel"]):
        return self.db[model_cls.__name__]

    def save(self, model: "BaseModel", *, ttl: int | None = None) -> None:  # noqa: ARG002 – ttl via Mongo TTL index
        self._coll(model.__class__).replace_one({"_id": model.key}, model.to_dict(), upsert=True)

    def load(self, model_cls: Type[T], key: str) -> Optional[T]:  # type: ignore[override]
        doc = self._coll(model_cls).find_one({"_id": key})
        return model_cls(**doc) if doc else None

    def delete(self, key: str) -> None:  # type: ignore[override]
        raise NotImplementedError("Need model class; call Model.delete() instead.")


# ---------------------------------------------------------------------------
# BaseModel
# ---------------------------------------------------------------------------

class BaseModel:
    # shared backend across *all* subclasses unless overridden
    _backend: ClassVar[StorageBackend] = LocalBackend()

    # ------------------------------------------------------------------
    # construction / dict helpers
    # ------------------------------------------------------------------
    def __init__(self, **kwargs: Any) -> None:
        self.load_data(kwargs)

    # make it mapping‑like ------------------------------------------------
    def __getitem__(self, key: str) -> Any:  # noqa: D401
        return self.__dict__.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.__dict__[key] = value

    def __getattr__(self, item: str) -> Any:  # type: ignore[override]
        try:
            return self.__dict__[item]
        except KeyError:
            raise AttributeError(item) from None

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: D401
        self.__dict__[name] = value

    # ------------------------------------------------------------------
    def load_data(self, data: Mapping[str, Any]) -> None:
        self.__dict__.update(data)

    def to_dict(self) -> MutableMapping[str, Any]:
        return self.__dict__.copy()

    # ------------------------------------------------------------------
    # persistence helpers
    # ------------------------------------------------------------------
    @property
    def key(self) -> str:
        k = self.__dict__.get("id") or self.__dict__.get("key")
        if not k:
            raise AttributeError("Model must have an 'id' or 'key' attribute for persistence")
        return str(k)

    # save / reload -------------------------------------------------------
    def save(self, *, ttl: Optional[int] = None) -> None:
        self.__class__._backend.save(self, ttl=ttl)

    @classmethod
    def get(cls: Type[T], key: str) -> Optional[T]:
        return cls._backend.load(cls, key)

    def delete(self) -> None:
        self.__class__._backend.delete(self.key)

    # back‑end management --------------------------------------------------
    @classmethod
    def configure_backend(cls, backend: StorageBackend) -> None:
        cls._backend = backend

    # ------------------------------------------------------------------
    # (de)serialisation
    # ------------------------------------------------------------------
    def serialize(self) -> bytes:
        """Gzipped JSON bytes."""
        return gzip.compress(json.dumps(self.to_dict(), default=str).encode())

    @classmethod
    def deserialize(cls: Type[T], data: bytes | str | os.PathLike[str]) -> T:  # type: ignore[override]
        if isinstance(data, (str, os.PathLike)):
            data = pathlib.Path(data).read_bytes()
        obj_dict = json.loads(gzip.decompress(data).decode())
        return cls(**obj_dict)

    # pretty repr ---------------------------------------------------------
    def __str__(self) -> str:  # noqa: D401
        return f"<{self.__class__.__name__}: {self.__dict__}>"

    __repr__ = __str__

