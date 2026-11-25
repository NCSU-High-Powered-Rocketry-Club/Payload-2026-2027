
"""Drivetrain node: joystick input to front and back Motoron controllers."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy

from drivetrain.arcade import arcade_drive

from . import motoron

# ============================================================
# MOTOR CONFIGURATION
# ============================================================

I2C_ADDRESS = 0x10

FRONT_I2C_BUS = 3
BACK_I2C_BUS = 1

# Motor direction inversion
# True = invert motor output
# False = normal motor output

INVERT_FRONT_LEFT = False
INVERT_FRONT_RIGHT = True

INVERT_BACK_LEFT = False
INVERT_BACK_RIGHT = True


class DrivetrainNode(Node):
    """Maps joystick input to front and back Motoron outputs."""

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

        # Motor direction configuration
        self._inversions = {
            "front_left": INVERT_FRONT_LEFT,
            "front_right": INVERT_FRONT_RIGHT,
            "back_left": INVERT_BACK_LEFT,
            "back_right": INVERT_BACK_RIGHT,
        }

        # Initialize front and back motor controllers
        self._front_mc = motoron.MotoronI2C(
            bus=FRONT_I2C_BUS,
            address=I2C_ADDRESS,
        )

        self._back_mc = motoron.MotoronI2C(
            bus=BACK_I2C_BUS,
            address=I2C_ADDRESS,
        )

        # Initialize both controllers
        for mc in (self._front_mc, self._back_mc):
            mc.reinitialize()
            mc.disable_crc()
            mc.clear_reset_flag()

            mc.set_max_acceleration(1, 200)
            mc.set_max_deceleration(1, 300)

        self._last_joy_time = None
        self._joy_timeout = 0.5

        self.create_subscription(
            Joy,
            "joy",
            self._on_joy,
            10,
        )

        self.create_timer(
            0.1,
            self._check_joy_timeout,
        )

        self.get_logger().info(
            "Drivetrain initialized: "
            f"Front bus={FRONT_I2C_BUS}, "
            f"Back bus={BACK_I2C_BUS}"
        )

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

    def _apply_inversion(
        self, speed: int, invert: bool
    ) -> int:
        return -speed if invert else speed

    def _set_motor_outputs(
        self, left: float, right: float
    ) -> None:

        # Convert joystick outputs to Motoron speed values
        left_speed = round(left * self._max_speed)
        right_speed = round(right * self._max_speed)

        # Apply individual motor inversions
        front_left = self._apply_inversion(
            left_speed, INVERT_FRONT_LEFT
        )

        front_right = self._apply_inversion(
            right_speed, INVERT_FRONT_RIGHT
        )

        back_left = self._apply_inversion(
            left_speed, INVERT_BACK_LEFT
        )

        back_right = self._apply_inversion(
            right_speed, INVERT_BACK_RIGHT
        )

        # FRONT MOTOR CONTROLLER (BUS 3)
        # Motor 1 = Left
        # Motor 2 = Right
        self._front_mc.set_speed(1, front_left)
        self._front_mc.set_speed(2, front_right)

        # BACK MOTOR CONTROLLER (BUS 1)
        # Motor 1 = Left
        # Motor 2 = Right
        self._back_mc.set_speed(1, back_left)
        self._back_mc.set_speed(2, back_right)

        self.get_logger().debug(
            f"Front: L={front_left} R={front_right} | "
            f"Back: L={back_left} R={back_right}"
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
