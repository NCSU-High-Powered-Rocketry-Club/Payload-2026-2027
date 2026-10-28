# Payload 2026-2027

ROS 2 Jazzy workspace (Ubuntu 24.04).

| Package | Purpose |
|---|---|
| `payload_drivetrain` | `drivetrain_node`: subscribes to `/joy`, computes arcade drive (motor output is a TODO stub) |
| `payload_bringup` | Launch file + params; starts `joy_node` (Xbox controller) and the drivetrain |

## Build and run

```bash
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
source install/setup.bash
ros2 launch payload_bringup bringup.launch.py
```

## Dev tooling

uv is used only for dev tooling (ruff); ROS dependencies come from rosdep/apt.

```bash
uv sync
uv run ruff check . && uv run ruff format .
colcon test --packages-select payload_drivetrain
```
