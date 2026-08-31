"""The context for the payload state machine."""

import time
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from payload.data_handling.packets.context_data_packet import ContextDataPacket
from payload.state import StandbyState, State

if TYPE_CHECKING:
    from firm_client import FIRMDataPacket

    from payload.base_classes.base_firm import BaseFIRM
    from payload.data_handling.data_processor import DataProcessor
    from payload.data_handling.logger import Logger
    from payload.data_handling.packets.processor_data_packet import ProcessorDataPacket


class Context:
    """
    Manages the state machine for the rocket's payload system, keeping track of the current state,
    and communicating with hardware such as a the motor.

    This class is what connects the state machine to the hardware.

    Read more about the state machine pattern here:
    https://www.tutorialspoint.com/design_pattern/state_pattern.htm
    """

    __slots__ = (
        "context_data_packet",
        "data_processor",
        "firm",
        "firm_data_packets",
        "landing_time_seconds",
        "launch_time_seconds",
        "logger",
        "most_recent_firm_data_packet",
        "processor_data_packets",
        "state",
    )

    def __init__(self, firm: BaseFIRM, logger: Logger, data_processor: DataProcessor) -> None:
        self.logger = logger
        self.firm = firm
        self.data_processor = data_processor
        self.state: State = StandbyState(self)
        self.firm_data_packets: list[FIRMDataPacket] = []
        self.processor_data_packets: list[ProcessorDataPacket] = []
        self.most_recent_firm_data_packet: FIRMDataPacket | None = None
        self.context_data_packet: ContextDataPacket | None = None
        self.launch_time_seconds: int = 0
        self.landing_time_seconds: int = 0

    def start(self):
        self.firm.start()
        self.logger.start()

    def stop(self):
        self.firm.stop()
        self.logger.stop()

    def update(self):
        self.firm_data_packets = self.firm.get_data_packets()

        # If we don't have any packets, don't do anything
        if not self.firm_data_packets:
            return

        self.most_recent_firm_data_packet = self.firm_data_packets[-1]

        # Update the data processor with the new data packets.
        self.data_processor.update(self.firm_data_packets)
        self.processor_data_packets = self.data_processor.get_processor_data_packets()

        self.state.update()

        self.generate_data_packets()

        self.logger.log(
            self.context_data_packet,  # type: ignore
            self.firm_data_packets,
        )

    def generate_data_packets(self) -> None:
        self.context_data_packet = ContextDataPacket(
            state=type(self.state),
            retrieved_firm_packets=len(self.firm_data_packets),
            update_timestamp_ns=int(time.time_ns()),
            epoch_time=datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M:%S"),
        )
