import pytest
from payload_drivetrain.arcade import arcade_drive


def test_forward():
    assert arcade_drive(0.5, 0.0) == (0.5, 0.5)


def test_spin_in_place():
    assert arcade_drive(0.0, 1.0) == (-1.0, 1.0)


def test_saturation_preserves_ratio():
    left, right = arcade_drive(1.0, 1.0)
    assert (left, right) == pytest.approx((0.0, 1.0))
