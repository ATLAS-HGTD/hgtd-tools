# hgtd_tools/assets.py
import json
from functools import cache
from importlib.resources import files

ASSETS = files("hgtd_tools").joinpath("assets")


@cache
def load_json_from_assets(name: str):
    return json.loads(ASSETS.joinpath(name).read_text(encoding="utf-8"))
