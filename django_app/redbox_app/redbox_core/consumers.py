import logging
from time import sleep

from channels.generic.websocket import WebsocketConsumer

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ChatConsumer(WebsocketConsumer):

    def receive(self, text_data):
        logger.debug(f"receive {text_data=}")
        self.send("Hello")
        sleep(.5)
        self.send(" world.")
