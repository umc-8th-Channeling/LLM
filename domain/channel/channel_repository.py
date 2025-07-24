from core.database.model.channel import Channel
from core.database.repository.crud_repository import CRUDRepository


class ChannelRepository(CRUDRepository[Channel]):
    def model_class(self) -> type[Channel]:
        return Channel
