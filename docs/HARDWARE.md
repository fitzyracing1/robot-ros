# Wiring a real accelerometer / IMU

> **Status: untested on physical hardware.** The code path (sensor_msgs/Imu subscription,
> stale detection, fallback to sim, calibration offset, optional MPU-6050 reader) is covered by
> unit tests and a CI test that publishes a *fake* `sensor_msgs/Imu`. Nobody has yet run it with a
> real sensor attached. Treat the steps below as a starting point and check them against your
> board's and breakout's own documentation.

## How it plugs in
`sensor_node` subscribes to `sensor_msgs/msg/Imu` on parameter `imu_topic` (default `/imu/data`) and
uses only `linear_acceleration` (m/s^2, REP 145). Parameters:

| param | default | meaning |
|---|---|---|
| `source` | `auto` | `imu` = real hardware only; `sim` = simulator (CI / no hardware); `auto` = imu if a message arrives within `imu_detect_timeout_s`, else sim (logged loudly as "FALLING BACK TO SIM") |
| `imu_topic` | `/imu/data` | Imu topic |
| `imu_detect_timeout_s` | `3.0` | auto-detect window |
| `imu_stale_ms` | `500` | no Imu message for longer than this -> `sensor_ok=false` -> the self-check is **dark** |
| `accel_units` | `m/s^2` | set `g` only if a driver publishes in g (non-standard) |
| `accel_offset` | `[0,0,0]` | per-axis bias in m/s^2, subtracted before tilt/load |
| `mpu6050_direct` | `false` | read an MPU-6050 directly over I2C with `smbus2` (no ROS driver) |
| `i2c_bus` | `1` | bus for `mpu6050_direct` |

## Wiring (I2C, 3.3 V logic)

Raspberry Pi 40-pin header (physical pin numbers): **3.3V = pin 1, GND = pin 6, SDA1 = pin 3 (GPIO2),
SCL1 = pin 5 (GPIO3)** -> I2C bus 1 (`/dev/i2c-1`). Jetson developer kits use a Pi-compatible 40-pin
header with I2C on pins 3/5, but the Linux bus number differs by model (e.g. bus 1 or 7) - check with
`i2cdetect -l`.

| sensor pin | Pi / Jetson header |
|---|---|
| VCC / VIN | pin 1 (3.3 V) - many breakouts also accept 5 V via an onboard regulator; check yours |
| GND | pin 6 |
| SDA | pin 3 |
| SCL | pin 5 |

Default addresses: MPU-6050 `0x68` (`0x69` with AD0 high); BNO055 `0x28` (`0x29` alt).
Enable I2C (Raspberry Pi OS: `raspi-config` -> Interface -> I2C; Ubuntu: `dtparam=i2c_arm=on` in
`/boot/firmware/config.txt`), then `sudo apt install i2c-tools && i2cdetect -y 1` should show the address.
Note: the BNO055 uses I2C clock stretching, which the Raspberry Pi's I2C controller is known to handle
poorly; a slower bus or the BNO055's UART mode may be needed.

## Driver packages that publish sensor_msgs/Imu

| sensor | package | how verified | topic |
|---|---|---|---|
| BNO055 | `bno055` (github.com/flynneva/bno055) | ROS Index page https://index.ros.org/p/bno055/ lists it as released for Humble, Jazzy and others, v0.5.0, I2C or UART, publishes `bno055/imu` (sensor_msgs/Imu) | `/bno055/imu` |
| MPU-6050 | `ros2_mpu6050` (github.com/kimsniper/ros2_mpu6050) | its GitHub README: ROS 2 Humble, tested on a Raspberry Pi 4B, publishes sensor_msgs/msg/Imu on `/imu/mpu6050`. **Not** on ROS Index as a released binary - build from source; not confirmed on Jazzy | `/imu/mpu6050` |

Unsure / not checked: whether `ros-jazzy-bno055` installs cleanly on a Pi or Jetson image, and whether
`ros2_mpu6050` builds on Jazzy. There are other community MPU-6050 drivers; they were not evaluated.

### BNO055
```bash
sudo apt install ros-jazzy-bno055     # released binary per ROS Index
ros2 run bno055 bno055 --ros-args -p connection_type:=i2c -p i2c_bus:=1 -p i2c_address:=0x28 \
  -r /bno055/imu:=/imu/data
ros2 run robot_ros sensor_node --ros-args -p source:=imu
```
(Alternatively leave the driver alone and point us at it: `-p imu_topic:=/bno055/imu`.)

### MPU-6050
```bash
cd ~/ws/src && git clone https://github.com/kimsniper/ros2_mpu6050 && cd .. \
  && colcon build --packages-select ros2_mpu6050 && source install/setup.bash
ros2 launch ros2_mpu6050 ros2_mpu6050.launch.py      # publishes /imu/mpu6050
ros2 run robot_ros sensor_node --ros-args -p source:=imu -p imu_topic:=/imu/mpu6050
```
Or, without any driver (needs `pip install smbus2`, ±2 g range, address 0x68):
```bash
ros2 run robot_ros sensor_node --ros-args -p source:=imu -p mpu6050_direct:=true -p i2c_bus:=1
```

## Calibration
1. Mount the sensor where it will live; put the robot on a surface you know is level; keep it still.
2. Record ~200 samples: `ros2 topic echo /imu/data --field linear_acceleration` (or log them).
3. Compute the offset (mean minus (0, 0, 9.81)):
   ```python
   from robot_ros.gravity import offset_from_samples
   print(offset_from_samples(samples))   # samples = [(ax, ay, az), ...]
   ```
4. Pass it: `-p accel_offset:="[0.12, -0.08, -0.02]"`. Level now reads ~0 deg tilt and load_g ~1.0.
5. Check: tip the robot by a known angle (e.g. a 10 deg wedge) and confirm `tilt_deg` in the limiter log.
   The ±2 g MPU-6050 range and BNO055 fusion modes have their own calibration (the `ros2_mpu6050`
   calibrate node, the BNO055 `calibration_request` service); do those first.
6. Axis orientation matters: tilt is measured from the sensor's +z axis, so mount it z-up (or remap axes
   in the driver, e.g. BNO055 `placement_axis_remap`).
