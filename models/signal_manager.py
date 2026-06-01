from __future__ import annotations
import models
from typing import Dict, Callable, Any, List, Tuple

signals : Dict[str, List[Tuple[models.amadeus_plugin.AmadeusPlugin, Callable[..., Any]]]] = {}


def register_signal(name: str, plugin: models.amadeus_plugin.AmadeusPlugin, handler: Callable[..., Any]):
    if name not in signals:
        signals[name] = []
    signals[name].append((plugin, handler))


async def emit_signal(name: str, *args, **kwargs):
    handlers = signals.get(name, [])
    for plugin, handler in handlers:
        # Check si le plugin est actif ou, dans le cas d'un message custom, que le plugin soit target ou que le message s'adresse à tout le monde
        if plugin.active and (name != 'on_custom_message' or (args[0].to_plugin is None or args[0].to_plugin == plugin.plugin_name)):
            await handler(*args, **kwargs)