import ipaddress
import typing
import logging
from pathlib import Path
import tomllib

DEFAULT_PORT = 33603
DEFAULT_CHUNK_SIZE = 1024


class Config:
    def __init__(self, data: dict[str, typing.Any]):
        self._data = data
        self.config_file_path: typing.Optional[str] = None

    @staticmethod
    def load_str(config_txt: str):
        return Config(tomllib.loads(config_txt))

    @staticmethod
    def load(fpath: str):
        with open(fpath, 'rb+') as f:
            conf = Config(tomllib.load(f))
            conf.config_file_path = fpath
            return conf

    def get(self, key, default=None):
        if key == "storage_dir":
            storage_dir = self._data.get(key, default)
            if storage_dir is None:
                return storage_dir
            storage_dir = Path(storage_dir)
            if self.config_file_path is None:
                if not storage_dir.is_absolute():
                    raise NotImplementedError("storage_dir key uses relative file path but config file path is unknown")
            else:
                if not storage_dir.is_absolute():
                    storage_dir = (Path(self.config_file_path).parent / storage_dir).resolve(True)
            if not storage_dir.exists():
                raise NotImplementedError("storage_dir does not exist")
            if storage_dir.is_file():
                raise NotImplementedError("storage_dir cannot be a file")
            return storage_dir.resolve(True)
        return self._data.get(key, default)

