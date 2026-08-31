"""File to handle the display of real-time flight data in the terminal."""

import os
import threading
import time
from typing import TYPE_CHECKING

from colorama import Fore, Style, init

from payload.constants import DisplayEndingType

if TYPE_CHECKING:
    import argparse

    from payload.context import Context


G = Fore.GREEN
R = Fore.RED
Y = Fore.YELLOW
C = Fore.CYAN
RESET = Style.RESET_ALL


class FlightDisplay:
    """
    Class related to displaying real-time flight data in the terminal with
    pretty colors and spacing.
    """

    MOVE_CURSOR_UP = "\033[F"  # Move cursor up one line

    __slots__ = (
        "_args",
        "_context",
        "_current_pid",
        "_display_header",
        "_display_update_thread",
        "_launch_file",
        "_running",
        "_start_time",
        "end_mock_interrupted",
        "end_mock_natural",
    )

    def __init__(self, context: Context, args: argparse.Namespace) -> None:
        """
        Initializes the FlightDisplay object.

        :param context: The Context object.
        :param args: Command line arguments determining the program
            configuration.
        """
        init(autoreset=True)  # Automatically reset colors after each print
        self._context = context
        self._start_time = 0.0  # Time since the replay started (first packet received)
        self._running = False
        self._args = args

        # daemon threads are killed when the main thread exits.
        self._display_update_thread = threading.Thread(
            target=self.update_display, daemon=True, name="Real Time Display Thread"
        )
        self._current_pid = os.getpid()

        # Create events to signal the end of the replay.
        self.end_mock_natural = threading.Event()
        self.end_mock_interrupted = threading.Event()

        # Check if it's a real flight using the CLI args rather than try/except
        if self._args.mode == "real":
            self._launch_file = "N/A"
        else:
            self._launch_file = self._args.path.name if self._args.path else "Unknown"

        # The string to show at the top of the display:
        self._display_header = f"{Y}{'=' * 15} {'REPLAY' if self._args.mode == 'mock' else 'REAL TIME'} INFO {'=' * 15}{RESET}"  # noqa: E501

    def start(self) -> None:
        """
        Starts the display and cpu monitoring thread.

        Also prepares the processes for monitoring in the replay. This
        should only be done *after* context.start() is called, because
        we need the thread IDs.
        """
        self._running = True
        self._display_update_thread.start()

    def stop(self) -> None:
        """Stops the display thread."""
        self._running = False
        self._display_update_thread.join()

    def update_display(self) -> None:
        """
        Updates the display with real-time data.

        Runs in another thread. Automatically stops when the replay
        ends.
        """
        # Don't print the flight data if we are in debug mode
        if getattr(self._args, "debug", False):
            return

        # Wait till we processed a data packet. This is to prevent the display from updating
        # before we have any data to display.
        while not (
            self._context.context_data_packet and self._context.data_processor._last_data_packet
        ):
            pass

        self._start_time = time.time()

        # Update the display as long as the program is running:
        while self._running:
            self._update_display()

            # If we are running a real flight, end the display when we launch:
            if self._args.mode == "real" and self._context.state.name == "MotorBurnState":
                self._update_display(DisplayEndingType.TAKEOFF)
                break

            time.sleep(0.05)  # Don't hog the CPU

        # The program has ended, so we print the final display, depending on how it ended:
        if self.end_mock_natural.is_set():
            self._update_display(DisplayEndingType.NATURAL)
        if self.end_mock_interrupted.is_set():
            self._update_display(DisplayEndingType.INTERRUPTED)

    def _update_display(self, end_type: DisplayEndingType | None = None) -> None:
        """
        Updates the display with real-time data.

        :param end_type: The type of ending for the flight data display.
        """
        data_processor = self._context.data_processor

        time_since_launch = (
            self._context.data_processor.current_timestamp_seconds
            - self._context.launch_time_seconds
            if self._context.launch_time_seconds
            else 0
        )

        # Prepare output
        output = [
            self._display_header,
            f"Replay file:                  {C}{self._launch_file}{RESET}",
            f"Time since replay start:      {C}{time.time() - self._start_time:<10.2f}{RESET} {R}s{RESET}",  # noqa: E501
            f"{Y}{'=' * 12} REAL TIME FLIGHT DATA {'=' * 12}{RESET}",
            # Format time as MM:SS:
            f"Launch time:                 {G}T+{time.strftime('%M:%S', time.gmtime(time_since_launch))}{RESET}",  # noqa: E501
            f"State:                       {G}{self._context.state.name:<15}{RESET}",
            f"Current velocity:            {G}{data_processor.vertical_velocity:<10.2f}{RESET} {R}m/s{RESET}",  # noqa: E501
            f"Max velocity so far:         {G}{data_processor.max_vertical_velocity:<10.2f}{RESET} {R}m/s{RESET}",  # noqa: E501
            f"Current height:              {G}{data_processor.current_altitude:<10.2f}{RESET} {R}m{RESET}",  # noqa: E501
            f"Max height so far:           {G}{data_processor.max_altitude:<10.2f}{RESET} {R}m{RESET}",  # noqa: E501
        ]

        # Adds additional info to the display if -v was specified
        if getattr(self._args, "verbose", False):
            output.extend(
                [
                    f"{Y}{'=' * 18} DEBUG INFO {'=' * 17}{RESET}",
                    f"Average acceleration:        {G}{data_processor.average_vertical_acceleration:<10.2f}{RESET} {R}m/s^2{RESET}",  # noqa: E501
                    f"Log buffer size:             {G}{len(self._context.logger._log_buffer):<10}{RESET} {R}packets{RESET}",  # noqa: E501
                    # Use htop -H -p <PID> to see thread CPU usage
                    f"Current process ID:          {G}{self._current_pid:<10}{RESET} ",
                ]
            )

        # Print the output
        print("\n".join(output))

        # Move the cursor up for the next update, if the replay hasn't ended:
        if not end_type:
            print(self.MOVE_CURSOR_UP * len(output), end="", flush=True)

        # Print the end of replay message if the replay has ended
        match end_type:
            case DisplayEndingType.NATURAL:
                print(f"{R}{'=' * 14} END OF REPLAY {'=' * 14}{RESET}")
            case DisplayEndingType.INTERRUPTED:
                print(f"{R}{'=' * 12} INTERRUPTED REPLAY {'=' * 13}{RESET}")
            case DisplayEndingType.TAKEOFF:
                print(f"{R}{'=' * 13} ROCKET LAUNCHED {'=' * 14}{RESET}")
