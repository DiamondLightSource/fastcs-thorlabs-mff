from __future__ import annotations

import logging

from fastcs.attributes import AttrR, AttrRW, Polled
from fastcs.controllers import Controller
from fastcs.methods import command

from fastcs_thorlabs_mff.connection import MFFConnection

logger = logging.getLogger(__name__)


class ThorlabsMFF(Controller):
    def __init__(self, connection: MFFConnection):
        super().__init__()
        self.connection = connection

        # Datatypes are inferred from the getters' return annotations
        self.position = AttrRW(
            getter=Polled(connection.get_position, period=0.2),
            setter=connection.set_position,
        )
        # Static device info: read once at connect, and again after a reconnect
        self.model = AttrR(getter=connection.get_model)
        self.device_type = AttrR(getter=connection.get_device_type)
        self.serial_no = AttrR(getter=connection.get_serial_no)
        self.firmware_version = AttrR(getter=connection.get_firmware_version)
        self.hardware_version = AttrR(getter=connection.get_hardware_version)

    @command()
    async def blink_led(self) -> None:
        logger.info("Sending blink LED command")
        await self.connection.identify()
