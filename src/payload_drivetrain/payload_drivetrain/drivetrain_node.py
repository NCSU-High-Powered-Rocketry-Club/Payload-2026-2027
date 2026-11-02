
"""Drivetrain node: joystick input to Motoron motor commands."""

import motoron
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy

from payload_drivetrain.arcade import arcade_drive


class DrivetrainNode(Node):
    """Maps joystick input to left/right Motoron outputs."""

    def __init__(self) -> None:
        super().__init__("drivetrain")

        self._throttle_axis = self.declare_parameter(
            "throttle_axis", 1
        ).value
        self._turn_axis = self.declare_parameter(
            "turn_axis", 3
        ).value
        self._deadband = self.declare_parameter(
            "deadband", 0.05
        ).value
        self._max_speed = self.declare_parameter(
            "max_speed", 800
        ).value

        # Initialize the Motoron.
        self._mc = motoron.MotoronI2C()
        self._mc.reinitialize()
        self._mc.disable_crc()
        self._mc.clear_reset_flag()

        # Configure acceleration and deceleration.
        for motor in (1, 2):
            self._mc.set_max_acceleration(motor, 200)
            self._mc.set_max_deceleration(motor, 300)

        self._last_joy_time = None
        self._joy_timeout = 0.5

        self.create_subscription(
            Joy, "joy", self._on_joy, 10
        )

        self.create_timer(0.1, self._check_joy_timeout)

        self.get_logger().info("Drivetrain node initialized.")

    def _on_joy(self, msg: Joy) -> None:
        if max(self._throttle_axis, self._turn_axis) >= len(msg.axes):
            self.get_logger().warn(
                "Joy message has too few axes",
                throttle_duration_sec=5.0,
            )
            return

        self._last_joy_time = self.get_clock().now()

        throttle = self._apply_deadband(
            msg.axes[self._throttle_axis]
        )
        turn = self._apply_deadband(
            msg.axes[self._turn_axis]
        )

        left, right = arcade_drive(throttle, turn)
        self._set_motor_outputs(left, right)

    def _apply_deadband(self, value: float) -> float:
        return 0.0 if abs(value) < self._deadband else value

    def _set_motor_outputs(
        self, left: float, right: float
    ) -> None:
        left_speed = round(left * self._max_speed)
        right_speed = round(right * self._max_speed)

        self._mc.set_speed(1, left_speed)
        self._mc.set_speed(2, right_speed)

        self.get_logger().debug(
            f"left={left_speed} right={right_speed}"
        )

    def _check_joy_timeout(self) -> None:
        if self._last_joy_time is None:
            return

        elapsed = (
            self.get_clock().now() - self._last_joy_time
        ).nanoseconds / 1e9

        if elapsed > self._joy_timeout:
            self._set_motor_outputs(0.0, 0.0)
            self._last_joy_time = None
            self.get_logger().warn(
                "Joystick timeout: stopping motors."
            )

    def destroy_node(self):
        try:
            self._set_motor_outputs(0.0, 0.0)
        finally:
            super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DrivetrainNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
