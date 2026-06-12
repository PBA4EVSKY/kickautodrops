"""Lightweight pub/sub event bus. Decouples core logic from display layer."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Awaitable, Callable


class EventType(Enum):
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    CONNECTION = auto()
    PROGRESS = auto()
    DROP_STATUS = auto()


@dataclass
class Event:
    type: EventType
    message: str
    timestamp: float = field(default_factory=time.time)
    data: dict | None = None


Subscriber = Callable[["Event"], Awaitable[None]]
_subscribers: list[Subscriber] = []
_pending_tasks: set[asyncio.Task] = set()


def subscribe(callback: Subscriber) -> None:
    """Register an async callback to receive all events."""
    if callback not in _subscribers:
        _subscribers.append(callback)


def unsubscribe(callback: Subscriber) -> None:
    """Remove a previously registered callback."""
    if callback in _subscribers:
        _subscribers.remove(callback)


async def _run_subscriber(cb: Subscriber, event: "Event") -> None:
    """Invoke a subscriber, surfacing failures instead of swallowing them."""
    try:
        await cb(event)
    except Exception as exc:  # noqa: BLE001 - last-resort guard for one bad subscriber
        print(f"[EVENT-DISPATCH-ERROR] {cb!r}: {exc}")


def emit(event_type: EventType, message: str, data: dict | None = None) -> None:
    """Emit an event to all subscribers. Safe to call from sync or async context.

    When an event loop is running, events are dispatched via
    ``loop.create_task()`` so subscribers run as background tasks.
    When no loop is running (module import, early bootstrap), falls
    back to a plain ``print()``.
    """
    event = Event(type=event_type, message=message, data=data)
    try:
        loop = asyncio.get_running_loop()
        for cb in _subscribers:
            # Keep a strong reference until the task finishes; otherwise the
            # event loop may garbage-collect it mid-flight (see asyncio docs).
            task = loop.create_task(_run_subscriber(cb, event))
            _pending_tasks.add(task)
            task.add_done_callback(_pending_tasks.discard)
    except RuntimeError:
        print(f"[{event_type.name}] {message}")
