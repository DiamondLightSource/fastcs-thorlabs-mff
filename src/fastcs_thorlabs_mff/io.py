from __future__ import annotations

import logging
from dataclasses import dataclass

from fastcs.attributes import AttributeIO, AttributeIORef, AttrW

from fastcs_thorlabs_mff.connection import APTConnection
from fastcs_thorlabs_mff.constants import CHANNEL, MsgId
from fastcs_thorlabs_mff.messages import APTMessage

logger = logging.getLogger(__name__)


@dataclass
class MFFPositionIORef(AttributeIORef):
    """Moves the flipper; the readback comes from the status scan."""


class MFFPositionIO(AttributeIO[bool, MFFPositionIORef]):
    def __init__(self, connection: APTConnection):
        super().__init__()
        self.connection = connection

    async def send(self, attr: AttrW[bool, MFFPositionIORef], value: bool) -> None:
        position = 2 if value else 1
        logger.info("Moving to position %d", position)
        await self.connection.send(APTMessage(MsgId.MOT_MOVE_JOG, CHANNEL, position))
