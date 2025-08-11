# Project: MscBot
# License: MIT

import time

from data.config_settings import get_backoff_config
from utils.pretty_print import display_info

_cfg = get_backoff_config()
_factor = 1.0
_last_good = time.time()


def get_delay_factor() -> float:
    global _factor, _last_good
    if time.time() - _last_good > _cfg["cool_down_good_seconds"]:
        if _factor > 1.0:
            _factor = max(1.0, _factor - _cfg["factor_step"])
    return _factor


def record_timeout():
    global _factor
    if not _cfg["enable"]:
        return
    _factor = min(_cfg["factor_max"], _factor + _cfg["factor_step"])
    display_info(f"Backoff increased: factor={_factor:.2f}")


def record_good():
    global _last_good
    _last_good = time.time()
