"""Bridge callbacks between framework messages and portable protocol handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar


MessageT = TypeVar("MessageT")


@dataclass(slots=True)
class DomainProtocolBridge(Generic[MessageT]):
    """Forward an adapter-decoded message into a domain-layer callback.

    A direct SeQUeNCe ``Protocol`` subclass can own this bridge and call ``deliver``
    from ``received_message``.  The bridge itself remains framework-independent and is
    therefore unit-testable without importing SeQUeNCe.
    """

    logical_node_id: str
    handler: Callable[[str, MessageT], None]

    def deliver(self, source_node_id: str, message: MessageT) -> None:
        """Deliver one decoded message to the registered domain handler."""
        self.handler(source_node_id, message)
