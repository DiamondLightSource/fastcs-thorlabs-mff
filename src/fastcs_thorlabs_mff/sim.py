import asyncio

from fastcs.connections import SerialConnection, SerialConnectionSettings


class SimSerialConnection(SerialConnection):
    """Simulates the Thorlabs MFF serial interface."""

    def __init__(self):
        self._position: bool = False  # False = pos 1, True = pos 2
        self._moving: bool = False

    async def connect(self, settings: SerialConnectionSettings) -> None:
        print(f"[SIM] Connected (ignoring port {settings.port})")

    async def close(self) -> None:
        print("[SIM] Disconnected")

    async def send_command(self, message: bytes) -> None:
        if message == b"\x6a\x04\x00\x02\x50\x01":  # move to pos 2
            await self._simulate_move(True)
        elif message == b"\x6a\x04\x00\x01\x50\x01":  # move to pos 1
            await self._simulate_move(False)
        # blink_led command is a no-op in sim

    async def send_query(self, message: bytes, response_size: int) -> bytes:
        if message == b"\x29\x04\x00\x00\x50\x01":  # get_position
            return self._build_position_response()
        elif message == b"\x05\x00\x00\x00\x50\x01":  # get_info
            return self._build_info_response()
        return bytes(response_size)

    async def _simulate_move(self, target: bool) -> None:
        self._moving = True
        await asyncio.sleep(0.5)  # MFF flip time ~500ms
        self._position = target
        self._moving = False

    def _build_position_response(self) -> bytes:
        # 12 bytes, position at byte 8: 1=pos1 (False), 2=pos2 (True)
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
