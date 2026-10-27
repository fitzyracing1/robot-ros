"""Gravity sense: simulated accelerometer -> tilt, load estimate, is_level."""
import math
import random

G = 9.81


def simulate(tilt_deg=0.0, roll_deg=0.0, payload_kg=0.0, noise=0.0, seed=0, axis="x"):
    """Accelerometer vector (m/s^2) at rest: gravity tilted by pitch/roll.
    Extra payload slightly compresses the mount, read as a small extra z load (sim only)."""
    rnd = random.Random(seed)
    p, r = math.radians(tilt_deg), math.radians(roll_deg)
    mag = G * (1 + 0.01 * payload_kg)
    ax = -mag * math.sin(p)
    ay = mag * math.cos(p) * math.sin(r)
    az = mag * math.cos(p) * math.cos(r)
    return tuple(v + rnd.gauss(0, noise) for v in (ax, ay, az))


def analyze(accel, max_tilt_deg=10.0):
    ax, ay, az = accel
    mag = math.sqrt(ax * ax + ay * ay + az * az) or 1e-9
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, az / mag))))
    return {"accel": [ax, ay, az], "tilt_deg": round(tilt, 2),
            "load_g": round(mag / G, 3), "load_kg_est": round(max(0.0, (mag / G - 1) / 0.01), 1),
            "is_level": tilt <= max_tilt_deg}


# --- real-sensor helpers: the same math works for any (ax, ay, az) vector ---
def to_ms2(vec, units="m/s^2"):
    """Convert an accel vector to m/s^2. units: 'm/s^2' (sensor_msgs/Imu standard) or 'g'."""
    k = {"m/s^2": 1.0, "ms2": 1.0, "g": G}.get(units)
    if k is None:
        raise ValueError(f"unknown accel units {units!r}")
    return tuple(float(v) * k for v in vec)


def calibrate(vec, offset=(0.0, 0.0, 0.0)):
    """Subtract a per-axis bias (m/s^2), measured with the sensor level and still."""
    off = list(offset) + [0.0] * (3 - len(offset))
    return tuple(v - o for v, o in zip(vec, off[:3]))


def from_vector(vec, max_tilt_deg=10.0, units="m/s^2", offset=(0.0, 0.0, 0.0)):
    """Tilt / load / is_level from a real or simulated accel vector."""
    return analyze(calibrate(to_ms2(vec, units), offset), max_tilt_deg)


def offset_from_samples(samples):
    """Calibration offset from samples taken level and at rest: mean - (0, 0, G)."""
    n = len(samples)
    mean = [sum(s[i] for s in samples) / n for i in range(3)]
    return (mean[0], mean[1], mean[2] - G)
