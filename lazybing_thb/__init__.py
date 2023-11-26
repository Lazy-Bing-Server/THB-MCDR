from mcdreforged.api.types import PluginServerInterface

from lazybing_thb.utils import rtr
from lazybing_thb.storage.config import config
from lazybing_thb.core import register_command
from lazybing_thb.storage.impl.request import TeleportRequest
from lazybing_thb.storage.impl.history import TeleportHistory
from lazybing_thb.storage.impl.home import PlayerHomeStorage
from lazybing_thb.player_list import PlayerOnlineList


PlayerOnlineList.get_instance().register_event_listeners()


def on_load(server: PluginServerInterface, prev_module):
    TeleportRequest.remove_all_files()
    TeleportHistory.resolve_dir()
    PlayerHomeStorage.resolve_dir()

    register_command()
    server.register_help_message(config.command_prefix.help_message_prefix, rtr('help.mcdr'))
