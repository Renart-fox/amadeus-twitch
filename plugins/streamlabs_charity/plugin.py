import socketio, requests, asyncio
from models.amadeus_plugin import AmadeusPlugin
from models.decorators import on_load, on_custom_message, CustomMessage
from models.signal_manager import emit_signal
from models.globals import set_global, get_global
from config.amadeus_config import Amadeus_Config


from twitchAPI.twitch import Twitch


from threading import Thread


from .streamlabs_db import Streamlabs_DB


PLUGIN_NAME = "streamlabs_charity"

class StreamlabsCharity(AmadeusPlugin):

    plugin_name = PLUGIN_NAME
    sio = socketio.Client()


    def __init__(self) -> None:
        super().__init__()

        self.config_parser.set(self.plugin_name, 'access_token', '')

        self.write_config(overwrite=False)
        self.read_config()

        if self.active:
            self.db = Streamlabs_DB(self.plugin_name, self.config_parser)
            self.sio.on("event", self.on_event)

    
    @on_load
    async def on_load(self):
        thread = Thread(name='streamlabs_ws', target=self.handle_ws, daemon=True)
        thread.start()


    @sio.event
    def connect():
        print("Connected to Streamlabs WebSocket!")

    @sio.event
    def disconnect():
        print("Disconnected from Streamlabs WebSocket")

    @sio.event
    def connect_error(data):
        print("Connection failed:", data)

    def on_event(self, data):
        if data['type'] == 'streamlabscharitydonation':
            donation_to = data['message'][0]['name']
            if donation_to == Amadeus_Config().target_channel:
                don_info = {
                    'type': 'new_donation',
                    'donation_amount_formatted' : data['message'][0]['formattedAmount'],
                    'donation_amount' : data['message'][0]['amount'],
                    'donation_from' : data['message'][0]['from'],
                    'donation_from_twitchname' : data['message'][0]['twitchDisplayName']
                }
                c = CustomMessage(from_plugin=PLUGIN_NAME, data=don_info)
                twitch_bot: Twitch = get_global('twitch_bot')
                self.db.add_donation(don_info['donation_from'], don_info['donation_amount'])
                asyncio.run(twitch_bot.send_chat_announcement('181464807', '1232194164', f"ALERTE !!! Nous venons de recevoir un don de {don_info['donation_amount_formatted']} de la part de {don_info['donation_from']} pour les Petits Princes !!!!!!!!!"))
                asyncio.run(emit_signal('on_custom_message', c))


    def get_socket_token(self):
        url = "https://streamlabs.com/api/v2.0/socket/token"

        headers = {
            "Authorization": f"Bearer {self.config_parser[self.plugin_name]['access_token']}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print("Error getting socket token:")
            print(response.text)
            return None

        return response.json()


    def handle_ws(self):
        socket_data = self.get_socket_token()
        socket_token = socket_data['socket_token'] # type: ignore
        url = f"https://sockets.streamlabs.com?token={socket_token}"
        self.sio.connect(url, retry=True)
        self.sio.wait()

    
    @on_custom_message
    async def on_custom_message(self, message: CustomMessage):
        if message.data['type'] == 'get_session_donations':
            session_donations = self.db.get_all_donations_for_current_session()
            c = CustomMessage(self.plugin_name, {'type': 'session_donations', 'donations': session_donations})
            await emit_signal('on_custom_message', c)



exported_class = StreamlabsCharity