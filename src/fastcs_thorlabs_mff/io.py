from __future__ import annotations

from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass
from typing import Any, TypeVar

from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrW

NumberT = TypeVar("NumberT", int, float)


@dataclass
class MFFAttributeIORef(AttributeIORef):
    _: KW_ONLY
    name: str
    response_size: int
    response_handler: Callable
    read_cmd: Callable | None = None
    write_cmd: Callable | None = None
    update_period: float | None = 10


class MFFAttributeIO(AttributeIO[NumberT, MFFAttributeIORef]):
    """IO for mff attribute"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    async def update(
        self,
        attr: AttrR[NumberT, MFFAttributeIORef],
    ) -> None:
        if attr.io_ref.read_cmd:
            response = await self.controller.conn.send_query(
                attr.io_ref.read_cmd(),
                attr.io_ref.response_size,
            )

            response = attr.io_ref.response_handler(response)
            if attr.datatype is bool:
                await attr.update(int(response))
            else:
                await attr.update(response)

    async def send(
        self,
        attr: AttrW[NumberT, MFFAttributeIORef],
        value: Any,
    ) -> None:
        if attr.io_ref.write_cmd:
            if attr.datatype is bool:
                value = int(value)
            await self.controller.conn.send_command(
                attr.io_ref.write_cmd(value),
            )
