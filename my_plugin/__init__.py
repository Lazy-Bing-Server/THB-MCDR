from mcdreforged.api.all import *

from my_plugin.utils import rtr
from my_plugin.config import config
from my_plugin.core import register_command


def on_load(server: PluginServerInterface, prev_module):
    server.register_help_message(config.primary_prefix, rtr('help.mcdr'))
    register_command()
