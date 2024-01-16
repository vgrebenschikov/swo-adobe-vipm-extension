from typing import Any, Callable, MutableMapping, Sequence

from typing_extensions import Annotated, Doc

from .dataclasses import Event

EventListener = Callable[[Any, Event], None]


class EventsRegistry:
    def __init__(
        self,
    ) -> None:
        self.listeners: MutableMapping[str, EventListener] = {}

    def listener(
        self,
        event_type: Annotated[
            str,
            Doc("Unique identifier of the event type."),
        ],
        /,
    ) -> Callable[[EventListener], EventListener]:
        """
        Unique identifier of the event type.

        ## Example

        ```python
        from swo.mpt.extensions.core import Extension

        ext = Extension()


        @ext.events.listener("orders")
        def process_order(client, event):
            ...
        ```
        """

        def decorator(func: EventListener) -> EventListener:
            self.listeners[event_type] = func
            return func

        return decorator

    def get_listener(
        self,
        event_type: Annotated[
            str,
            Doc("Unique identifier of the event type."),
        ],
    ) -> EventListener | None:
        return self.listeners.get(event_type)

    def get_registered_types(self) -> Sequence[str]:
        return list(self.listeners.keys())

    def is_event_supported(
        self,
        event_type: Annotated[
            str,
            Doc("Unique identifier of the event type."),
        ],
    ) -> bool:
        return event_type in self.listeners
