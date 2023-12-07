import os
import shutil
import time
from typing import Union, List, Optional

from mcdreforged.api.utils import Serializable
from ruamel import yaml

from lazybing_thb.utils import psi, logger, rtr

PrefixType = Union[str, List[str]]


class PermissionRequirements(Serializable):
    reload: int = 3

    tpa: int = 0
    home: int = 0
    back: int = 0


class CommandPrefix(Serializable):
    home: PrefixType = "!!home"
    tpa: PrefixType = "!!tpa"
    tpc: PrefixType = "!!tpc"
    back: PrefixType = "!!back"

    @property
    def home_(self) -> List[str]:
        return [self.home] if isinstance(self.home, str) else self.home

    @property
    def tpa_(self) -> List[str]:
        return [self.tpa] if isinstance(self.tpa, str) else self.tpa

    @property
    def tpc_(self) -> List[str]:
        return [self.tpc] if isinstance(self.tpc, str) else self.tpc

    @property
    def back_(self) -> List[str]:
        return [self.back] if isinstance(self.back, str) else self.back

    @property
    def help_message_prefix(self):
        return self.home_[0]


class Configuration(Serializable):
    __TEMPLATE_PATH = os.path.join("resources", "default_cfg.yml")
    __CONFIG_FILE = 'config.yml'
    __CONFIG_TEMP = 'temp_config.yml'
    __PRINT_TO_CONSOLE = True

    command_prefix: CommandPrefix = CommandPrefix.get_default()
    permission_requirements: PermissionRequirements = PermissionRequirements.get_default()

    teleport_delay: int = 5
    request_expire_time: Union[int, float] = 60.0
    max_home_count: int = 10
    undo_history_expire_time: int = 24  # hrs

    minecraft_data_api_timeout: int
    debug: bool
    verbosity: bool

    @classmethod
    def get_template(cls) -> yaml.CommentedMap:
        try:
            with psi.open_bundled_file(cls.__TEMPLATE_PATH) as f:
                return yaml.YAML().load(f)
        except Exception as e:
            logger.warning("Template not found, is plugin modified?", exc_info=e)
            return yaml.CommentedMap()

    @staticmethod
    def get_data_folder():
        if psi is not None:
            return psi.get_data_folder()
        return '.'

    @classmethod
    def get_config_file_path(cls):
        return os.path.join(cls.get_data_folder(), cls.__CONFIG_FILE)

    @classmethod
    def get_config_temp(cls):
        return os.path.join(cls.get_data_folder(), cls.__CONFIG_TEMP)

    @classmethod
    def log(cls, tr_key: str, *args, **kwargs):
        if psi is not None and cls.__PRINT_TO_CONSOLE:
            return logger.info(rtr(tr_key, *args, with_prefix=False, **kwargs))

    @property
    def prefix(self) -> List[str]:
        prefixes = []
        for values in self.command_prefix.serialize().values():  # type: PrefixType
            if isinstance(values, str):
                prefixes.append(values)
            else:
                prefixes += values
        return prefixes

    @property
    def primary_prefix(self) -> str:
        return self.prefix[0]

    @property
    def debug_commands(self):
        return self.serialize().get('debug', False)

    @property
    def is_verbose(self):
        return self.serialize().get("verbosity", False)

    def is_reached_max_home_amount(self, count: int):
        return count >= self.max_home_count

    def is_history_expired(self, timestamp: float):
        return timestamp + (self.undo_history_expire_time * 60 * 60) <= time.time()

    @property
    def mda_timeout(self):
        return self.serialize().get('minecraft_data_api_timeout', 3)

    @classmethod
    def load(cls) -> 'Configuration':
        default_config = cls.get_default().serialize()
        config_file_path = cls.get_config_file_path()
        needs_save = False

        try:
            with open(config_file_path, encoding='utf8') as file_handler:
                read_data: dict = yaml.YAML(typ='safe').load(file_handler)
        except Exception as e:
            result_config = default_config.copy()
            needs_save = True
            cls.log('server_interface.load_config_simple.failed', e)
        else:
            result_config = read_data
            if default_config is not None:
                # constructing the result config based on the given default config
                for key, value in default_config.items():
                    if key not in read_data:
                        result_config[key] = value
                        cls.log('server_interface.load_config_simple.key_missed', key, value)
                        needs_save = True
            cls.log('server_interface.load_config_simple.succeed')

        try:
            result_config = cls.deserialize(result_config)
        except Exception as e:
            result_config = cls.get_default()
            needs_save = True
            cls.log('server_interface.load_config_simple.failed', e)

        if needs_save:
            result_config.save()

        logger.set_verbose(result_config.is_verbose)
        return result_config

    def save(self):
        config_file_path = self.get_config_file_path()
        config_temp_path = self.get_config_temp()
        if os.path.isdir(config_file_path):
            os.removedirs(config_file_path)

        def _save(safe_dump: bool = False):
            if os.path.exists(config_temp_path):
                os.remove(config_temp_path)
            formatted_config: yaml.CommentedMap
            if os.path.isfile(config_file_path) and not safe_dump:
                with open(config_file_path, 'r', encoding='utf8') as f:
                    formatted_config = yaml.YAML(typ='rt').load(f)
            else:
                formatted_config = self.get_template()
                safe_dump = True

            config_content = self.serialize()
            formatted_config.update(config_content)
            with open(config_temp_path, 'w', encoding='utf8') as f:
                yaml.YAML(typ='rt').dump(formatted_config, f)

            try:
                with open(config_temp_path, 'r', encoding='utf8') as f:
                    self.deserialize(yaml.YAML(typ='safe').load(f))
            except (TypeError, ValueError):
                if safe_dump:
                    os.remove(config_temp_path)
                    with open(config_file_path, 'w', encoding='utf8') as f:
                        yaml.YAML(typ='safe').dump(config_content, f)
                    logger.info(rtr("config.save_with_default_fmt"))
                    logger.warning(rtr('config.format_failure'))
                else:
                    logger.info(rtr("config.retry_saving"))
                    _save(safe_dump=True)
            else:
                if os.path.exists(config_file_path):
                    os.remove(config_file_path)
                shutil.move(config_temp_path, config_file_path)

        _save()


config: Optional["Configuration"] = None
if psi is not None:
    config = Configuration.load()
