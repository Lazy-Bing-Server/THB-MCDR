import functools
import inspect
import logging
import os
import re
import threading
from typing import Optional, Dict, Callable, List, Union

from mcdreforged.api.decorator import FunctionThread
from mcdreforged.api.event import MCDRPluginEvents
from mcdreforged.api.rtext import *
from mcdreforged.api.types import PluginServerInterface, ServerInterface, MCDReforgedLogger

psi: Optional[PluginServerInterface]
__si, psi = ServerInterface.get_instance(), None
if __si is not None:
    psi = __si.as_plugin_server_interface()
MessageText: type = Union[str, RTextBase]


class BlossomLogger(MCDReforgedLogger):
    class NoColorFormatter(logging.Formatter):
        def formatMessage(self, record) -> str:
            return self.clean_console_color_code(super().formatMessage(record))

        @staticmethod
        def clean_console_color_code(text: str) -> str:
            return re.compile(r'\033\[(\d+(;\d+)?)?m').sub('', text)

    __inst: Optional["BlossomLogger"] = None
    __verbosity: bool = False

    __SINGLE_FILE_LOG_PATH: Optional[str] = None
    if psi is not None:
        __SINGLE_FILE_LOG_PATH = f'{psi.get_self_metadata().id}.log'
    FILE_FMT: NoColorFormatter = NoColorFormatter(
        '[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    @classmethod
    def get_instance(cls) -> "BlossomLogger":
        if cls.__inst is None:
            cls.__inst = cls().bind_single_file()
        return cls.__inst

    @classmethod
    def set_verbose(cls, verbosity: bool) -> None:
        cls.__verbosity = verbosity
        cls.get_instance().debug("Verbose mode enabled")

    @classmethod
    def get_verbose(cls) -> bool:
        return cls.__verbosity

    def __init__(self):
        if psi is not None:
            super().__init__(psi.get_self_metadata().id)
            psi.register_event_listener(MCDRPluginEvents.PLUGIN_LOADED, lambda *args, **kwargs: self.unbind_file())
        else:
            super().__init__()

    def debug(self, *args, option=None, no_check: bool = False) -> None:
        return super().debug(*args, option=option, no_check=no_check or self.__verbosity)

    def unbind_file(self) -> None:
        if self.file_handler is not None:
            self.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None

    def bind_single_file(self, file_name: Optional[str] = None) -> "BlossomLogger":
        if file_name is None:
            if self.__SINGLE_FILE_LOG_PATH is None:
                return self
            file_name = os.path.join(psi.get_data_folder(), self.__SINGLE_FILE_LOG_PATH)
        self.unbind_file()
        ensure_dir(os.path.dirname(file_name))
        self.file_handler = logging.FileHandler(file_name, encoding='UTF-8')
        self.file_handler.setFormatter(self.FILE_FMT)
        self.addHandler(self.file_handler)
        return self


def htr(translation_key: str, *args, prefixes: Optional[List[str]] = None, **kwargs) -> RTextMCDRTranslation:
    def __get_regex_result(line: str):
        pattern = r'(?<=§7){}[\S ]*?(?=§)'
        for prefix_tuple in prefixes:
            for prefix in prefix_tuple:
                result = re.search(pattern.format(prefix), line)
                if result is not None:
                    return result
        return None

    def __htr(key: str, *inner_args, **inner_kwargs) -> MessageText:
        original, processed = ntr(key, *inner_args, **inner_kwargs), []
        if not isinstance(original, str):
            return key
        for line in original.splitlines():
            result = __get_regex_result(line)
            if result is not None:
                command = result.group() + ' '
                processed.append(RText(line).c(RAction.suggest_command, command).h(
                    rtr(f'help.detailed.hover', command)))
            else:
                processed.append(line)
        return RTextBase.join('\n', processed)

    return rtr(translation_key, *args, **kwargs).set_translator(__htr)


def get_thread_prefix() -> str:
    return to_camel_case(psi.get_self_metadata().name, divider=' ') + '_'


def rtr(translation_key: str, *args, with_prefix=True, **kwargs) -> RTextMCDRTranslation:
    prefix = psi.get_self_metadata().id + '.'
    if with_prefix and not translation_key.startswith(prefix):
        translation_key = f"{prefix}{translation_key}"
    return psi.rtr(translation_key, *args, **kwargs).set_translator(ntr)


def named_thread(arg: Optional[Union[str, Callable]] = None) -> Callable:
    def wrapper(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            def try_func():
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    psi.logger.exception('Error running thread {}'.format(threading.current_thread().name), exc_info=e)

            prefix = get_thread_prefix()
            thread = FunctionThread(target=try_func, args=[], kwargs={}, name=prefix + thread_name)
            thread.start()
            return thread

        wrap.__signature__ = inspect.signature(func)
        wrap.original = func
        return wrap

    # Directly use @new_thread without ending brackets case, e.g. @new_thread
    if isinstance(arg, Callable):
        thread_name = to_camel_case(arg.__name__, divider="_")
        return wrapper(arg)
    # Use @new_thread with ending brackets case, e.g. @new_thread('A'), @new_thread()
    else:
        thread_name = arg
        return wrapper


def ntr(
        translation_key: str,
        *args,
        language: Optional[str] = None,
        _mcdr_tr_language: Optional[str] = None,
        allow_failure: bool = True,
        **kwargs
) -> MessageText:
    if language is not None and _mcdr_tr_language is None:
        _mcdr_tr_language = language
    try:
        return psi.tr(
            translation_key, *args, language=language, _mcdr_tr_language=_mcdr_tr_language, allow_failure=False, **kwargs
        )
    except (KeyError, ValueError):
        fallback_language = psi.get_mcdr_language()
        try:
            if fallback_language == 'en_us':
                raise KeyError(translation_key)
            return psi.tr(
                translation_key, *args, _mcdr_tr_language='en_us', language='en_us', allow_failure=allow_failure, **kwargs
            )
        except (KeyError, ValueError):
            languages = []
            for item in (language, fallback_language, 'en_us'):
                if item not in languages:
                    languages.append(item)
            languages = ', '.join(languages)
            if allow_failure:
                psi.logger.error(f'Error translate text "{translation_key}" to language {languages}')
            else:
                raise KeyError(f'Translation key "{translation_key}" not found with language {languages}')


def to_camel_case(string: str, divider: str = ' ', upper: bool = True) -> str:
    word_list = [capitalize(item) for item in string.split(divider)]
    if not upper:
        first_word_char_list = list(word_list[0])
        first_word_char_list[0] = first_word_char_list[0].lower()
        word_list[0] = ''.join(first_word_char_list)
    return ''.join(word_list)


def capitalize(string: str) -> str:
    if len(string) == 0:
        return string
    char_list = list(string)
    char_list[0] = char_list[0].upper()
    return ''.join(char_list)


def ensure_dir(folder: str) -> None:
    if os.path.isfile(folder):
        raise FileExistsError('Data folder structure is occupied by existing file')
    if not os.path.isdir(folder):
        os.makedirs(folder)


def dtr(translation_dict: Dict[str, str], *args, **kwargs) -> RTextMCDRTranslation:
    def fake_tr(
            translation_key: str,
            *inner_args,
            _mcdr_tr_language: Optional[str] = None,
            language: Optional[str] = None,
            allow_failure: bool = True,
            **inner_kwargs
    ) -> MessageText:
        if language is not None and _mcdr_tr_language is None:
            _mcdr_tr_language = language
        result = translation_dict.get(language)
        fallback_language = [psi.get_mcdr_language()]
        if 'en_us' not in fallback_language and 'en_us' != language:
            fallback_language.append('en_us')
        for lang in fallback_language:
            result = translation_dict.get(lang)
            if result is not None:
                use_rtext = any([isinstance(e, RTextBase) for e in list(inner_args) + list(inner_kwargs.values())])
                if use_rtext:
                    return RTextBase.format(result, *inner_args, **inner_kwargs)
                return result.format(*inner_args, **inner_kwargs)
        if result is None:
            if allow_failure:
                return '<Translation failed>'
            raise KeyError(
                        'Failed to translate from dict with translations {}, language {}, fallback_language {}'.format(
                            translation_dict, language, ', '.join(fallback_language)))

    return RTextMCDRTranslation('', *args, **kwargs).set_translator(fake_tr)


logger: BlossomLogger = BlossomLogger.get_instance()
