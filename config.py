import ipaddress
import typing
import logging
import tomllib


class Config:
    instance = None

    def __init__(self, data: dict[str, typing.Any]):
        self._data = data

    @staticmethod
    def load(fpath: str):
        with open(fpath, 'rb+') as f:
            Config.instance = Config(tomllib.load(f))
            return Config.instance

    def get(self, key, default=None):
        return self._data.get(key, default)

