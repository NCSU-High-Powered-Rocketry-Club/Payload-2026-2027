"""Launch the Xbox controller (joy_node) and the drivetrain node."""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Build the launch description."""
    config = get_package_share_directory("payload_bringup") + "/config"
    return LaunchDescription(
        [
            Node(
                package="joy",
                executable="joy_node",
                name="joy_node",
                parameters=[f"{config}/joy.yaml"],
            ),
            Node(
                package="payload_drivetrain",
                executable="drivetrain_node",
                name="drivetrain",
                parameters=[f"{config}/drivetrain.yaml"],
            ),
        ]
    )
