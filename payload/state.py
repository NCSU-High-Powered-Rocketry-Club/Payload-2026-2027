"""
Module for the finite state machine that represents which state of flight
the rocket is in.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from payload.constants import (
    GROUND_ALTITUDE_METERS,
    LANDED_ACCELERATION_METERS_PER_SECOND_SQUARED,
    MAX_ALTITUDE_THRESHOLD,
    TAKEOFF_VELOCITY_METERS_PER_SECOND,
)

if TYPE_CHECKING:
    from payload.context import Context


class State(ABC):
    """
    Abstract Base class for the states of the payloaad system. Each state
    will have an update method that will be called every loop iteration and a
    next_state method that will be called when the state is over.

    For this template, we will have 5 states, feel free to change these as needed for your payload:
    1. Standby - when the rocket is on the rail on the ground
    2. Motor Burn - when the motor is burning and the rocket is accelerating
    3. Coast - after the motor has burned out and the rocket is coasting up
    4. Free Fall - when the rocket is falling back to the ground after apogee
    5. Landed - when the rocket lands on the ground
    """

    __slots__ = ("context",)

    def __init__(self, context: Context) -> None:
        """:param context: The Payload Context managing the state machine."""
        self.context = context

    @property
    def name(self) -> str:
        """:return: The name of the state"""
        return self.__class__.__name__

    @abstractmethod
    def update(self) -> None:
        """
        Called every loop iteration.

        Uses the Payload Context to interact with the hardware and
        decides when to move to the next state.
        """

    @abstractmethod
    def next_state(self) -> None:
        """
        We never expect/want to go back a state e.g. We're never going to go
        from Flight to Motor Burn, so this method just goes to the next
        state.
        """


class StandbyState(State):
    """When the rocket is on the launch rail on the ground."""

    __slots__ = ()

    def update(self) -> None:
        """Checks if the rocket has launched, based on our velocity."""
        data = self.context.data_processor
        # If the velocity of the rocket is above a threshold, the rocket has launched.
        if data.vertical_velocity > TAKEOFF_VELOCITY_METERS_PER_SECOND:
            self.next_state()
            return

    def next_state(self):
        self.context.state = MotorBurnState(self.context)


class MotorBurnState(State):
    """When the motor is burning and the rocket is accelerating."""

    __slots__ = ()

    def __init__(self, context: Context) -> None:
        super().__init__(context)

    def update(self) -> None:
        """
        Checks to see if the velocity has decreased lower than the maximum
        velocity, indicating the motor has burned out.
        """
        data = self.context.data_processor

        # If our current velocity is less than our max velocity, that means we have stopped
        # accelerating. This is the same thing as checking if our accel sign has flipped
        if data.vertical_velocity < data.max_vertical_velocity:
            self.next_state()
            return

        # Fallback! If FIRM data wasn't good, we need to transition to coast state:
        # time_since_burn = time.time() - self.start_motor_burn_time_s

        # if time_since_burn > 3:
        #     self.next_state()
        #     return

    def next_state(self) -> None:
        self.context.state = CoastState(self.context)


class CoastState(State):
    """
    When the motor has burned out and the rocket is coasting to apogee.
    """

    __slots__ = ()

    def __init__(self, context: Context) -> None:
        super().__init__(context)

    def update(self) -> None:
        """
        Checks to see if the rocket has reached apogee, indicating the start
        of free fall.
        """
        data = self.context.data_processor

        # If our velocity is less than 0 and our altitude is less than 95% of our max altitude, we
        # are in free fall.
        if (
            data.vertical_velocity <= 0
            and data.current_altitude <= data.max_altitude * MAX_ALTITUDE_THRESHOLD
        ):
            self.next_state()
            return

    def next_state(self) -> None:
        self.context.state = FreeFallState(self.context)


class FreeFallState(State):
    """When the rocket is falling back to the ground after apogee."""

    __slots__ = ()

    def __init__(self, context: Context) -> None:
        super().__init__(context)

    def update(self) -> None:
        """
        Check if the rocket has landed, based on our altitude and a spike in
        acceleration.
        """
        data = self.context.data_processor

        # If our altitude is around 0, and we have an acceleration spike, we have landed
        if (
            data.current_altitude <= GROUND_ALTITUDE_METERS
            and data.average_vertical_acceleration >= LANDED_ACCELERATION_METERS_PER_SECOND_SQUARED
        ):
            self.next_state()

    def next_state(self) -> None:
        self.context.state = LandedState(self.context)


class LandedState(State):
    """When the rocket has landed."""

    __slots__ = ()

    def update(self) -> None:
        """
        We use this method to stop the air brakes system after we have hit
        our log buffer.
        """
        if self.context.logger.is_log_buffer_full:
            self.context.stop()

    def next_state(self) -> None:
        # Explicitly do nothing, there is no next state
        pass
