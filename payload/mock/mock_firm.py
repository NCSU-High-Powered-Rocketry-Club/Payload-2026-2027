"""Module for simulating the FIRM hardware by reading from a log file."""

import queue
import threading
import time
from typing import TYPE_CHECKING

import polars as pl
from firm_client import FIRMDataPacket

from payload.base_classes.base_firm import BaseFIRM
from payload.constants import SERIAL_TIMEOUT_SECONDS, STOP_SIGNAL

if TYPE_CHECKING:
    from pathlib import Path


class MockFIRM(BaseFIRM):
    """
    A mock implementation of FIRM for testing/simulation purposes.

    It reads a CSV log file and feeds FIRMDataPackets into the queue as
    if they were coming from the hardware.
    """

    __slots__ = (
        "_data_fetch_thread",
        "_headers",
        "_is_running",
        "_log_file_path",
        "_needed_fields",
        "_queued_packets",
        "_requested_to_run",
    )

    def __init__(
        self,
        log_file_path: Path,
        real_time_replay: bool = False,
    ):
        """
        Initializes the MockFIRM.

        :param log_file_path: CSV log file path.
        :param real_time_replay: If True, packets are emitted with
            delays matching their original timestamps. If False, packets
            are emitted as fast as possible.
        """
        self._log_file_path = log_file_path

        # Set up a queue and thread
        self._queued_packets: queue.SimpleQueue[FIRMDataPacket | str] = queue.SimpleQueue()
        self._data_fetch_thread = threading.Thread(
            target=self._fetch_data_loop,
            args=(real_time_replay,),
            name="Mock FIRM Thread",
            daemon=True,
        )

        self._is_running = threading.Event()
        self._requested_to_run = threading.Event()

        super().__init__()

    @property
    def is_running(self) -> bool:
        """
        Returns True if the Mock FIRM thread is running and fetching
        data.
        """
        return self._is_running.is_set()

    @property
    def requested_to_run(self) -> bool:
        """
        Returns True if the Mock FIRM thread has been requested to run.
        """
        return self._requested_to_run.is_set()

    def start(self) -> None:
        """Starts the Mock FIRM thread."""
        self._requested_to_run.set()
        if not self._data_fetch_thread.is_alive():
            self._data_fetch_thread.start()

    def stop(self) -> None:
        """Stops the Mock FIRM thread."""
        self._requested_to_run.clear()
        # Fetch all packets which are not yet fetched and discard them, so main() does not get
        # stuck (i.e. deadlocks) waiting for the thread to finish.
        self._queued_packets.put(STOP_SIGNAL)  # signal the main thread to stop waiting

        self._data_fetch_thread.join(timeout=SERIAL_TIMEOUT_SECONDS)
        if self._data_fetch_thread.is_alive():
            raise RuntimeError("FIRM data fetch thread did not terminate in time.")

    def get_data_packets(self, block: bool = True) -> list[FIRMDataPacket]:
        """Returns all available FIRM data packets from the queue."""
        packets = []

        if block:
            # Block until at least one item is available
            item = self._queued_packets.get(block=True)
            if item == STOP_SIGNAL:
                return packets  # Makes the main update() loop exit early.
            packets.append(item)

        while not self._queued_packets.empty():
            item = self._queued_packets.get(block=block)

            # If we hit the stop signal, ensure we mark ourselves as stopped
            if item == STOP_SIGNAL:
                break  # Makes the main update() loop exit early.

            packets.append(item)

        return packets

    # ------------------------ THREAD METHODS -------------------------

    def _scan_csv(self, *, start_index: int = 0, **kwargs) -> pl.LazyFrame:
        """Prepares the Polars LazyFrame with only the columns we need."""
        # 1. Get all headers present in the CSV
        excluded_columns = [
            "est_tilt_angle_degrees",
            "est_mach_number",
            "raw_rotated_acceleration_x_gs",
            "raw_rotated_acceleration_y_gs",
            "raw_rotated_acceleration_z_gs",
        ]
        self._headers = [
            h
            for h in pl.scan_csv(self._log_file_path).collect_schema().names()
            if h not in excluded_columns
        ]

        # 2. Get all fields defined in the FIRMDataPacket struct
        packet_fields = list(FIRMDataPacket.__struct_fields__)

        # 3. Intersection: Only read columns that exist in both the CSV and the Packet
        self._needed_fields = [f for f in packet_fields if f in self._headers]

        return pl.scan_csv(
            self._log_file_path,
            has_header=True,
            skip_rows_after_header=start_index,
            infer_schema_length=100,
            **kwargs,
        ).select(self._needed_fields)

    def _read_file(self, real_time_replay: bool) -> None:
        """
        Reads the CSV, converts rows to FIRMDataPackets, and manages replay
        timing.

        :param real_time_replay: Whether to mimic a real flight by sleeping for a set period, or run
            at full speed, e.g. for using it in the CI.
        :param start_after_log_buffer: Whether to send the data packets only after the log buffer
            was filled for Standby state.
        """
        collected_data: pl.DataFrame = self._scan_csv().collect()

        # Iterate over the rows of the dataframe and put the data packets in the queue
        for row in collected_data.iter_rows(named=True):
            # Check if the loop should stop:
            if not self._requested_to_run.is_set():
                break

            start_time = time.time()

            # Drop None values from the row so msgspec Structs can be made:
            # This approach of deleting is faster than using a dict comprehension by about 6%
            row_dict = row.copy()
            for k in list(row_dict.keys()):
                if row_dict[k] is None:
                    del row_dict[k]

            firm_data_packet = FIRMDataPacket(**row_dict)

            self._queued_packets.put(firm_data_packet)

            # Sleep only if we are running a real-time replay
            if real_time_replay:
                # Mimic the polling interval so it "runs in real time"
                end_time = time.time()
                time.sleep(max(0.0, 1.0 / 100.0 - (end_time - start_time)))

    def _fetch_data_loop(
        self,
        real_time_replay: bool,
    ) -> None:
        """
        :param real_time_replay: Whether to mimic a real flight by sleeping for a set period, or run
            at full speed.
        :param start_after_log_buffer: Whether to send the data packets only after the log buffer
            was filled for Standby state.
        """
        """The main thread loop."""
        self._is_running.set()

        self._read_file(real_time_replay)

        self._is_running.clear()
        # If we don't put the STOP_SIGNAL in the queue, the main thread will wait till
        # FIRM_SERIAL_TIMEOUT seconds before exiting, which is not what we want.
        self._queued_packets.put(STOP_SIGNAL)
