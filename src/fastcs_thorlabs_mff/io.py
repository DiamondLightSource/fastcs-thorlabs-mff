from __future__ import annotations

import logging
from dataclasses import dataclass

from fastcs.attributes import AttributeIO, AttributeIORef, AttrW

from fastcs_thorlabs_mff import protocol
from fastcs_thorlabs_mff.connection import APTConnection

logger = logging.getLogger(__name__)


@dataclass
class MFFPositionIORef(AttributeIORef):
    """Writes to the flipper position. Readback comes from the status scan."""


class MFFPositionIO(AttributeIO[bool, MFFPositionIORef]):
    def __init__(self, connection: APTConnection):
        super().__init__()
        self.connection = connection

    async def send(self, attr: AttrW[bool, MFFPositionIORef], value: bool) -> None:
        logger.info("Moving to position %d", 2 if value else 1)
        await self.connection.send(protocol.move_jog(value))
