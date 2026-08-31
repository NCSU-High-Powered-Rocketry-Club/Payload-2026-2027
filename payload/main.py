"""
The main file which will be run on the Raspberry Pi.

It will create the Context object and run the main loop.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from payload.constants import LOGS_PATH
from payload.context import Context
from payload.data_handling.data_processor import DataProcessor
from payload.data_handling.logger import Logger
from payload.hardware.firm import FIRM
from payload.mock.display import FlightDisplay
from payload.mock.mock_firm import MockFIRM
from payload.mock.mock_logger import MockLogger
from payload.utils import arg_parser

if TYPE_CHECKING:
    import argparse


def run_real_flight() -> None:
    """
    Entry point for the application to run the real flight.
    Entered when run with `uv run real`.
    """
    args = arg_parser()
    args.mode = "real"
    run_flight(args)


def run_mock_flight() -> None:
    """
    Entry point for the application to run the mock flight.
    Entered when run with `uv run mock [file]`.
    """
    args = arg_parser()
    args.mode = "mock"

    if not args.path:
        default_dir = Path("launch_data/real_firm_launches")
        if default_dir.exists() and default_dir.is_dir():
            files = [f for f in default_dir.iterdir() if f.is_file()]
            if files:
                args.path = files[0]
                print(f"No file provided. Defaulting to: {args.path}")

    run_flight(args)


def run_pretend_flight() -> None:
    """
    Entry point for the application to run the pretend flight.
    Entered when run with `uv run pretend [file]`.
    """
    args = arg_parser()
    args.mode = "pretend"

    if not args.path:
        default_dir = Path("launch_data/raw_firm_data")
        if default_dir.exists() and default_dir.is_dir():
            # Pretend mode requires .frm files
            files = [f for f in default_dir.iterdir() if f.is_file() and f.suffix.lower() == ".frm"]
            if files:
                args.path = files[0]
                print(f"No file provided. Defaulting to: {args.path}")

    elif args.path.suffix.lower() != ".frm":
        sys.exit("Error: Pretend mode requires a .FRM file.")

    run_flight(args)


def run_flight(args: argparse.Namespace) -> None:
    """
    Initializes the system components and starts the main loop.

    :param args: Command line arguments determining the program configuration.
    """
    firm, logger, data_processor = create_components(args)

    # Initialize the Context and display
    context = Context(firm, logger, data_processor)
    flight_display = FlightDisplay(context, args)

    # Run the main flight loop
    run_flight_loop(context, flight_display)


def create_firm_from_args(args: argparse.Namespace):
    """Create the correct FIRM implementation based on CLI args."""
    if args.mode == "real":
        return FIRM()

    if args.mode == "mock":
        return MockFIRM(
            log_file_path=args.path,
            real_time_replay=not args.fast_replay,
        )

    if args.mode == "pretend":
        return FIRM(
            is_pretend=True,
            log_file_path=args.path,
        )

    raise ValueError(f"Unknown mode: {args.mode}")


def create_components(args: argparse.Namespace):
    """Creates the system components needed for the payload system."""
    firm = create_firm_from_args(args)
    if args.mode in ("mock", "pretend"):
        logger = MockLogger(LOGS_PATH, delete_log_file=not args.keep_log_file)
    else:
        logger = Logger(LOGS_PATH)

    data_processor = DataProcessor()
    return firm, logger, data_processor


def run_flight_loop(context: Context, flight_display: FlightDisplay) -> None:
    """Runs the main loop for the code."""
    try:
        context.start()
        flight_display.start()
        while True:
            context.update()
    except KeyboardInterrupt:
        pass
    finally:
        context.stop()
