from typing import Union, Iterable, List
from mcdreforged.api.types import CommandSource
from mcdreforged.api.command import *

from my_plugin.utils import rtr, htr, psi
from my_plugin.config import config


def show_help(source: CommandSource):
    meta = psi.get_self_metadata()
    source.reply(
        htr(
            'help.detailed',
            prefixes=config.prefix,
            prefix=config.primary_prefix,
            name=meta.name,
            ver=str(meta.version)
        )
    )


def reload_self(source: CommandSource):
    psi.reload_plugin(psi.get_self_metadata().id)
    source.reply(rtr('msg.reloaded'))


def register_command():
    def permed_literal(literals: Union[str, Iterable[str]]) -> Literal:
        literals = {literals} if isinstance(literals, str) else set(literals)
        perm = 1
        for item in literals:
            target_perm = config.get_prem(item)
            if target_perm > perm:
                perm = target_perm
        return Literal(literals).requires(lambda src: src.has_permission(target_perm))

    root_node: Literal = Literal(config.prefix).runs(lambda src: show_help(src))

    children: List[AbstractNode] = [
        permed_literal('reload').runs(lambda src: reload_self(src))
    ]

    debug_nodes: List[AbstractNode] = []

    if config.debug_commands:
        children += debug_nodes

    for node in children:
        root_node.then(node)

    psi.register_command(root_node)
