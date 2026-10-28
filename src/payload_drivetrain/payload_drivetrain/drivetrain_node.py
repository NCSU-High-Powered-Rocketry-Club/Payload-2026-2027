"""Drivetrain node: subscribes to joystick input and performs arcade drive."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy

from payload_drivetrain.arcade import arcade_drive


class DrivetrainNode(Node):
    """Maps /joy axes to left/right motor outputs using arcade drive."""

    def __init__(self) -> None:
        """Declare parameters and create the /joy subscription."""
        super().__init__("drivetrain")
        # Defaults match an Xbox controller under joy_node: left stick Y / right stick X.
        self._throttle_axis = self.declare_parameter("throttle_axis", 1).value
        self._turn_axis = self.declare_parameter("turn_axis", 3).value
        self._deadband = self.declare_parameter("deadband", 0.05).value
        self.create_subscription(Joy, "joy", self._on_joy, 10)

    def _on_joy(self, msg: Joy) -> None:
        if max(self._throttle_axis, self._turn_axis) >= len(msg.axes):
            self.get_logger().warn("Joy message has too few axes", throttle_duration_sec=5.0)
            return
        throttle = self._apply_deadband(msg.axes[self._throttle_axis])
        turn = self._apply_deadband(msg.axes[self._turn_axis])
        left, right = arcade_drive(throttle, turn)
        self._set_motor_outputs(left, right)

    def _apply_deadband(self, value: float) -> float:
        return 0.0 if abs(value) < self._deadband else value

    def _set_motor_outputs(self, left: float, right: float) -> None:
        """Send outputs in [-1, 1] to the motors. TODO: implement hardware interface."""
        self.get_logger().debug(f"left={left:.2f} right={right:.2f}")


def main(args: list[str] | None = None) -> None:
    """Entry point."""
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
