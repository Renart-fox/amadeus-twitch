import socketio, requests, asyncio
from models.amadeus_plugin import AmadeusPlugin
from models.decorators import on_load, on_custom_message, CustomMessage, on_chat_message
from models.signal_manager import emit_signal
from models.globals import set_global, get_global
from config.amadeus_config import Amadeus_Config


from twitchAPI.twitch import Twitch


PLUGIN_NAME = "websocket"


class Websocket(AmadeusPlugin):
    
    plugin_name = PLUGIN_NAME
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins="*",
        logger=False
    )
    connected_applications = []


    def __init__(self) -> None:
        super().__init__()

        self.write_config(overwrite=False)
        self.read_config()

        if self.active:
            fastpi_app = get_global('fastapi_app')
            app = socketio.ASGIApp(self.sio, fastpi_app)
            set_global('socketio_app', app)


    @sio.event
    async def connect(sid, environ, auth):
        print('Frontend connected with sid ', sid)

    @sio.event
    async def disconnect(sid, reason):
        print('Frontend disconnected with sid ', sid, reason)


    @on_chat_message
    async def on_chat_message(self, message):
        await self.sio.emit('chat_message', {
            'user': message.user.name,
            'message': message.text
        })


exported_class = Websocket