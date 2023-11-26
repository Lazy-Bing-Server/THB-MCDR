from typing import Union

from mcdreforged.utils.serializer import Serializable
from minecraft_data_api import get_player_coordinate, get_player_dimension
from lazybing_thb.storage.config import config
from lazybing_thb.utils import psi, logger

Number = Union[int, float]
dim_convert = {
    0: 'minecraft:overworld',
    -1: 'minecraft:the_nether',
    1: 'minecraft:the_end'
}


class Location(Serializable):
    x: Number
    y: Number
    z: Number
    dim: Union[int, str]  # Get from minecraft data api

    @classmethod
    def deserialize(cls, data: dict, **kwargs):
        if isinstance(data['dim'], int) and not data['dim'] in [-1, 0, 1]:
            raise ValueError("Invalid integer value found for dimensions")
        return super().deserialize(data, **kwargs)

    def get_dim_name(self):
        dim = dim_convert.get(self.dim, self.dim)
        logger.debug(f"Location dimension converted: {dim}")
        return dim

    @classmethod
    def get_location(cls, player: str):
        if psi.is_on_executor_thread():
            raise RuntimeError("Illegal call on Executor threads")
        coordinate = get_player_coordinate(player, timeout=config.mda_timeout)
        dimension = get_player_dimension(player, timeout=config.mda_timeout)
        return cls.deserialize(
            dict(
                x=coordinate.x, y=coordinate.y, z=coordinate.z,
                dim=dimension
            )
        )
