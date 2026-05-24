from typing import Dict, Any
from twitchAPI.chat import Chat

globals : Dict[str, Any] = {
}

def set_global(key: str, value: Any):
    globals[key] = value


def get_global(key: str):
    return globals.get(key)