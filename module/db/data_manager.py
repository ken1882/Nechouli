from module.logger import logger
from module.db.models import base
from module.base import utils
import module.db.models as models
import struct
import importlib

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
                if not issubclass(type(dat), base.BaseModel):
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

