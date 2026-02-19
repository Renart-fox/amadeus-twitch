import json
import asyncio
import uuid

from config.amadeus_config import Amadeus_Config
from obs.obs_manager import OBS_Manager
from utils.tools import get_audio_duration

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.helper import first
from twitchAPI.chat import Chat, EventData, ChatCommand, ChatMessage
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.object.eventsub import ChannelPointsCustomRewardRedemptionAddEvent, ChannelRaidEvent

from obswebsocket import obsws, requests



amadeus_config = Amadeus_Config('config.yaml')
obs_manager = OBS_Manager(amadeus_config.obs_host, amadeus_config.obs_port, amadeus_config.obs_password)


current_scene_name = obs_manager.get_current_scene_name()
scene_items = obs_manager.get_scene_item_list(current_scene_name)

webcam_scene_item_id = ''
for item in scene_items:
    if item['sourceName'] == 'Webcam':
        webcam_scene_item_id = item['sceneItemId']


async def rotate_camera(uuid):
    res = obs_manager.get_scene_item_transform(current_scene_name, uuid)
    base_rot = int(res['rotation'])
    i = base_rot + 1

    while i != base_rot:
        await asyncio.sleep(0.01)
        obs_manager.set_scene_item_transform(current_scene_name, uuid, {
            'rotation': i
        })
        res = obs_manager.get_scene_item_transform(current_scene_name, uuid)
        i = int(res['rotation']) + 1
        if i == base_rot:
            break
        if i >= 270:
            i = -90

    obs_manager.set_scene_item_transform(current_scene_name, uuid, {
        'rotation': base_rot
    })


DASHBOARD_SCOPES = [AuthScope.CHAT_READ,
                    AuthScope.CHAT_EDIT,
                    AuthScope.CHANNEL_READ_REDEMPTIONS,
                    AuthScope.CHANNEL_MANAGE_REDEMPTIONS
                    ]
TARGET_CHANNEL = 'mielikki_fox'


with open("tokens.json", "r") as f:
    tokens = json.load(f)
    client_id = tokens["client_id"]
    client_secret = tokens["client_secret"]


async def on_chat_ready(event: EventData):
    print("Chat is ready!")
    await event.chat.join_room(TARGET_CHANNEL)


async def on_message(msg: ChatMessage):
    print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}') # type: ignore


async def on_prout(cmd: ChatCommand):
    await cmd.reply('Ca pue')

    audio_duration = get_audio_duration('F:\\Twitch\\Amadeus\\assets\\sounds\\Fart with reverb sound effect.wav')

    input_name = obs_manager.create_input(
        scene_name=current_scene_name,
        input_kind="ffmpeg_source",
        input_settings={
            "local_file": 'F:\\Twitch\\Amadeus\\assets\\sounds\\Fart with reverb sound effect.wav',
            "is_local_file": True,
            "looping": False
        }
    )
    obs_manager.set_volume(
        input_name=input_name,
        volume=-20.0
    )

    obs_manager.set_input_audio_monitor_type(
        input_name=input_name,
        monitor_type='OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT'
    )

    await asyncio.sleep(audio_duration)

    obs_manager.remove_input(input_name=input_name)


async def on_tourne(cmd: ChatCommand):
    await rotate_camera(webcam_scene_item_id)


async def on_reward_redeemed(event: ChannelPointsCustomRewardRedemptionAddEvent):
    if event.event.reward.title == 'Orson Welles':
        with open(f'F:\\Twitch\\Superpositions\\queue\\{uuid.uuid4()}.json', 'w') as f:
            json.dump({
                'user': event.event.user_name,
                'action': 'Orson Welles',
                'message': ''
            }, f)


async def on_raid(event: ChannelRaidEvent):
    match event.event.from_broadcaster_user_name:
        case 'HardSquare':
            pass
        case 'JackChiwac':
            pass
        case _:
            pass


async def run():
    twitch = await Twitch(client_id, client_secret)
    helper = UserAuthenticationStorageHelper(twitch, DASHBOARD_SCOPES)
    await helper.bind()

    chat = await Chat(twitch)

    user = None

    async for u in twitch.get_users(logins=['mielikki_fox']):
        user = u

    eventsub = EventSubWebsocket(twitch)
    eventsub.start()
    await eventsub.listen_channel_points_custom_reward_redemption_add(user.id, on_reward_redeemed) # type: ignore
    await eventsub.listen_channel_raid(to_broadcaster_user_id=user.id, callback=on_raid) # type: ignore

    chat.register_event(ChatEvent.READY, on_chat_ready)

    chat.register_event(ChatEvent.MESSAGE, on_message)

    chat.register_command('prout', on_prout)
    chat.register_command('tourne', on_tourne)

    chat.start()

    try:
        input('press ENTER to stop\n')
    finally:
        chat.stop()
        await eventsub.stop()
        await twitch.close()


if __name__ == "__main__":

    asyncio.run(run())