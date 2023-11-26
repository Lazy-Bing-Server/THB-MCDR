import json
import os.path
import time

from lazybing_thb.location import Location
from lazybing_thb.storage.abstract_player_storage import AbstractPlayerStorage


class History(Location):
    timestamp: float
    warned = False

    @classmethod
    def from_coordinates(cls, coordinates: Location):
        data = coordinates.serialize()
        data = data.copy()
        if 'timestamp' not in data.keys():
            data['timestamp'] = time.time()
        return cls.deserialize(data)


class TeleportHistory(AbstractPlayerStorage):
    @classmethod
    def get_folder_name(cls):
        return "history"

    def file_path(self):
        return os.path.join(self.get_folder_path(), f"{self.player}.json")

    def save(self, data: History):
        with self.open('w') as f:
            return json.dump(data.serialize(), f, ensure_ascii=False, indent=4)

    def set_location(self, coordinates: Location):
        self.save(History.from_coordinates(coordinates))

    def get_history(self):
        with self.lock():
            self.ensure_file()
            if not self.exists():
                return None
            with self.open() as f:
                return History.deserialize(json.load(f))

    def set_warned(self):
        with self.lock():
            history = self.get_history()
            history.warned = False
            self.save(history)
