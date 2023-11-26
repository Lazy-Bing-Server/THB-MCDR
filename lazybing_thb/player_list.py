import threading
import contextlib
from typing import Optional, Union
from mcdreforged.api.event import MCDRPluginEvents

from minecraft_data_api import get_server_player_list
from lazybing_thb.storage.config import config
from lazybing_thb.utils import named_thread, psi


class PlayerOnlineList:
    __inst: Optional["PlayerOnlineList"] = None

    def __init__(self):
        self.__list = list()
        self.__lock = threading.RLock()
        self.__limit: Optional[int] = None

    @contextlib.contextmanager
    def lock(self, blocking: bool = True, timeout: Union[float, int] = -1):
        acq = self.__lock.acquire(blocking=blocking, timeout=timeout)
        try:
            yield acq
        finally:
            if acq:
                self.__lock.release()

    @property
    def players(self):
        return self.__list.copy()

    @property
    def limit(self):
        return self.__limit

    @property
    def amount(self):
        return len(self.__list)

    def is_online(self, player: str):
        with self.lock():
            return player in self.__list

    def add(self, *player: str):
        with self.lock():
            for item in player:
                if item not in self.__list:
                    self.__list.append(item)

    def remove(self, *player: str):
        with self.lock():
            for item in player:
                if item in self.__list:
                    self.__list.remove(item)

    @classmethod
    def get_instance(cls):
        if cls.__inst is None:
            cls.__inst = cls()
        return cls.__inst

    def register_event_listeners(self):
        psi.register_event_listener(MCDRPluginEvents.PLUGIN_LOADED, lambda server, previous_module: self.init_player_list())
        psi.register_event_listener(MCDRPluginEvents.SERVER_STARTUP, lambda server: self.on_server_startup())
        psi.register_event_listener(MCDRPluginEvents.SERVER_STOP, lambda server, return_code: self.on_server_stop())
        psi.register_event_listener(MCDRPluginEvents.PLAYER_JOINED, lambda server, player, info: self.add(player))
        psi.register_event_listener(MCDRPluginEvents.PLAYER_LEFT, lambda server, player: self.remove(player))

    @named_thread
    def init_player_list(self):
        with self.lock():
            if psi.is_server_startup():
                amount, limit, player_list = get_server_player_list(timeout=config.mda_timeout)
                self.add(*player_list)
                self.__limit = limit

    @named_thread
    def on_server_startup(self):
        with self.lock():
            if psi.is_server_startup():
                limit = get_server_player_list(timeout=config.mda_timeout)[1]
                self.__limit = limit

    def on_server_stop(self):
        with self.lock():
            self.__limit = None
            self.__list = []
