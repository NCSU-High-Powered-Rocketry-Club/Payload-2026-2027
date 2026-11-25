# Payload 2026-2027

ROS 2 Jazzy workspace (Ubuntu 24.04).

| Package | Purpose |
|---|---|
| `rover_bringup` | Launch file + params; starts `joy__linux_node` (Xbox controller) and the drivetrain |
| `rover_drivetrain` | `drivetrain_node`: subscribes to `/joy`, computes arcade drive (motor output is a TODO stub) |

## Build and run

```bash
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
source install/setup.bash
ros2 launch payload_bringup bringup.launch.py
```