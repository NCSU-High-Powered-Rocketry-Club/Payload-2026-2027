"""
Module for the ContextDataPacket class.
"""

import msgspec

from payload.state import State  # noqa: TC001 (doesn't work with msgspec)


class ContextDataPacket(msgspec.Struct, tag=True, array_like=True):
    """
    This data packet keeps data owned by the Context as well as metadata about the context.
    """

    state: type[State]
    """
    Represents the stage of flight we are in.

    This is the state that the state machine is in.
    """

    retrieved_firm_packets: int
    """
    This is the number of packets we got from the IMU thread, in the main thread.

    This number will always be below constants.MAX_FETCHED_PACKETS. If this number is on the high
    end, it indicates some performance issues with the main thread.
    """

    update_timestamp_ns: int
    """
    The timestamp reported by the local computer at which we processed and logged this data packet.

    This is used to compare the time difference between what is reported by the IMU, and when we
    finished processing the data packet.
    """

    epoch_time: str
    """
    The Epoch Time stamp reported by the Raspberry Pi at the time the data packet was processed

    This is used for NASA reporting as they require timestamps for all Payload Operations
    """
