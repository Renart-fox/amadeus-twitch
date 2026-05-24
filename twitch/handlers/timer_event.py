import threading
import asyncio
from twitch.handlers.handler import Handler


class TimerEventHandler(Handler):
    def __init__(self, config: str, timer: int, kwargs: dict = {}) -> None:
        super().__init__(config)
        self.timer = timer
        self.kwargs = kwargs
        threading.Timer(self.timer, self.call_process_from_timer).start()


    def call_process_from_timer(self):
        asyncio.run(self.process())


    async def process(self, kwargs: dict = {}):
        await super().process(self.kwargs)
        threading.Timer(self.timer, self.call_process_from_timer).start()