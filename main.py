import json, asyncio, threading
import datetime

import importlib.util
import sys
from pathlib import Path

from pathlib import PurePath

from config.amadeus_config import Amadeus_Config, USER_CONFIG_DIR
from obs.obs_manager import OBS_Manager
from utils import tools

from twitch.handlers.event_manager import process_events, add_event, register_handler, set_chat
from twitch.handlers.handler import Handler
from twitch.handlers.timer_event import TimerEventHandler

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.helper import first
from twitchAPI.chat import Chat, EventData, ChatCommand, ChatMessage
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.object.eventsub import ChannelPointsCustomRewardRedemptionAddEvent, ChannelRaidEvent, ChannelRaidData, ChannelFollowEvent, ChannelFollowData, ChannelSubscribeEvent, ChannelSubscribeData
from twitchAPI.object.eventsub import ChannelPointsCustomRewardRedemptionData, Reward

from obswebsocket import obsws, requests

import uvicorn
from fastapi import FastAPI

from pydantic_ai import Agent, BinaryContent, RunContext
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.providers.anthropic import AnthropicProvider

import speech_recognition as sr
import pyaudio

from contextlib import asynccontextmanager

from models.globals import set_global, get_global
from models.signal_manager import emit_signal


@asynccontextmanager
async def lifespan(app: FastAPI):
    twitch_backend_thread = threading.Thread(target=asyncio.run, args=(run_twitch_backend(),), daemon=True)
    event_thread = threading.Thread(target=asyncio.run, args=(process_events(),), daemon=True)
    twitch_backend_thread.start()
    event_thread.start()
    yield

app = FastAPI(lifespan=lifespan)
    

amadeus_config = Amadeus_Config()

# ToDo : Transformer en plugin
obs_manager = OBS_Manager(amadeus_config.obs_host, amadeus_config.obs_port, amadeus_config.obs_password)

"""
current_scene_name = obs_manager.get_current_scene_name()
scene_items = obs_manager.get_scene_item_list(current_scene_name)

webcam_scene_item_id = ''
for item in scene_items:
    if item['sourceName'] == 'Webcam':
        webcam_scene_item_id = item['sceneItemId']

for item in scene_items:
    if 'Texte (GDI+)' in item['sourceName']:
        text_id = item['sceneItemId']
        res = obs_manager.get_scene_item_transform(current_scene_name, text_id)
        print(res)
        obs_manager.set_scene_item_transform(current_scene_name, text_id, {
            'positionX': 1920//2,
            'positionY': 1080//2,
            'alignment': 0
        })


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
"""

def load_plugins():
    """Discover and instantiate all plugins from the plugins folder."""
    plugins_dir = Path(__file__).parent / "plugins"
    plugin_instances = {}

    # Find all plugin.py files in subfolders
    for plugin_file in plugins_dir.glob("*/plugin.py"):
        plugin_folder = plugin_file.parent
        plugin_name = plugin_folder.name

        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(
            f"plugins.{plugin_name}.plugin",
            plugin_file
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"plugins.{plugin_name}.plugin"] = module
        spec.loader.exec_module(module)

        # Get the exported_class and instantiate it
        if hasattr(module, "exported_class"):
            exported_class = getattr(module, "exported_class")
            instance = exported_class()
            plugin_instances[plugin_name] = instance
            print(f"Loaded plugin: {plugin_name} -> {exported_class.__name__}")
        else:
            print(f"Plugin {plugin_name} has no exported_class attribute")

    return plugin_instances


async def on_chat_ready(event: EventData):
    print("Chat is ready!")
    await event.chat.join_room(amadeus_config.target_channel)

    await asyncio.sleep(5)  # Attendre que le chat soit complètement prêt avant d'émettre le signal

    await set_chat(event.chat)
    await emit_signal("on_load")


async def on_message(msg: ChatMessage):
    set_global('chat', msg.chat)
    await emit_signal("on_chat_message", msg)


async def on_follow(event: ChannelFollowEvent):
    await add_event(event)
    await emit_signal("on_follow")


async def on_prout(cmd: ChatCommand):
    await cmd.reply('Ca pue')

    audio_duration = tools.get_audio_duration('F:\\Twitch\\Amadeus\\assets\\sounds\\Fart with reverb sound effect.wav')

    audio_input_id, audio_scene_item_id = obs_manager.create_input(
        scene_name=obs_manager.get_current_scene_name(),
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

    obs_manager.remove_input(obs_manager.get_current_scene_name(), item_id=audio_scene_item_id)

"""
async def on_tourne(cmd: ChatCommand):
    await rotate_camera(webcam_scene_item_id)
"""

async def on_discord(cmd: ChatCommand):
    global chat
    await chat.send_message('mielikki_fox', 'https://discord.gg/He5aJyPhwt')


async def on_gsh(cmd: ChatCommand):
    global chat
    await chat.send_message('mielikki_fox', """
                            Du 4 au 7 juin, je serai en live pendant le Game Stream Heroes !
                            C'est un événement caritatif pour soutenir l'association Petits Princes, qui réalise les rêves d'enfants gravement malades.
                            Au programme: Undertale, Silksong, Cyberpunk 2077, du JdR, et plein d'autres choses !
                            """)


async def on_reward_redeemed(event: ChannelPointsCustomRewardRedemptionAddEvent):
    print(event)
    await add_event(event)


async def on_raid(event: ChannelRaidEvent):
    await add_event(event)


async def on_goals(cmd: ChatCommand):
    c = ChannelPointsCustomRewardRedemptionAddEvent()
    c.event = ChannelPointsCustomRewardRedemptionData()
    c.event.reward = Reward()
    c.event.user_input = ''
    c.event.reward.title = 'Donation Goals'
    
    await add_event(c)


async def run_twitch_backend():
    global chat

    print('===============================')
    print('Connecting to Twitch main channel account...')
    print('===============================')
    twitch = await Twitch(amadeus_config.client_id, amadeus_config.client_secret, authenticate_app=True, target_app_auth_scope=amadeus_config.scopes)
    helper = UserAuthenticationStorageHelper(twitch, amadeus_config.scopes, storage_path=PurePath(USER_CONFIG_DIR, './streamer_auth.json'))
    await helper.bind()

    print('===============================')
    print('Connecting to Twitch bot channel account...')
    print('===============================')
    twitch_bot = await Twitch(amadeus_config.client_id, amadeus_config.client_secret, authenticate_app=True, target_app_auth_scope=amadeus_config.scopes)
    helper_bot = UserAuthenticationStorageHelper(twitch_bot, amadeus_config.scopes, storage_path=PurePath(USER_CONFIG_DIR, './bot_auth.json'))
    await helper_bot.bind()

    chat = await Chat(twitch_bot)
    set_global('chat', chat)

    user = None

    async for u in twitch.get_users(logins=[amadeus_config.target_channel]):
        user = u

    eventsub = EventSubWebsocket(twitch)
    eventsub.start()
    await eventsub.listen_channel_points_custom_reward_redemption_add(user.id, on_reward_redeemed) # type: ignore
    await eventsub.listen_channel_raid(to_broadcaster_user_id=user.id, callback=add_event) # type: ignore
    await eventsub.listen_channel_follow_v2(broadcaster_user_id=user.id, moderator_user_id=user.id, callback=add_event) # type: ignore
    await eventsub.listen_channel_subscribe(broadcaster_user_id=user.id, callback=add_event) # type: ignore

    chat.register_event(ChatEvent.READY, on_chat_ready)

    chat.register_event(ChatEvent.MESSAGE, on_message)

    chat.register_command('prout', on_prout)
    chat.register_command('gsh', on_gsh)
    chat.register_command('discord', on_discord)
    chat.register_command('goals', on_goals)
    #chat.register_command('tourne', on_tourne)

    chat.start()

    raid_hardsquare_handler = Handler('''
        - send_message:
            text: "Merci {raider} pour le raid !"
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
        - show_text:
            text: "{raider}\\nvient de tuer {viewers} personnes !!!"
        - transform:
            input: "{text_0}"
            settings:
                positionX: 960
                positionY: 540
                alignment: 0
        - wait:
            duration: "{video_0_duration}"
        - remove_input:
            item: "{video_0}"
        - remove_input:
            item: "{audio_0}"
        - remove_input:
            item: "{text_0}"
                                      ''')

    default_raid_handler = Handler('''
        - send_message:
            text: "Merci {raider} pour le raid !"
        - play_video:
            video : "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\videos\\\\tv_time.mp4"
            volume: -10.0
        - show_text:
            text: "{raider}\\narrive avec {viewers} personnes !!!"
        - add_filter:
            filter: "green screen"
            input_uuid : "{video_0_uuid}"
        - transform:
            input: "{text_0}"
            settings:
                positionX: 960
                positionY: 540
                alignment: 0
        - wait:
            duration: "{video_0_duration}"
        - remove_input:
            item: "{video_0}"
        - remove_input:
            item: "{text_0}"
                                   ''')
    
    default_follow_handler = Handler('''
        - play_video:
            video : "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\videos\\\\mayuri_wave.gif"
            volume: -20.0
            loop: True
        - play_sound:
            sound: "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\sounds\\\\Tuturu - Sound Effect (HD).mp3"
            volume: -30.0
        - transform:
            input: "{video_0}"
            settings:
                positionX: 960
                positionY: 300
                alignment: 0
        - show_text:
            text: "Merci {user} pour le follow !!!"
        - send_message:
            text: "Merci {user} pour le follow !"
        - transform:
            input: "{text_0}"
            settings:
                positionX: 960
                positionY: 540
                alignment: 0
        - wait:
            duration: "{audio_0_duration}"
        - remove_input:
            item: "{video_0}"
        - remove_input:
            item: "{audio_0}"
        - remove_input:
            item: "{text_0}"
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
    
    tts_handler = Handler('''
        - text_to_speech:
            text: "{user_message}"
        - play_sound:
            sound: "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\sounds\\\\output_reverb.mp3"
        - wait:
            duration: "{audio_0_duration}"
        - remove_input:
            item: "{audio_0}"
    ''')

    message_gsh = TimerEventHandler('''
        - play_video:
            video : "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\videos\\\\spot GSH 2026 HQ.gif"
            volume: -10.0
        - transform:
            input: "{video_0}"
            settings:
                positionX: 960
                positionY: 0
                alignment: 4
        - send_message:
            text: >
                    Du 4 au 7 juin, je serai en live pendant le Game Stream Heroes !
                    C'est un événement caritatif pour soutenir l'association Petits Princes, qui réalise les rêves d'enfants gravement malades.
                    Au programme: Undertale, Silksong, Cyberpunk 2077, du JdR, et plein d'autres choses !
        - wait:
            duration: "{video_0_duration}"
        - remove_input:
            item: "{video_0}"
    ''', 3600, {
        'chat': chat
    })
    
    default_sub_handler = Handler('''
        - play_video:
            video : "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\videos\\\\Makise.Kurisu.full.2733824.gif"
            volume: -20.0
            loop: True
        - play_sound:
            sound: "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\sounds\\\\Zone Clear - Sonic Pinball Party.mp3"
            volume: -30.0
        - transform:
            input: "{video_0}"
            settings:
                positionX: 710
                positionY: 150
        - show_text:
            text: "Merci {user} pour le sub !!!"
        - send_message:
            text: "Merci {user} pour le sub !"
        - transform:
            input: "{text_0}"
            settings:
                positionX: 240
                positionY: 600
        - wait:
            duration: "{audio_0_duration}"
        - remove_input:
            item: "{video_0}"
        - remove_input:
            item: "{audio_0}"
        - remove_input:
            item: "{text_0}"
                                  ''')

    donation_goals_handler = Handler('''
        - show_image:
            image: "F:\\\\Twitch\\\\Amadeus\\\\assets\\\\videos\\\\donation_goals.png"
        - wait:
            duration: 20
        - remove_input:
            item: "{image_0}"
                                     ''')

    await register_handler('raid', raid_hardsquare_handler, 'HardSquare')
    await register_handler('raid', default_raid_handler, 'default')
    await register_handler('follow', default_follow_handler, 'default')
    await register_handler('sub', default_sub_handler, 'default')
    await register_handler('command', orson_welles_handler, 'Orson Welles')
    await register_handler('command', tts_handler, 'TTS')
    await register_handler('command', donation_goals_handler, 'Donation Goals')
    

    await on_follow(None)

    """
    await asyncio.sleep(5)
    c = ChannelRaidEvent()
    c.event = ChannelRaidData()
    c.event.from_broadcaster_user_name = 'HardSquare'
    c.event.to_broadcaster_user_id = '181464807'
    c.event.from_broadcaster_user_id = '423130163'
    c.event.viewers = 69
    await on_raid(c)
    """
    
    """
    c = ChannelFollowEvent()
    c.event = ChannelFollowData()
    c.event.user_name = 'BravoLesRolistesDu79'
    await on_follow(c)
    """
    """
    c = ChannelSubscribeEvent()
    c.event = ChannelSubscribeData()
    c.event.user_name = 'flumble3'
    await add_event(c)
    """
    """
    try:
        input('press ENTER to stop\n')
    finally:
        chat.stop()
        await eventsub.stop()
        await twitch.close()
    """

if __name__ == "__main__":
    print('========================================')
    print('PLUGINS')
    print('========================================')
    set_global('plugin_instances', load_plugins())
    print('========================================')
    print('AMADEUS SERVER')
    print('========================================')
    uvicorn.run(app, host="localhost", port=8080)