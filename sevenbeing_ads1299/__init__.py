"""TI ADS1299EEG-FE on MMB0.

`ADS1299` and the CLI talk USB directly and do not import sevenbeing.
`Ads1299Driver` is the optional sevenbeing plugin.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .device import ADS1299
from .usb_ids import BOOT_PID, BOOT_VID, STYX_PID, STYX_VID

__all__ = [
    "ADS1299",
    "Ads1299Driver",
    "BOOT_VID",
    "BOOT_PID",
    "STYX_VID",
    "STYX_PID",
    "__version__",
]


def __getattr__(name: str):
    if name == "Ads1299Driver":
        from .driver import Ads1299Driver

        return Ads1299Driver
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
