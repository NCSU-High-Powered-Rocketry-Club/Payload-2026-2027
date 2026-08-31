"""
Module for describing the data packet for the logger to log.
"""

import msgspec


class LoggerDataPacket(msgspec.Struct, array_like=True, kw_only=True):
    """
    Represents a collection of all data that the logger can log in a line.

    Not every field will be filled in every packet. The order in which the fields are defined
    determines the order in which they will be logged.
    """

    # Fields derived from ContextDataPacket
    timestamp_epoch: str | None
    state_letter: str | None

    # Estimated Data Packet Fields
    est_position_z_meters: float | None = None
    est_velocity_z_meters_per_s: float | None = None
    temperature_celsius: float | None = None
    timestamp_seconds: float | None = None
    raw_acceleration_x_gs: float | None = None
    raw_acceleration_y_gs: float | None = None
    raw_acceleration_z_gs: float | None = None
