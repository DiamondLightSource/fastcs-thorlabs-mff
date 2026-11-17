import logging

from fastcs_thorlabs_mff.connection import MFFConnection

logger = logging.getLogger(__name__)


class SimMFFConnection(MFFConnection):
    """Simulates the Thorlabs MFF serial interface.

    yaml can't choose this in place of `MFFConnection`, so pass it in Python, e.g.
    ``ControllerSpec("MFF", ThorlabsMFF, connection=SimMFFConnection())``.
    """

    def __init__(self):
        super().__init__(port="SIM")
        self._position: bool = False  # False = position 1, True = position 2

    async def connect(self) -> None:
        logger.info("[SIM] Connected")

    async def close(self) -> None:
        logger.info("[SIM] Disconnected")

    async def write_bytes(self, data: bytes) -> None:
        if data == b"\x23\x02\x00\x00\x50\x01":  # blink_led
            logger.info("[SIM] LED blinking!")
        elif data == b"\x6a\x04\x00\x02\x50\x01":  # move to position 2
            await self._simulate_move(True)
        elif data == b"\x6a\x04\x00\x01\x50\x01":  # move to position 1
            await self._simulate_move(False)

    async def query_bytes(self, data: bytes, size: int) -> bytes:
        if data == b"\x29\x04\x00\x00\x50\x01":  # get_position
            return self._build_position_response()
        elif data == b"\x05\x00\x00\x00\x50\x01":  # get_info
            return self._build_info_response()

        return bytes(size)

    async def _simulate_move(self, target: bool) -> None:
        position_label = "position 2" if target else "position 1"
        logger.debug("[SIM] Moving to %s", position_label)
        self._position = target

    def _build_position_response(self) -> bytes:
        # 12 bytes, position at byte 8: 1=position1 (False), 2=position2 (True)
        response = bytearray(12)
        response[8] = 2 if self._position else 1
        return bytes(response)

    def _build_info_response(self) -> bytes:
        response = bytearray(90)
        response[10:18] = b"MFF101  "  # model
        response[18:20] = (0x1007).to_bytes(2, "little")  # device type
        response[6:10] = (12345678).to_bytes(4, "little")  # serial no
        response[20:24] = (0x010203).to_bytes(4, "little")  # firmware v
        response[84:86] = (3).to_bytes(2, "little")  # hardware v
        return bytes(response)
