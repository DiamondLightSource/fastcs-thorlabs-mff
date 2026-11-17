from __future__ import annotations

import logging

from fastcs.attributes import AttrR, AttrRW, Polled
from fastcs.controllers import Controller
from fastcs.methods import command

from fastcs_thorlabs_mff.connection import MFFConnection
from fastcs_thorlabs_mff.protocol import ThorlabsAPTProtocol

logger = logging.getLogger(__name__)
protocol = ThorlabsAPTProtocol()

POSITION_RESPONSE_SIZE = 12
INFO_RESPONSE_SIZE = 90


class ThorlabsMFF(Controller):
    def __init__(self, connection: MFFConnection):
        super().__init__()
        self.connection = connection

        # Datatypes are inferred from the getters' return annotations
        self.position = AttrRW(
            getter=Polled(self.get_position, period=0.2),
            setter=self.set_position,
        )
        # Static device info, all from one info query. `model`'s getter makes the
        # query once at connect, and again after a reconnect, and fills in the rest
        self.model = AttrR(getter=self.read_info)
        self.device_type = AttrR(int)
        self.serial_no = AttrR(int)
        self.firmware_version = AttrR(int)
        self.hardware_version = AttrR(int)

    async def get_position(self) -> bool:
        response = await self.connection.query_bytes(
            protocol.get_position(), POSITION_RESPONSE_SIZE
        )
        return protocol.read_position(response)

    async def set_position(self, value: bool) -> None:
        logger.info("Setting position to %s", value)
        await self.connection.write_bytes(protocol.set_position(value))

    async def read_info(self) -> str:
        """Query the device info, update the info attributes and return the model"""
        info = await self.connection.query_bytes(
            protocol.get_info(), INFO_RESPONSE_SIZE
        )
        await self.device_type.update(protocol.read_type(info))
        await self.serial_no.update(protocol.read_serial_no(info))
        await self.firmware_version.update(protocol.read_firmware_v(info))
        await self.hardware_version.update(protocol.read_hardware_v(info))
        return protocol.read_model(info)

    @command()
    async def blink_led(self) -> None:
        logger.info("Sending blink LED command")
        await self.connection.write_bytes(protocol.set_identify())
