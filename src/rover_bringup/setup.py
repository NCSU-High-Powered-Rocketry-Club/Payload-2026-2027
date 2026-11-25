import setuptools

package_name = "rover_bringup"

setuptools.setup(
    name=package_name,
    version="0.1.0",
    packages=[],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/rover.launch.py"]),
        (f"share/{package_name}/config", ["config/joy_linux.yaml", "config/drivetrain.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="NCSU High Powered Rocketry Club",
    maintainer_email="yarielhdez771@gmail.com",
    description="Launch files and config for the Payload rover.",
    license="MIT",
)
