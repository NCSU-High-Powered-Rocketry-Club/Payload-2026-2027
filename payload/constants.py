"""The constants for the payload."""

from enum import StrEnum
from pathlib import Path

# ------------------------ FIRM constants ------------------------

PORT_LINUX = "/dev/ttyACM0"
PORT_WINDOWS = "COM5"
BAUD_RATE = 2_000_000
SERIAL_TIMEOUT_SECONDS = 1.0

# ------------------------ State machine constants ------------------------


# ------------------------ Standby to MotorBurn ------------------------


TAKEOFF_VELOCITY_METERS_PER_SECOND = 10
"""The velocity in meters per second that the rocket must reach before we
consider it to have taken off."""

# ------------------------ Coasting to Freefall ------------------------
MAX_ALTITUDE_THRESHOLD = 0.95
"""We don't care too much about accurately changing to the freefall state, so
we just check if the rocket is less than 95% of the max altitude it reached.

FIXME: Depending on the payload implementation, this might need to be changed
"""

# ------------------------ Freefall to Landing ------------------------
MAX_FREE_FALL_SECONDS = 345.0
"""The maximum amount of time in seconds that the rocket can be in freefall
before we consider it to have landed.

This is to prevent the program from running indefinitely if our code
never detects the landing of the rocket. This value accounts for the
worst case scenario of the main parachute deploying at apogee.
"""

GROUND_ALTITUDE_METERS = 10.0
"""The zeroed-out altitude (final altitude minus initial altitude) in meters
that the rocket must be under before we consider it to have landed."""
LANDED_ACCELERATION_METERS_PER_SECOND_SQUARED = 20.0
"""The acceleration in m/s^2 that the rocket must be above before we consider
it to have landed.
"""

# ------------------------ Logger constants------------------------
LOGS_PATH = Path("logs")

LOG_BUFFER_SIZE = 5000
"""
Buffer size if CAPACITY is reached.

Once the state changes, this buffer will be logged to make sure we don't lose data.
"""

NUMBER_OF_LINES_TO_LOG_BEFORE_FLUSHING = 100  # 1 second of data
"""
The number of lines we log before manually flushing the buffer and forcing the OS to write to the
file.
"""

STOP_SIGNAL = "STOP"
"""
The signal to stop the Logger and MockFIRM, this will be put in the queue to stop the threads.
"""

# ------------------------ DataProcessor constants ------------------------
GRAVITY_METERS_PER_SECOND_SQUARED = 9.81
"""The acceleration due to gravity, used for converting gs to meters per second squared."""

# ------------------------ Display Configuration ------------------------


class DisplayEndingType(StrEnum):
    """Enum that represents the different ways the display can end."""

    NATURAL = "natural"
    """The display ends naturally, when the payload finishes, in a mock replay."""
    INTERRUPTED = "interrupted"
    """The display ends because the user interrupted the program."""
    TAKEOFF = "takeoff"
    """The display ends because the rocket took off, in a real launch."""
