"""
File which contains utility functions which can be reused in the project.
"""

import argparse
import queue
from pathlib import Path
from typing import Any


def convert_unknown_type_to_float(obj_type: Any) -> float:
    """
    Converts the object to a float.

    Used by msgspec to convert numpy float64 to a float.
    :param obj_type: The object to convert.
    :return: The converted object.
    """
    return float(obj_type)


def convert_ns_to_s(nanoseconds: int) -> float:
    """
    Converts nanoseconds to seconds.

    :param nanoseconds: The time in nanoseconds.
    :return: The time in seconds.
    """
    return nanoseconds * 1e-9


def convert_s_to_ns(seconds: float) -> float:
    """
    Converts seconds to nanoseconds.

    :param seconds: The time in seconds.
    :return: The time in nanoseconds.
    """
    return seconds * 1e9


def get_all_packets_from_queue(packet_queue: queue.SimpleQueue, block: bool) -> list[Any]:
    """
    Empties the queue and returns all the items in a list.

    :param packet_queue: The queue to empty.
    :param block: Whether to block when getting items from the queue.

    :return: A list of all the items in the queue.
    """
    items = []

    if block:
        # Block until at least one item is available
        items.append(packet_queue.get(block=True))

    # Drain the rest of the queue, non-blocking
    while not packet_queue.empty():
        try:
            items.append(packet_queue.get(block=False))
        except queue.Empty:
            break
    return items


def arg_parser() -> argparse.Namespace:
    """Parse CLI arguments for the payload program."""
    parser = argparse.ArgumentParser(description="Run payload in real, mock, or pretend mode.")

    # A single optional argument for the file path
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Path to the flight data file (required for mock and pretend modes).",
    )

    parser.add_argument(
        "-l",
        "--keep-log-file",
        action="store_true",
        help="Keep the log file after replay stops.",
    )

    parser.add_argument(
        "-f",
        "--fast-replay",
        action="store_true",
        help="Run replay at full speed (mock mode only).",
    )

    return parser.parse_args()
