from fastcs.connections import SerialConnectionSettings
from pydantic import BaseModel


class ControllerConfig(BaseModel):
    serial_settings: SerialConnectionSettings


class IOCConfig(BaseModel):
    pv_prefix: str


class GUIConfig(BaseModel):
    output_path: str
    title: str


class TransportConfig(BaseModel):
    ioc: IOCConfig
    gui: GUIConfig


class Config(BaseModel):
    controller: ControllerConfig
    transport: list[TransportConfig]
