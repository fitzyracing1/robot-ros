"""Optional direct I2C reader for an MPU-6050 (behind sensor_node param mpu6050_direct).
Needs `pip install smbus2`; never imported in CI. UNTESTED on physical hardware.
Registers per the InvenSense MPU-6000/6050 register map: PWR_MGMT_1=0x6B, ACCEL_XOUT_H=0x3B,
default full scale +/-2 g = 16384 LSB/g, default I2C address 0x68 (0x69 with AD0 high)."""
from .gravity import G

PWR_MGMT_1, ACCEL_XOUT_H, LSB_PER_G = 0x6B, 0x3B, 16384.0


def _s16(hi, lo):
    v = (hi << 8) | lo
    return v - 65536 if v & 0x8000 else v


def raw_to_ms2(data):
    """6 bytes from ACCEL_XOUT_H.. -> (ax, ay, az) m/s^2 at +/-2 g."""
    return tuple(_s16(data[i], data[i + 1]) / LSB_PER_G * G for i in (0, 2, 4))


class MPU6050:
    def __init__(self, bus=1, address=0x68):
        from smbus2 import SMBus
        self.bus, self.addr = SMBus(bus), address
        self.bus.write_byte_data(self.addr, PWR_MGMT_1, 0)  # wake from sleep

    def read_accel_ms2(self):
        return raw_to_ms2(self.bus.read_i2c_block_data(self.addr, ACCEL_XOUT_H, 6))
