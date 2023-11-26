import os.path
import shutil
from typing import Optional

from lazybing_thb.storage.abstract_player_storage import AbstractPlayerStorage


class TeleportRequest(AbstractPlayerStorage):
    @classmethod
    def get_folder_name(cls):
        return "tpa"

    def get_file_path(self):
        return os.path.join(self.get_folder_path(), f"{self.player}.tpa")

    def set_requester(self, requester: str):
        with self.open('w') as f:
            f.write(requester)

    def get_requester(self) -> Optional[str]:
        with self.lock():
            if not self.exists():
                return None
            with self.open() as f:
                return f.read()

    @classmethod
    def remove_all_files(cls):
        if os.path.exists(cls.get_folder_path()):
            shutil.rmtree(cls.get_folder_path())
        cls.resolve_dir()
