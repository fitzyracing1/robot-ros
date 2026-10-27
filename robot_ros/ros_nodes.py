"""ROS 2 layer (rclpy). Topics:
  /robot/sensors (std_msgs/String JSON job + accel [ax,ay,az] m/s^2)   -> limiter_node
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
    import rclpy
    Node, String = _require()
    rclpy.init(args=args)
    n = Node("sensor_node")
    pub = n.create_publisher(String, "/robot/sensors", 10)
    from .gravity import simulate
    n.declare_parameter("tilt_deg", 0.0)
    job = {"name": "aisle-setting", "cart_width": 2, "racks_needed": 4}

    def tick():
        job["accel"] = list(simulate(n.get_parameter("tilt_deg").value, noise=0.02))  # gravity sense
        pub.publish(String(data=json.dumps(job)))
    n.create_timer(2.0, tick)
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
            job["name"], make_attempt(job, count[0]), accel=job.get("accel"))
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
