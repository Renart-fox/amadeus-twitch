from typing import Dict

def on_load(func):
    func._signal_name = "on_load"
    return func

def on_chat_message(func):
    func._signal_name = "on_chat_message"
    return func

def on_follow(func):
    func._signal_name = "on_follow"
    return func

def on_custom_message(func):
    func._signal_name = "on_custom_message"
    return func

def on_stream_start(func):
    func._signal_name = "on_stream_start"
    return func

def on_stream_end(func):
    func._signal_name = "on_stream_end"
    return func

def on_stream_update(func):
    func._signal_name = "on_stream_update"
    return func


class CustomMessage:
    from_plugin: str
    to_plugin: str | None
    data: Dict

    def __init__(self, from_plugin: str, data: Dict, to_plugin: str | None = None) -> None:
        self.from_plugin = from_plugin
        self.to_plugin = to_plugin
        self.data = data