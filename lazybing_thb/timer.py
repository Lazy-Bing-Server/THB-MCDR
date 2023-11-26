import contextlib
import threading
import time
import uuid

from typing import Dict, Union

from mcdreforged.api.decorator import FunctionThread
from mcdreforged.api.rtext import *
from lazybing_thb.utils import named_thread
from lazybing_thb.storage.config import config
from lazybing_thb.storage.impl.request import TeleportRequest
from lazybing_thb.utils import psi, rtr


class RequestTimer:
    __running_timer: Dict[str, "RequestTimer"] = {}

    def __init__(self, target: str):
        self.__lock = threading.RLock()
        self.__target = target
        self.__uuid = uuid.uuid4()
        self.__request = None

    @property
    def uuid_prefix(self) -> str:
        return hex(self.__uuid.time_low)[2:]

    @property
    def uuid(self) -> uuid.UUID:
        return self.__uuid

    @property
    def target(self) -> str:
        return self.__target

    @contextlib.contextmanager
    def lock(self, blocking: bool = True, timeout: Union[float, int] = -1):
        acq = self.__lock.acquire(blocking=blocking, timeout=timeout)
        try:
            yield acq
        finally:
            if acq:
                self.__lock.release()

    def get_requester(self) -> str:
        with self.__lock:
            return self.get_request().get_requester()

    def get_request(self) -> TeleportRequest:
        with self.__lock:
            if self.__request is None:
                self.__request = TeleportRequest.get_instance(self.target)
            return self.__request

    def is_valid(self) -> bool:
        with self.__lock:
            return self in self.__running_timer.values()

    def remove(self) -> None:
        with self.__lock:
            if self in self.__running_timer.values():
                del self.__running_timer[self.target]
                self.get_request().remove_file()

    def start(self) -> FunctionThread:
        with self.__lock:
            @named_thread(f"Request_{self.target}_{self.uuid_prefix}")
            def daemon():
                time.sleep(config.request_expire_time)
                with self.__lock:
                    if self.is_valid():
                        requester = self.get_requester()
                        target = self.target
                        psi.tell(target, rtr("tpa.teleport_expired_target", requester))
                        psi.tell(
                            requester,
                            rtr("tpa.teleport_expired_requester.text", target).h(
                                rtr('tpa.teleport_expired_requester.hover', target)
                            ).c(
                                RAction.run_command, f"{config.command_prefix.tpa_[0]} {target}"
                            )
                        )
                        self.remove()
                        self.get_request().remove_file()

            self.__running_timer[self.target] = self
            return daemon()

    @classmethod
    def get_timer(cls, target: str):
        if target in cls.__running_timer:
            return cls.__running_timer[target]
        return cls(target)
