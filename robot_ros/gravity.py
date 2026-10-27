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
