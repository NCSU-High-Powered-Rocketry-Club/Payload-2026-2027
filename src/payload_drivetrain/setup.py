from setuptools import find_packages, setup

package_name = "payload_drivetrain"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="NCSU High Powered Rocketry Club",
    maintainer_email="todo@example.com",
    description="Arcade drive drivetrain node for the Payload rover.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "drivetrain_node = payload_drivetrain.drivetrain_node:main",
        ],
    },
)
