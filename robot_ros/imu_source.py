"""Choose the accel source for sensor_node: a real IMU (sensor_msgs/Imu) or the simulator.
Pure Python (no rclpy) so the logic is unit-tested in the sim CI job. Times are seconds."""
from .gravity import simulate, calibrate, to_ms2


class ImuSource:
    def __init__(self, source="auto", detect_timeout_s=3.0, stale_ms=500, units="m/s^2",
                 offset=(0.0, 0.0, 0.0), start=0.0, log=print):
        if source not in ("auto", "imu", "sim"):
            raise ValueError("source must be 'imu', 'sim' or 'auto'")
        self.requested, self.mode = source, (source if source != "auto" else "detecting")
        self.detect_timeout_s, self.stale_s = detect_timeout_s, stale_ms / 1000.0
        self.units, self.offset, self.start, self.log = units, offset, start, log
        self.last_t, self.last_vec = None, None

    def on_imu(self, ax, ay, az, now):
        """Feed sensor_msgs/Imu.linear_acceleration (m/s^2 per REP 145)."""
        self.last_t, self.last_vec = now, calibrate(to_ms2((ax, ay, az), self.units), self.offset)
        if self.mode == "detecting":
            self.mode = "imu"
            self.log("gravity source: real IMU detected -> using imu")

    def read(self, now, tilt_deg=0.0):
        """-> (accel or None, sensor_ok, mode). sensor_ok False = stale/missing IMU -> dark."""
        if self.mode == "detecting" and now - self.start >= self.detect_timeout_s:
            self.mode = "sim"
            self.log(f"gravity source: no IMU message within {self.detect_timeout_s}s "
                     "-> FALLING BACK TO SIM (simulated accelerometer, not real hardware)")
        if self.mode == "sim":
            return list(simulate(tilt_deg, noise=0.02)), True, "sim"
        if self.last_t is None or now - self.last_t > self.stale_s:
            return None, False, self.mode  # imu required (or detecting) but no fresh data: dark
        return list(self.last_vec), True, "imu"
