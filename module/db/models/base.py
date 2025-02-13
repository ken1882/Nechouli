import json
import gzip
try:
    import redis
except ImportError:
    pass

class BaseModel:

    def __init__(self, *args, **kwargs):
        self.load_data(kwargs)

    def __getitem__(self, key):
        return self.__dict__.get(key, None)

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getattr__(self, key):
        return self.__dict__.get(key, None)

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def load_data(self, data):
        self.__dict__.update(data)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return f"<BaseModel: {self.__dict__}>"

    def __repr__(self):
        return self.__str__()

    def serialize(self, type='json'):
        if type == 'json':
            return gzip.compress(json.dumps(self.to_dict()).encode())

    @classmethod
    def deserialize(cls, data:bytes):
        data = json.loads(gzip.decompress(data).decode())
        return cls(**data)

    def to_json(self):
        return json.dumps(self.to_dict())

