"""Launch the Xbox controller (joy_linux_node) and the drivetrain node."""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Build the launch description."""
    config = get_package_share_directory("rover_bringup") + "/config"
    return LaunchDescription(
        [
            Node(
                package="joy_linux",
                executable="joy_linux_node",
                name="joy_linux",
                parameters=[f"{config}/joy_linux.yaml"],
            ),
            Node(
                package="rover_drivetrain",
                executable="rover_drivetrain_node",
                name="drivetrain",
                parameters=[f"{config}/drivetrain.yaml"],
            ),
        ]
    )
