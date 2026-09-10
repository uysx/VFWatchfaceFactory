"""
Device configuration.

Only IDW13 is enabled/supported right now, per project scope. The table is
structured as a dict so additional devices can be added later without any
architectural changes elsewhere in the app.

Field meanings (mirrors the reference C++ editor's DeviceConfig struct):
    device_id            deviceId / description written into iwf.json
    canvas_w, canvas_h    native watch-face render resolution
    anchor_x, anchor_y    default watch-hand anchor point (usually canvas center)
    border_rect_w/h       procedural preview border rectangle size
    corner_radius         preview rounded-corner radius
    border_color          preview border QColor (r, g, b)
    border_width          preview border pen width
    preview_w, preview_h  output preview.png canvas size
    preview_scale         extra scale factor applied when fitting canvas into preview
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceConfig:
    device_id: str
    canvas_w: int
    canvas_h: int
    anchor_x: int
    anchor_y: int
    border_rect_w: int
    border_rect_h: int
    corner_radius: int
    border_color: tuple
    border_width: int
    preview_w: int
    preview_h: int
    preview_scale: float


DEVICES = {
    "IDW13": DeviceConfig(
        device_id="IDW13",
        canvas_w=240, canvas_h=284,
        anchor_x=120, anchor_y=142,
        border_rect_w=168, border_rect_h=196,
        corner_radius=31,
        border_color=(37, 37, 37, 255),
        border_width=1,
        preview_w=174, preview_h=196,
        preview_scale=1.0,
    ),
}

DEFAULT_DEVICE_ID = "IDW13"


def get_device(device_id: str) -> DeviceConfig:
    return DEVICES.get(device_id, DEVICES[DEFAULT_DEVICE_ID])
