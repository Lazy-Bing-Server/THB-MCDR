import abc
import contextlib
import os
import shutil

from threading import RLock

from typing_extensions import Self
from typing import Union, Type
from lazybing_thb.utils import psi


class AbstractPlayerStorage(abc.ABC):
    __instances = {}

    @classmethod
    def get_folder_name(cls):
        raise NotImplementedError

    @classmethod
    def get_folder_path(cls):
        return os.path.join(psi.get_data_folder(), cls.get_folder_name())

    @classmethod
    def get_instance(cls: Type[Self], player: str) -> Self:
        if player not in cls.__instances.keys():
            cls.__instances[player] = cls(player)
        return cls.__instances[player]

    @classmethod
    def resolve_dir(cls):
        if os.path.isfile(cls.get_folder_path()):
            os.remove(cls.get_folder_path())
        if not os.path.isdir(cls.get_folder_path()):
            os.makedirs(cls.get_folder_path())

    def __init__(self, player: str):
        self.__player: str = player
        self.__lock = RLock()

    @property
    def player(self):
        return self.__player

    @property
    def file_path(self):
        raise NotImplementedError

    @contextlib.contextmanager
    def lock(self, blocking: bool = True, timeout: Union[float, int] = -1):
        acq = self.__lock.acquire(blocking=blocking, timeout=timeout)
        try:
            yield acq
        finally:
            if acq:
                self.__lock.release()

    def exists(self):
        with self.lock():
            return os.path.isfile(self.file_path)

    def remove_file(self):
        with self.lock():
            os.remove(self.file_path)

    def ensure_file(self):
        with self.lock():
            if os.path.isdir(self.file_path):
                shutil.rmtree(self.file_path)

    @contextlib.contextmanager
    def open(self, mode: str = 'r', encoding: str = 'utf8'):
        with self.lock():
            self.ensure_file()
            with open(self.file_path, mode=mode, encoding=encoding) as f:
                yield f
