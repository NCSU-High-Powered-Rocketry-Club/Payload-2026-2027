from setuptools import find_packages, setup

package_name = "rover_drivetrain"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="NCSU High Powered Rocketry Club",
    maintainer_email="yarielhdez771@gmail.com",
    description="Arcade drive drivetrain node for the Payload rover.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "rover_drivetrain_node = drivetrain.drivetrain_node:main",
        ],
    },
)
