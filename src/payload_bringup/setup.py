from setuptools import find_packages, setup

package_name = "payload_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/bringup.launch.py"]),
        (f"share/{package_name}/config", ["config/joy.yaml", "config/drivetrain.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="NCSU High Powered Rocketry Club",
    maintainer_email="todo@example.com",
    description="Launch files and config for the Payload rover.",
    license="MIT",
)
