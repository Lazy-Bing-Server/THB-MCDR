import json

from minecraft_data_api import get_player_dimension
from typing import Callable
from mcdreforged.api.rtext import *

from lazybing_thb.utils import named_thread, psi, logger, rtr
from lazybing_thb.location import Location, dim_convert
from lazybing_thb.storage.config import config
from lazybing_thb.storage.impl.history import TeleportHistory


@named_thread
def _execute_teleport(requester: str, func: Callable, *args, record_history: bool = True, **kwargs):
    if record_history:
        requester_location = Location.get_location(requester)
        logger.debug(f'Requester_location: {requester_location}')
        TeleportHistory.get_instance(requester).set_location(requester_location)

    func(*args, **kwargs)

    psi.tell(
        requester,
        rtr(
            'teleport.after_teleport.text',
            undo_command=RText(
                config.command_prefix.back_[0],
                RColor.gray
            ).h(
                rtr('teleport.after_teleport.hover')
            ).c(
                RAction.run_command,
                config.command_prefix.back_[0]
            )
        )
    )


def teleport_to_location(requester: str, loc: Location, record_history: bool = True):
    def __execute():
        psi.execute(f'execute in {loc.get_dim_name()} as {requester} run tp {loc.x} {loc.y} {loc.z}')
        logger.info(f"Teleported {requester} to ({loc.x}, {loc.y}, {loc.z}) in {loc.dim}")

    _execute_teleport(requester, __execute, record_history=record_history)


def teleport_to_player(requester: str, target: str, record_history: bool = True):
    def __execute():
        dim_id = get_player_dimension(target, timeout=config.mda_timeout)
        target_dim = dim_convert.get(dim_id, dim_id)
        psi.execute(f'execute in {target_dim} as {requester} run tp {target}')
        logger.info(f"Teleported {requester} to {target}")

    _execute_teleport(requester, __execute, record_history=record_history)
