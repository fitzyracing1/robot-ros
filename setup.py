from setuptools import setup
setup(
    name="robot_ros", version="0.1.0", packages=["robot_ros"],
    package_data={"robot_ros": ["light.json"]},
    data_files=[("share/ament_index/resource_index/packages", ["resource/robot_ros"]),
                ("share/robot_ros", ["package.xml"])],
    install_requires=["setuptools"], license="MIT",
    entry_points={"console_scripts": [
        "sensor_node = robot_ros.ros_nodes:sensor_main",
        "limiter_node = robot_ros.ros_nodes:limiter_main",
        "brain_node = robot_ros.ros_nodes:brain_main"]},
)
