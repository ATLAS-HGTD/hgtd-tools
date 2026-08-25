# hgtd_tools/asset_helpers.py
import base64
import io
import json
from functools import cache
from importlib.resources import files

from PIL import Image

ASSETS = files("hgtd_tools").joinpath("assets")


@cache
def load_json_from_assets(name: str):
    return json.loads(ASSETS.joinpath(name).read_text(encoding="utf-8"))


@cache
def load_image_from_assets(filename: str) -> Image.Image:
    """Loads a PNG asset from the package as a PIL Image object."""
    img_bytes = ASSETS.joinpath(filename).read_bytes()
    return Image.open(io.BytesIO(img_bytes))


@cache
def load_image_from_assets_as_b64(filename):
    """Loads a PNG asset from the package as base64 for tkinter windowIcon."""
    img_bytes = ASSETS.joinpath(filename).read_bytes()
    return base64.b64encode(img_bytes).decode("utf-8")
