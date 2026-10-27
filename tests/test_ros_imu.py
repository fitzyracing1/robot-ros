"""ros2-jazzy job only: publish a fake sensor_msgs/Imu and check sensor_node consumes it."""
import json, os, subprocess, time
import pytest

rclpy = pytest.importorskip("rclpy")
pytest.importorskip("sensor_msgs.msg")


def test_sensor_node_consumes_fake_imu():
    from rclpy.node import Node
    from sensor_msgs.msg import Imu
    from std_msgs.msg import String
    if not os.environ.get("AMENT_PREFIX_PATH") or subprocess.run(
            ["ros2", "pkg", "prefix", "robot_ros"], capture_output=True).returncode:
        pytest.skip("robot_ros not installed in a sourced workspace")
    proc = subprocess.Popen(["ros2", "run", "robot_ros", "sensor_node", "--ros-args",
                             "-p", "source:=imu", "-p", "imu_topic:=/test/imu",
                             "-p", "publish_period_s:=0.2", "-p", "imu_stale_ms:=1000"])
    rclpy.init()
    n = Node("fake_imu")
    pub = n.create_publisher(Imu, "/test/imu", 10)
    got = []
    n.create_subscription(String, "/robot/sensors", lambda m: got.append(json.loads(m.data)), 10)
    try:
        end = time.time() + 30
        while time.time() < end and not any(j.get("accel_source") == "imu" and j["sensor_ok"]
                                            for j in got):
            m = Imu()
            m.linear_acceleration.x, m.linear_acceleration.y, m.linear_acceleration.z = 0.5, -0.25, 9.7
            pub.publish(m)
            rclpy.spin_once(n, timeout_sec=0.05)
        j = [j for j in got if j.get("accel_source") == "imu" and j["sensor_ok"]]
        assert j, f"sensor_node never reported imu data; got {got[-3:]}"
        assert j[-1]["accel"] == [0.5, -0.25, 9.7]
    finally:
        proc.terminate(); proc.wait(10)
        n.destroy_node(); rclpy.shutdown()
