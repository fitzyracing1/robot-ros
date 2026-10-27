"""ROS 2 layer (rclpy). Topics:
  /robot/sensors (std_msgs/String JSON job + accel [ax,ay,az] m/s^2, sensor_ok, accel_source)
  /imu/data (sensor_msgs/Imu, param imu_topic)  -> sensor_node   -> limiter_node
  /robot/lit_actions (std_msgs/String JSON)   -> brain_node
  /robot/motion (std_msgs/String JSON plan)   <- brain_node
"""
import json


def _require():
    import rclpy  # noqa: F401
    from rclpy.node import Node
    from std_msgs.msg import String
    return Node, String


def sensor_main(args=None):
    """Params: source ('auto'|'imu'|'sim', default auto: imu if a message arrives within
    imu_detect_timeout_s, else sim), imu_topic (/imu/data), imu_stale_ms (500),
    accel_units ('m/s^2'|'g'), accel_offset ([ax, ay, az] m/s^2), tilt_deg (sim only),
    mpu6050_direct (False; read an MPU-6050 over I2C via smbus2 instead of a ROS driver)."""
    import rclpy
    Node, String = _require()
    rclpy.init(args=args)
    n = Node("sensor_node")
    pub = n.create_publisher(String, "/robot/sensors", 10)
    from .imu_source import ImuSource
    for k, v in (("tilt_deg", 0.0), ("source", "auto"), ("imu_topic", "/imu/data"),
                 ("imu_detect_timeout_s", 3.0), ("imu_stale_ms", 500), ("accel_units", "m/s^2"),
                 ("accel_offset", [0.0, 0.0, 0.0]), ("publish_period_s", 2.0),
                 ("mpu6050_direct", False), ("i2c_bus", 1)):
        n.declare_parameter(k, v)
    P = lambda k: n.get_parameter(k).value
    now = lambda: n.get_clock().now().nanoseconds / 1e9
    src = ImuSource(P("source"), P("imu_detect_timeout_s"), P("imu_stale_ms"), P("accel_units"),
                    tuple(P("accel_offset")), start=now(), log=n.get_logger().info)
    job = {"name": "aisle-setting", "cart_width": 2, "racks_needed": 4}
    if P("source") != "sim":
        from sensor_msgs.msg import Imu

        def on_imu(m):
            a = m.linear_acceleration
            src.on_imu(a.x, a.y, a.z, now())
        n.create_subscription(Imu, P("imu_topic"), on_imu, 10)
        n.get_logger().info(f"gravity source={P('source')} imu_topic={P('imu_topic')}")
    if P("mpu6050_direct"):
        from .mpu6050 import MPU6050
        mpu = MPU6050(P("i2c_bus"))
        n.create_timer(0.02, lambda: src.on_imu(*mpu.read_accel_ms2(), now()))

    def tick():
        accel, ok, mode = src.read(now(), P("tilt_deg"))
        job.update(accel=accel, sensor_ok=ok, accel_source=mode)  # gravity sense
        if not ok:
            n.get_logger().warn(f"IMU data stale/missing (> {P('imu_stale_ms')} ms): self-check dark")
        pub.publish(String(data=json.dumps(job)))
    n.create_timer(P("publish_period_s"), tick)
    rclpy.spin(n)


def limiter_main(args=None):
    import rclpy
    from .limiter import Limiter
    from .aisle import make_attempt
    Node, String = _require()
    rclpy.init(args=args)
    n = Node("limiter_node")
    n.declare_parameter("threshold", 7)
    n.declare_parameter("max_tilt_deg", 10.0)
    pub = n.create_publisher(String, "/robot/lit_actions", 10)
    count = [0]

    def on_job(msg):
        job = json.loads(msg.data)
        count[0] += 1
        res = Limiter(threshold=n.get_parameter("threshold").value,
                      max_tilt_deg=n.get_parameter("max_tilt_deg").value).run(
            job["name"], make_attempt(job, count[0]), accel=job.get("accel"), sensor_ok=job.get("sensor_ok", True))
        n.get_logger().info(f"score={res.score} code={res.code} lit={res.lit} gravity={res.gravity}")
        if res.lit:
            pub.publish(String(data=json.dumps({"task": res.task, "params": res.params,
                                                "score": res.score, "code": res.code, "plan": res.plan})))
    n.create_subscription(String, "/robot/sensors", on_job, 10)
    rclpy.spin(n)


def brain_main(args=None):
    import rclpy
    from .brain import Brain
    from .limiter import Result
    from .tenets import Usage
    Node, String = _require()
    rclpy.init(args=args)
    n = Node("brain_node")
    brain = Brain()
    motion = n.create_publisher(String, "/robot/motion", 10)

    def on_lit(msg):
        d = json.loads(msg.data)
        r = Result(d["task"], d["params"], d["score"], 1, Usage(), d["code"], d["plan"])
        if brain.observe(r):
            motion.publish(String(data=json.dumps(d["plan"])))
            n.get_logger().info(f"learned {brain.suggest(r.task)} tenet_level={brain.tenet_level}")
    n.create_subscription(String, "/robot/lit_actions", on_lit, 10)
    rclpy.spin(n)
