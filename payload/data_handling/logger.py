"""
Module for logging data to a CSV file in real time.
"""

import csv
import os
import queue
import threading
import typing
from collections import deque
from typing import Any, Literal

import msgspec

from payload.constants import (
    LOG_BUFFER_SIZE,
    NUMBER_OF_LINES_TO_LOG_BEFORE_FLUSHING,
    STOP_SIGNAL,
)
from payload.data_handling.packets.logger_data_packet import LoggerDataPacket
from payload.utils import get_all_packets_from_queue

if typing.TYPE_CHECKING:
    from pathlib import Path

    from firm_client import FIRMDataPacket

    from payload.data_handling.packets.context_data_packet import ContextDataPacket

DecodedLoggerDataPacket = list[int | float | str]
"""
The type of LoggerDataPacket after an instance of it converted to primitive type by
msgspec.to_builtins.
"""


class Logger:
    """
    A class that logs data to a CSV file.

    Similar to the IMU class, it runs in a separate thread. This is because the logging thread is
    I/O-bound, meaning that it spends most of its time waiting for the file to be written to. By
    running it in a separate thread, we can continue to log data while the main loop is running. It
    uses Python's csv module to append the airbrakes' current state, extension, and IMU data to our
    logs in real time.
    """

    __slots__ = (
        "_log_buffer",
        "_log_counter",
        "_log_queue",
        "_log_thread",
        "log_path",
    )

    def __init__(self, log_dir: Path) -> None:
        """
        Initializes the logger object.

        It creates a new log file in the specified directory. Like the IMU class, it creates a queue
        to store log messages, and starts a separate thread to handle the logging. We are logging a
        lot of data, and logging is I/O-bound, so running it in a separate thread allows the main
        loop to continue running without waiting for the log file to be written to.
        :param log_dir: The directory where the log files will be.
        """
        # Create the log directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)

        # Get all existing log files and find the highest suffix number
        existing_logs = list(log_dir.glob("log_*.csv"))
        max_suffix = (
            max(int(log.stem.split("_")[-1]) for log in existing_logs) if existing_logs else 0
        )

        # Buffer for StandbyState and LandedState
        self._log_counter = 0
        self._log_buffer = deque(maxlen=LOG_BUFFER_SIZE)

        # Create a new log file with the next number in sequence
        self.log_path = log_dir / f"log_{max_suffix + 1}.csv"
        with self.log_path.open(mode="w", newline="") as file_writer:
            headers = list(LoggerDataPacket.__struct_fields__)
            writer = csv.writer(file_writer)
            writer.writerow(headers)

        self._log_queue: queue.SimpleQueue[LoggerDataPacket | Literal["STOP"]] = queue.SimpleQueue()

        # Start the logging thread
        self._log_thread = threading.Thread(
            target=self._logging_loop, name="Logger Thread", daemon=True
        )

    @property
    def is_running(self) -> bool:
        """
        Returns whether the logging thread is running.
        """
        return self._log_thread.is_alive()

    @property
    def is_log_buffer_full(self) -> bool:
        """
        Returns whether the log buffer is full.
        """
        return len(self._log_buffer) == LOG_BUFFER_SIZE

    @staticmethod
    def _convert_unknown_type_to_str(obj_type: Any) -> str:
        """
        Truncates the decimal place of the object to 8 decimal places.

        Used by msgspec to convert numpy float64 to a string.
        :param obj_type: The object to truncate.
        :return: The truncated object.
        """
        return f"{obj_type:.8f}"

    @staticmethod
    def _prepare_logger_packets(
        context_data_packet: ContextDataPacket,
        firm_data_packets: list[FIRMDataPacket],
    ) -> list[LoggerDataPacket]:
        """
        Creates a data packet representing a row of data to be logged.

        :param context_data_packet: The Context Data Packet to log.
        :param firm_data_packets: The FIRM data packets to log.
        length as the number of EstimatedDataPackets present in the `imu_data_packets`.
        :return: A deque of LoggerDataPacket objects.
        """
        logger_data_packets: list[LoggerDataPacket] = []

        # Convert the firm data packets to a LoggerDataPacket:
        for firm_data_packet in firm_data_packets:
            logger_packet = LoggerDataPacket(
                timestamp_epoch=context_data_packet.epoch_time,
                state_letter=context_data_packet.state.__name__,
                timestamp_seconds=firm_data_packet.timestamp_seconds,
            )

            logger_packet.est_position_z_meters = firm_data_packet.est_position_z_meters
            logger_packet.est_velocity_z_meters_per_s = firm_data_packet.est_velocity_z_meters_per_s
            logger_packet.temperature_celsius = firm_data_packet.temperature_celsius
            logger_packet.raw_acceleration_x_gs = firm_data_packet.raw_acceleration_x_gs
            logger_packet.raw_acceleration_y_gs = firm_data_packet.raw_acceleration_y_gs
            logger_packet.raw_acceleration_z_gs = firm_data_packet.raw_acceleration_z_gs

            logger_data_packets.append(logger_packet)

        return logger_data_packets

    def start(self) -> None:
        """
        Starts the logging thread.

        This is called before the main while loop starts.
        """
        self._log_thread.start()

    def stop(self) -> None:
        """
        Stops the logging thread.

        It will finish logging the current message and then stop.
        """
        # Log the buffer before stopping the thread
        self._log_the_buffer()
        self._log_queue.put(STOP_SIGNAL)  # Put the stop signal in the queue
        # Waits for the thread to finish before stopping it
        self._log_thread.join()

    def log(
        self,
        context_data_packet: ContextDataPacket,
        firm_data_packets: list[FIRMDataPacket],
    ) -> None:
        """
        Logs the current state, extension, and IMU data to the CSV file.

        :param context_data_packet: The Context Data Packet to log.
        :param firm_data_packets: The IMU data packets to log.
        """
        # We are populating a list with the fields of the logger data packet
        logger_data_packets: list[LoggerDataPacket] = Logger._prepare_logger_packets(
            context_data_packet,
            firm_data_packets,
        )

        # If we are not in Standby or Landed State, we should log the buffer if it's not empty:
        if self._log_buffer:
            self._log_the_buffer()

        # Reset the counter for other states
        self._log_counter = 0
        for packet in logger_data_packets:
            self._log_queue.put(packet, block=False)

    def _log_the_buffer(self):
        """
        Enqueues all the packets in the log buffer to the log queue, so they will be logged.
        """
        for packet in self._log_buffer:
            self._log_queue.put(packet, block=False)
        self._log_buffer.clear()

    # ------------------------ ALL METHODS BELOW RUN IN A SEPARATE THREAD -------------------------
    @staticmethod
    def _truncate_floats(data: DecodedLoggerDataPacket) -> list[str | int]:
        """
        Truncates the decimal place of the floats in the list to 8 decimal places.

        :param data: The list of values whose floats we should truncate.
        :return: The truncated list.
        """
        return [f"{value:.8f}" if isinstance(value, float) else value for value in data]

    def _logging_loop(self) -> None:  # pragma: no cover
        """
        The loop that saves data to the logs.
        It runs in parallel with the main loop.
        """
        # Set up the csv logging in the new thread
        with self.log_path.open(mode="a", newline="") as file_writer:
            writer = csv.writer(file_writer)
            number_of_lines_logged = 0
            while True:
                # Get a message from the queue (this will block until a message is available)
                # Because there's no timeout, it will wait indefinitely until it gets a message.
                logger_packets: list[LoggerDataPacket | Literal["STOP"]] = (
                    get_all_packets_from_queue(self._log_queue, block=True)
                )
                packet_fields: list[DecodedLoggerDataPacket | Literal["STOP"]] = (
                    msgspec.to_builtins(
                        logger_packets, enc_hook=Logger._convert_unknown_type_to_str
                    )
                )
                # If the message is the stop signal, break out of the loop
                for message_field in packet_fields:
                    if message_field == STOP_SIGNAL:
                        return
                    writer.writerow(Logger._truncate_floats(message_field))
                    number_of_lines_logged += 1
                    # During our Pelicanator 1 flight, the rocket fell and had a very hard impact
                    # causing the pi to lose power. This caused us to lose a lot of lines of data
                    # that were not written to the log file. To prevent this from happening again,
                    # we flush the logger 1000 lines (equivalent to 1 second).
                    if number_of_lines_logged % NUMBER_OF_LINES_TO_LOG_BEFORE_FLUSHING == 0:
                        # Tell Python to flush the data. This gives the data to the OS, and it is
                        # stored as a dirty page cache (in memory) until the OS decides to write it
                        # to disk. Technically python automatically flushes the data when the python
                        # buffer is full (8192 bytes, which would be about 25 lines of data).
                        file_writer.flush()
                        # Tell the OS to write the file to disk from the dirty page cache. This
                        # ensures that the data is written to disk and not just stored in memory.
                        # This operation is the one which is actually "blocking" when talking about
                        # file I/O.
                        os.fsync(file_writer.fileno())
