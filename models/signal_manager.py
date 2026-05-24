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
        if plugin.active:
            await handler(*args, **kwargs)