from typing import List
import json, asyncio, uuid, threading

from config.amadeus_config import Amadeus_Config
from obs.obs_manager import OBS_Manager
from utils import tools

from twitch.handlers.event_manager import process_events, add_event, register_handler
from twitch.handlers.handler import Handler

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.helper import first
from twitchAPI.chat import Chat, EventData, ChatCommand, ChatMessage
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.object.eventsub import ChannelPointsCustomRewardRedemptionAddEvent, ChannelRaidEvent, ChannelRaidData, ChannelFollowEvent, ChannelFollowData

from obswebsocket import obsws, requests

import uvicorn
from fastapi import FastAPI


app = FastAPI()

amadeus_config = Amadeus_Config('config.yaml')
obs_manager = OBS_Manager().get_instance(amadeus_config.obs_host, amadeus_config.obs_port, amadeus_config.obs_password)


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


DASHBOARD_SCOPES = [
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.CHANNEL_READ_REDEMPTIONS,
    AuthScope.CHANNEL_MANAGE_REDEMPTIONS,
    AuthScope.MODERATOR_READ_FOLLOWERS,
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
    AuthScope.CHANNEL_MODERATE
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


async def on_follow(event: ChannelFollowEvent):
    await add_event(event)


async def on_prout(cmd: ChatCommand):
    await cmd.reply('Ca pue')

    audio_duration = tools.get_audio_duration('F:\\Twitch\\Amadeus\\assets\\sounds\\Fart with reverb sound effect.wav')

    audio_input_id, audio_scene_item_id = obs_manager.create_input(
        scene_name=current_scene_name,
        input_kind="ffmpeg_source",
        input_settings={
            "local_file": 'F:\\Twitch\\Amadeus\\assets\\sounds\\Fart with reverb sound effect.wav',
            "is_local_file": True,
            "looping": False
        }
    )
    obs_manager.set_volume(
        input_id=audio_input_id,
        volume=-20.0
    )

    obs_manager.set_input_audio_monitor_type(
        input_id=audio_input_id,
        monitor_type='OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT'
    )

    await asyncio.sleep(audio_duration)

    obs_manager.remove_input(current_scene_name,item_id=audio_scene_item_id)


async def on_tourne(cmd: ChatCommand):
    await rotate_camera(webcam_scene_item_id)


async def on_reward_redeemed(event: ChannelPointsCustomRewardRedemptionAddEvent):
    await add_event(event)


async def on_raid(event: ChannelRaidEvent):
    await add_event(event)


async def run_twitch_backend():
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
    await eventsub.listen_channel_raid(to_broadcaster_user_id=user.id, callback=add_event) # type: ignore
    await eventsub.listen_channel_follow_v2(broadcaster_user_id=user.id, moderator_user_id=user.id, callback=add_event) # type: ignore

    chat.register_event(ChatEvent.READY, on_chat_ready)

    chat.register_event(ChatEvent.MESSAGE, on_message)

    chat.register_command('prout', on_prout)
    chat.register_command('tourne', on_tourne)

    chat.start()

    raid_hardsquare_handler = Handler('''
        - play_video:
            video : "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\videos\\\\Jet crash on green screen.mp4"
            volume: -30.0
        - transform:
            input: "{video_0}"
            settings:
                scaleX: -1.5
                scaleY: 1.5
                positionX: 1920
        - add_filter:
            filter: "green screen"
            input_uuid : "{video_0_uuid}"
        - play_sound:
            sound: "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\sounds\\\\Square_Coucou Miel.wav"
            volume: 0.0
        - wait:
            duration: "{video_0_duration}"
        - remove_input:
            item: "{video_0}"
        - remove_input:
            item: "{audio_0}"
                                      ''')
    
    default_follow_handler = Handler('''
        - play_video:
            video : "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\videos\\\\Makise.Kurisu.full.2733824.gif"
            volume: -20.0
            loop: True
        - play_sound:
            sound: "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\sounds\\\\Zone Clear - Sonic Pinball Party.mp3"
            volume: -20.0
        - wait:
            duration: "{audio_0_duration}"
        - remove_input:
            item: "{video_0}"
        - remove_input:
            item: "{audio_0}"
                                      ''')
    
    orson_welles_handler = Handler('''
        - screenshot:
            scene: global
        - show_image:
            image: "{screenshot}"
        - play_video:
            video: "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\videos\\\\orsonwelles.mov"
            volume: -10.0
        - wait:
            duration: "{video_0_duration}"
        - remove_input:
            item: "{image_0}"
        - remove_input:
            item: "{video_0}"
                                   ''')

    await register_handler('raid', raid_hardsquare_handler, 'HardSquare')
    await register_handler('follow', default_follow_handler, 'default')
    await register_handler('command', orson_welles_handler, 'Orson Welles')

    c = ChannelRaidEvent()
    c.event = ChannelRaidData()
    c.event.from_broadcaster_user_name = 'HardSquare'
    c.event.viewers = 69
    await on_raid(c)
    """
        c = ChannelRaidEvent()
        c.event = ChannelRaidData()
        c.event.from_broadcaster_user_name = 'HardSquare'
        c.event.viewers = 69
        await on_raid(c)

        c = ChannelFollowEvent()
        c.event = ChannelFollowData()
        c.event.user_name = 'ehfioleazfhaolifhapiolfnhalmf'
        await on_follow(c)
    """

    try:
        input('press ENTER to stop\n')
    finally:
        chat.stop()
        await eventsub.stop()
        await twitch.close()


if __name__ == "__main__":
    twitch_backend_thread = threading.Thread(target=asyncio.run, args=(run_twitch_backend(),))
    event_thread = threading.Thread(target=asyncio.run, args=(process_events(),))
    twitch_backend_thread.start()
    event_thread.start()
    twitch_backend_thread.join()
    event_thread.join()