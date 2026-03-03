from typing import List, Any, Dict
import queue
from twitchAPI.chat import Chat
from twitch.handlers.handler import Handler

events : queue.Queue[Any] = queue.Queue()
chat: Chat = None # type: ignore

"""_summary_
raid:
    default:
        Handler
    hardsquare:
        Handler
    jackchiwace:
        Handler
follow:
    default:
        Handler
    ...
command:
    tts:
        Handler
"""
handlers : Dict[str, Dict[str, Handler]] = {}

async def add_event(event: Any):
    print(f'Adding event type "{type(event)}"')
    events.put(event)


async def register_handler(event_type: str, handler: Handler, handler_name: str = "default"):
    if event_type not in handlers:
        handlers[event_type] = {}
    handlers[event_type][handler_name] = handler


async def set_chat(t_chat: Chat):
    global chat
    chat = t_chat


async def process_events():
    print("Processing events...")
    while True:
        event = events.get()
        print(f'Got event type "{type(event)}"')
        handler = None
        kwargs = {}
        match type(event).__name__:
            case 'ChannelRaidEvent':
                await chat.twitch.send_a_shoutout(event.event.to_broadcaster_user_id, event.event.from_broadcaster_user_id, event.event.to_broadcaster_user_id)
                event_type = 'raid'
                broadcaster_user_name = event.event.from_broadcaster_user_name
                kwargs = {
                    'raider': event.event.from_broadcaster_user_name,
                    'viewers': event.event.viewers,
                    'chat': chat
                }
                handler = handlers.get(event_type, {}).get(broadcaster_user_name) or handlers.get(event_type, {}).get("default")
            case 'ChannelFollowEvent':
                event_type = 'follow'
                kwargs = {
                    "user": event.event.user_name,
                }
                handler = handlers.get(event_type, {}).get("default")
            case 'ChannelPointsCustomRewardRedemptionAddEvent':
                event_type = 'command'
                kwargs = {
                    'user_message': event.event.user_input
                }
                handler = handlers.get(event_type, {}).get(event.event.reward.title)
            case _:
                print(f'Unknown event type "{type(event)}"')
                continue
        await handler.process(kwargs) # type: ignore