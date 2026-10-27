# robot-ros

**ROS 2 feeds the limiter resulting in robot brain.**

```mermaid
flowchart LR
  S[ROS 2: sensor_node<br/>/robot/sensors] --> L[limiter_node<br/>self-score 1-10, retry up to 3, keep best<br/>tenets code CBWT]
  L -- lit only --> B[brain_node<br/>memory + tenet level<br/>reads light.json]
  L -. dark .-> X[held, not passed]
  B --> M[/robot/motion]
```

## Layers
- **ROS 2** (`robot_ros/ros_nodes.py`, rclpy, `std_msgs/String` JSON): `sensor_node`, `limiter_node` (param `threshold`, default 7), `brain_node`.
- **Limiter** (`limiter.py`): each action self-scores 1-10. Below threshold → retry, max 3 tries ("one is good, three is better"), best kept. Each retry adds to Work.
- **Four tenets code** (`tenets.py`): Cost, Bridge, Work, Theory (MSB→LSB), active-low: `0` = within limit (lit), `1` = over (dark). `0000` = online. Only lit actions pass.
- **Growing tenet limits**: tenet level 0 starts tight — $1 cost, 3 hops, 10 steps, 0 unverified claims. After N consecutive lit, high-scoring (≥8) actions (default N=5) limits loosen one step (bounded at level 3: $10, 6 hops, 40 steps, 1 claim). Any dark action tightens back one step. Tracked as `brain.tenet_level`.
- **Brain** (`brain.py`): receives only lit actions, remembers best params per task, uses them as the next first try.
- **Light rules**: `robot_ros/light.json` — hard-coded, read-only; the brain reads it (immutable view) and never writes it.
- **Code rule**: the robot writes its full plan before acting; an action with no plan is dark.
- **First skill — aisle setting** (`aisle.py`): simulated store grid with movable racks; the robot proposes a layout, scores it, retries if low, and builds the `0000` layout.

## Sim demo (no ROS needed)
```bash
python -m robot_ros.demo
python -m pytest -q tests
```
Sample:
```
job 3: tries=1 best=10.0 code=0000 lit -> brain tenet_level=1 params={'aisle_width': 2, 'rack_rows': 5}
```
(demo uses grow_after=3 so level growth shows quickly)

## With ROS 2 (Jazzy/Humble)
```bash
mkdir -p ws/src && cd ws/src && git clone https://github.com/fitzyracing1/robot-ros robot_ros && cd ..
source /opt/ros/jazzy/setup.bash && colcon build && source install/setup.bash
ros2 run robot_ros sensor_node & ros2 run robot_ros limiter_node & ros2 run robot_ros brain_node
ros2 topic echo /robot/motion
```

## CI
`sim` job: pure-Python tests + demo on ubuntu. `ros2-jazzy` job: `ros:jazzy` container, colcon build, rclpy import, tests.

License: MIT © 2026 Joshua Almeida
