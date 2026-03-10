class ThorlabsAPTProtocol:
    def set_identify(self):
        return b"\x23\x02\x00\x00\x50\x01"

    def get_position(self) -> bytes:
        return b"\x29\x04\x00\x00\x50\x01"

    def read_position(self, response: bytes) -> bool:
        return bool(int(response[8]) - 1)

    def set_position(self, desired: bool) -> bytes:
        if desired:
            return b"\x6a\x04\x00\x02\x50\x01"
        else:
            return b"\x6a\x04\x00\x01\x50\x01"

    def get_info(self) -> bytes:
        return b"\x05\x00\x00\x00\x50\x01"

    def read_model(self, response: bytes) -> str:
        return response[10:18].decode("ascii")

    def read_type(self, response: bytes) -> int:
        return int.from_bytes(response[18:20], byteorder="little")

    def read_serial_no(self, response: bytes) -> int:
        return int.from_bytes(response[6:10], byteorder="little")

    def read_firmware_v(self, response: bytes) -> int:
        return int.from_bytes(response[20:24], byteorder="little")

    def read_hardware_v(self, response: bytes) -> int:
        return int.from_bytes(response[84:86], byteorder="little")
