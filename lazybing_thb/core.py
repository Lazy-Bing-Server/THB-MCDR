import time
from typing import Optional

from mcdreforged.api.command import *
from mcdreforged.api.rtext import *
from mcdreforged.api.types import CommandSource, PlayerCommandSource

from lazybing_thb.location import Location
from lazybing_thb.storage.config import config
from lazybing_thb.storage.impl.history import TeleportHistory
from lazybing_thb.storage.impl.home import PlayerHomeStorage
from lazybing_thb.teleport import teleport_to_player, teleport_to_location
from lazybing_thb.timer import RequestTimer
from lazybing_thb.utils import rtr, htr, psi, named_thread
from lazybing_thb.player_list import PlayerOnlineList


def show_help(source: CommandSource):
    meta = psi.get_self_metadata()
    source.reply(
        htr(
            'help.detailed.text',
            prefixes=config.prefix,
            home_prefix=config.command_prefix.home_[0],
            tpa_prefix=config.command_prefix.tpa_[0],
            tpc_prefix=config.command_prefix.tpc_[0],
            back_prefix=config.command_prefix.back_[0],
            name=meta.name,
            ver=str(meta.version)
        )
    )


def reload_self(source: CommandSource):
    psi.reload_plugin(psi.get_self_metadata().id)
    source.reply(rtr('msg.reloaded'))


def get_current_requester(target: str):
    timer = RequestTimer.get_timer(target)
    with timer.lock():
        if not timer.is_valid():
            return None
        requester = timer.get_requester()
        timer.remove()
    return requester


# !!tpa
@named_thread
def accept_teleport_request(source: PlayerCommandSource):
    requester: Optional[str] = get_current_requester(source.player)
    if requester is None:
        return source.reply(rtr('tpa.request_not_found').set_color(RColor.red))
    if not PlayerOnlineList.get_instance().is_online(requester):
        return source.reply(rtr('teleport.not_online', RText(requester).set_color(RColor.yellow)))
    if config.teleport_delay >= 1:
        psi.tell(requester, rtr('tpa.countdown', str(config.teleport_delay)))
        for count in range(1, config.teleport_delay):
            time.sleep(1)
            psi.tell(requester, rtr('tpa.countdown', str(config.teleport_delay - count)))
        time.sleep(1)
    teleport_to_player(requester, source.player)


# !!tpc
def decline_teleport_request(source: PlayerCommandSource):
    requester: Optional[str] = get_current_requester(source.player)
    if requester is None:
        return source.reply(rtr('tpa.request_not_found').set_color(RColor.red))
    source.reply(rtr("tpa.request_declined", RText(requester, RColor.yellow)))
    psi.tell(requester, rtr('tpa.request_declined_requester', RText(source.player, RColor.yellow)))


# !!tpa <player>
def request_teleport(source: PlayerCommandSource, target: str):
    if source.player == target:
        return source.reply(rtr('tpa.urself').set_color(RColor.red))
    player_component = RText(target, RColor.yellow)
    if not PlayerOnlineList.get_instance().is_online(target):
        return source.reply(rtr('teleport.not_online', player_component).set_color(RColor.red))
    requester: str = source.player
    timer = RequestTimer.get_timer(target)
    with timer.lock():
        if timer.is_valid():
            return source.reply(
                rtr('tpa.request_already_exists', player_component).set_color(RColor.red)
            )
        timer.get_request().set_requester(requester)
        timer.start()

        def _tr(key: str, *args, **kwargs):
            return rtr(f"tpa.send_to_target.{key}", *args, **kwargs)
        psi.tell(
            target,
            _tr(
                'text',
                player=player_component,
                accept_comp=_tr('accept_comp').c(RAction.run_command, config.command_prefix.tpa_[0]).h(_tr('accept_hover')),
                decline_comp=_tr('decline_comp').c(RAction.run_command, config.command_prefix.tpc_[0]).h(_tr('decline_hover'))
            )
        )
        source.reply(rtr('tpa.request_create', player_component))


# !!home list
def list_home(source: PlayerCommandSource):
    home_list = PlayerHomeStorage.get_instance(source.player).get_data()
    component_list = [
        rtr('home.list_home_title', count=len(home_list), max_=config.max_home_count)
    ]
    num = 1
    is_dark = False
    for name, home_site in home_list.items():
        component_list.append(
            RTextList(
                f'[§7{num}§r] ',
                RText(
                    name, RColor.dark_aqua if is_dark else RColor.aqua, [RStyle.bold]
                ).h(
                    rtr('home.list_home_site.hover', name)
                ).c(
                    RAction.run_command, f'{config.command_prefix.home_[0]} {name}'
                )
            )
        )
        num += 1
        is_dark = not is_dark
    source.reply(RTextBase.join('\n', component_list))


@named_thread
# !!home add <home_site>
def add_home(source: PlayerCommandSource, home_site_name: str):
    home = PlayerHomeStorage.get_instance(source.player)
    player_location = Location.get_location(source.player)
    with home.lock():
        home_list = home.get_data()
        amount = len(home_list)
        if config.is_reached_max_home_amount(amount):
            return source.reply(rtr('home.reached_max_amount', config.max_home_count).set_color(RColor.red))
        added = home.set_home(home_site_name, player_location)
    if not added:
        return source.reply(rtr('home.home_site_exists', home_site_name).set_color(RColor.red))
    source.reply(rtr('home.added_home_site', home_site_name, len(home_list), config.max_home_count))


# !!home remove/rm <home_site>
def remove_home(source: PlayerCommandSource, home_site_name: str):
    home = PlayerHomeStorage.get_instance(source.player)
    with home.lock():
        removed = home.remove_home(home_site_name)
        if not removed:
            return source.reply(rtr('home.home_site_not_exists', home_site_name).set_color(RColor.red))
        amount = len(home.get_data())
    source.reply(rtr('home.home_site_removed', home_site_name, amount, config.max_home_count))


# !!home <home_site>
def teleport_to_home(source: PlayerCommandSource, home_site_name: str):
    home = PlayerHomeStorage.get_instance(source.player)
    with home.lock():
        site_location = home.get_home(home_site_name)
    teleport_to_location(source.player, site_location)


def undo_teleport(source: PlayerCommandSource):
    history = TeleportHistory.get_instance(source.player)
    history_location = history.get_history()
    if history_location is None:
        source.reply(
            rtr('back.no_history_found').set_color(RColor.red)
        )
    if config.is_history_expired(history_location.timestamp) and not history_location.warned:
        history.set_warned()
        return source.reply(
            rtr('back.expire_warn.text').set_color(RColor.yellow).h(
                rtr('back.expire_warn.hover')
            ).c(
                RAction.run_command, config.command_prefix.back_[0]
            )
        )
    teleport_to_location(source.player, history_location)


def register_command():
    tpa_root = Literal(config.command_prefix.tpa_).runs(accept_teleport_request)
    tpc_root = Literal(config.command_prefix.tpc_).runs(decline_teleport_request)
    home_root = Literal(config.command_prefix.home_).runs(show_help)
    back_root = Literal(config.command_prefix.back_).runs(undo_teleport).requires(
        lambda src: src.has_permission(config.permission_requirements.back))

    # !!tpa
    player_node_name = "player"
    tpa_root.then(
        QuotableText(player_node_name).requires(
            lambda src: src.has_permission(config.permission_requirements.tpa)
        ).runs(
            lambda src, ctx: request_teleport(src, ctx[player_node_name])
        )
    )

    # !!home
    home_site_name = "home_site"
    home_root.then(
        Literal('reload').requires(
            lambda src: src.has_permission(config.permission_requirements.reload)
        ).runs(
            lambda src: reload_self(src)
        )
    ).then(
        Literal('list').runs(list_home)
    ).then(
        Literal('add').then(
            QuotableText(home_site_name).runs(
                lambda src, ctx: add_home(src, ctx[home_site_name])
            )
        )
    ).then(
        Literal(['rm', 'remove']).then(
            QuotableText(home_site_name).runs(
                lambda src, ctx: remove_home(src, ctx[home_site_name])
            )
        )
    ).then(
        QuotableText(home_site_name).runs(
            lambda src, ctx: teleport_to_home(src, ctx[home_site_name])
        )
    )

    for item in (tpa_root, tpc_root, home_root, back_root):
        item.requires(lambda src: isinstance(src, PlayerCommandSource))
        psi.register_command(item)
