"""Pure arcade drive math, kept free of ROS so it is trivially unit-testable."""


def arcade_drive(throttle: float, turn: float) -> tuple[float, float]:
    """Convert throttle/turn inputs in [-1, 1] to (left, right) outputs in [-1, 1].

    Outputs are scaled down together when either side would exceed 1 so the
    turn ratio is preserved.
    """
    left = throttle - turn
    right = throttle + turn
    largest = max(abs(left), abs(right), 1.0)
    return left / largest, right / largest
