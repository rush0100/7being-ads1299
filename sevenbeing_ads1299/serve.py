"""Run ADS1299 PDK device daemon: gRPC DeviceService for sevenbeing core."""

from __future__ import annotations

from sevenbeing.devices.grpc_server import main_for_driver

from . import __version__
from .driver import Ads1299Driver


def main() -> None:
    main_for_driver(
        Ads1299Driver,
        default_port=51053,
        package="7being-ads1299",
        version=__version__,
    )


if __name__ == "__main__":
    main()
