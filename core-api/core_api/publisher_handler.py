from faststream.redis import RedisBroker

from redbox.models import File


class FilePublisher:
    """This class is a bit of a hack to overcome a shortcoming (bug?) in faststream
    whereby the broker is not automatically connected in sub-applications.

    TODO: fix this properly, or raise an issue against faststream
    """

    def __init__(self, broker: RedisBroker, queue_name: str):
        self.connected = False
        self.broker = broker
        self.queue_name = queue_name

    async def publish(self, file: File):
        if not self.connected:
            # we only do this once
            await self.broker.connect()
            self.connected = True
        await self.broker.publish(file, list=self.queue_name)
