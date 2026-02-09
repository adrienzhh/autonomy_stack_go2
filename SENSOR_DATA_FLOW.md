# Sensor Input Stream and Data Flow Documentation

This document describes the sensor input streams and data flow between modules (SLAM, Base Autonomy, and Route Planner) in the Go2 Autonomy Stack.

---

## Overview

The system contains three main modules:
1. **SLAM Module** (SuperOdom) - Sensor fusion and state estimation
2. **Base Autonomy System** - Local planning, terrain analysis, and path following
3. **Route Planner** (FAR Planner) - Global path planning with visibility graph

---

## Raw Sensor Inputs

| Topic | Type | Description |
|-------|------|-------------|
| Configured `laser_topic` | PointCloud2 / Livox CustomMsg | Raw lidar point cloud |
| Configured `imu_topic` | IMU | IMU data |

---

## 1. SLAM Module (SuperOdom)

SuperOdom consists of three main nodes:
1. **Feature Extraction Node** - Extracts features from lidar scans
2. **Laser Mapping Node** - Performs scan matching and mapping
3. **IMU Preintegration Node** - Fuses IMU data for high-rate odometry

### 1.1 Feature Extraction Node

**Subscribes:**
| Topic | Type | Description |
|-------|------|-------------|
| `laser_topic` (configured) | PointCloud2 / Livox CustomMsg | Raw lidar point cloud |
| `imu_topic` (configured) | IMU | IMU data |

**Publishes:**
| Topic | Type | Description |
|-------|------|-------------|
| `/super_odometry/feature_info` | LaserFeature | Extracted features |

### 1.2 Laser Mapping Node

**Subscribes:**
| Topic | Type | Description |
|-------|------|-------------|
| `/super_odometry/feature_info` | LaserFeature | From feature extraction |

**Publishes:**
| Topic | Type | Rate | Description |
|-------|------|------|-------------|
| `/super_odometry/laser_odometry` | Odometry | **10 Hz** | Main laser odometry output |
| `/super_odometry/registered_scan` | PointCloud2 | 10 Hz | Registered point cloud (world frame) |
| `/super_odometry/laser_cloud_map` | PointCloud2 | - | Accumulated map |
| `/super_odometry/laser_odom_path` | Path | - | Trajectory path |
| `/super_odometry/lio_prediction` | Odometry | - | LIO prediction |

### 1.3 IMU Preintegration Node (Future: 100 Hz Odometry)

**Subscribes:**
| Topic | Type | Description |
|-------|------|-------------|
| `imu_topic` (configured) | IMU | Raw IMU data |
| `/super_odometry/laser_odometry` | Odometry | From laser mapping (10 Hz) |

**Publishes:**
| Topic | Type | Rate | Description |
|-------|------|------|-------------|
| `/super_odometry/state_estimation` | Odometry | **100 Hz** | IMU-fused high-rate odometry (FUTURE) |
| `/super_odometry/state_estimation_health` | Bool | - | Health status |
| `/super_odometry/imuodom_path` | Path | - | IMU odometry path |

### Output Rate Summary

| Output | Current | Future |
|--------|---------|--------|
| **State Estimation** | 10 Hz (`/laser_odometry`) | 100 Hz (`/state_estimation` via IMU preintegration) |
| **Registered Scan** | 10 Hz | 10 Hz |

### Topic Remapping Configuration

SuperOdom publishes to `/state_estimation_go2`, and base autonomy nodes are remapped to consume it:

| SuperOdom Topic | Published To | Base Autonomy Consumes |
|-----------------|--------------|------------------------|
| `/super_odometry/laser_odometry` | `/state_estimation_go2` | `/state_estimation` → `/state_estimation_go2` |
| `/super_odometry/registered_scan` | `/registered_scan` | `/registered_scan` |

**How it works:**
1. SuperOdom's `superodom_autonomy.launch.py` remaps output to `/state_estimation_go2`
2. System launch files use `<set_remap from="/state_estimation" to="/state_estimation_go2"/>` 
3. All base autonomy nodes subscribe to `/state_estimation_go2` via this remap

**Current (10 Hz):**
```bash
# SuperOdom publishes
/super_odometry/laser_odometry -> /state_estimation_go2
# Base autonomy subscribes via remap
/state_estimation -> /state_estimation_go2
```

**Future (100 Hz with IMU preintegration):**
```bash
# Change SuperOdom to use IMU-fused odometry
/super_odometry/state_estimation -> /state_estimation_go2
```

---

## 2. Base Autonomy System

### 2.1 Sensor Scan Generation

Transforms registered cloud to sensor frame for downstream processing.

**Subscribes:**
| Topic | Type |
|-------|------|
| `/state_estimation` | Odometry |
| `/registered_scan` | PointCloud2 |

**Publishes:**
| Topic | Type |
|-------|------|
| `/sensor_scan` | PointCloud2 |
| `/state_estimation_at_scan` | Odometry |

### 2.2 Terrain Analysis

Analyzes terrain traversability and obstacle heights.

**Subscribes:**
| Topic | Type |
|-------|------|
| `/state_estimation` | Odometry |
| `/registered_scan` | PointCloud2 |
| `/joy` | Joy |
| `/map_clearing` | Float32 |

**Publishes:**
| Topic | Type | Description |
|-------|------|-------------|
| `/terrain_map` | PointCloud2 | Elevation-analyzed point cloud |

### 2.3 Terrain Analysis Extended

Extended terrain analysis for route planner integration.

**Subscribes:**
| Topic | Type |
|-------|------|
| `/state_estimation` | Odometry |
| `/registered_scan` | PointCloud2 |
| `/joy` | Joy |
| `/cloud_clearing` | Float32 |
| `/terrain_map` | PointCloud2 |

**Publishes:**
| Topic | Type |
|-------|------|
| `/terrain_map_ext` | PointCloud2 |

### 2.4 Local Planner

Collision avoidance and local path planning.

**Subscribes:**
| Topic | Type |
|-------|------|
| `/state_estimation` | Odometry |
| `/registered_scan` | PointCloud2 |
| `/terrain_map` | PointCloud2 |
| `/way_point` | PointStamped |
| `/joy` | Joy |
| `/speed` | Float32 |
| `/navigation_boundary` | PolygonStamped |
| `/added_obstacles` | PointCloud2 |
| `/check_obstacle` | Bool |

**Publishes:**
| Topic | Type | Description |
|-------|------|-------------|
| `/path` | Path | Collision-free local path |
| `/free_paths` | PointCloud2 | Visualization of free paths |

### 2.5 Path Follower

Velocity control for path tracking.

**Subscribes:**
| Topic | Type |
|-------|------|
| `/state_estimation` | Odometry |
| `/path` | Path |
| `/joy` | Joy |
| `/speed` | Float32 |
| `/stop` | Int8 |

**Publishes:**
| Topic | Type | Description |
|-------|------|-------------|
| `/cmd_vel` | TwistStamped | Velocity commands |
| `/api/sport/request` | Request | Go2 robot API commands (real robot) |

---

## 3. Route Planner (FAR Planner)

Global path planning using visibility graph.

### Subscribes

| Topic | Type | Source |
|-------|------|--------|
| `/odom_world` | Odometry | From SLAM (remapped `/state_estimation`) |
| `/terrain_cloud` | PointCloud2 | From terrain analysis (remapped `/terrain_map`) |
| `/scan_cloud` | PointCloud2 | From sensor scan (remapped `/sensor_scan`) |
| `/terrain_local_cloud` | PointCloud2 | Local terrain cloud |
| `/goal_point` | PointStamped | User goal input |
| `/joy` | Joy | Joystick commands |
| `/reset_visibility_graph` | Empty | Reset graph command |
| `/update_visibility_graph` | Bool | Update graph command |

### Publishes

| Topic | Type | Description |
|-------|------|-------------|
| `/way_point` | PointStamped | Intermediate waypoint to Base Autonomy |
| `/navigation_boundary` | PolygonStamped | Local boundary constraints |
| `/runtime` | Float32 | V-Graph update time |
| `/planning_time` | Float32 | Path planning time |
| `/far_reach_goal_status` | Bool | Goal reached status |

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAW SENSORS                                  │
│         laser_topic (LiDAR)              imu_topic (IMU)            │
└─────────────────┬─────────────────────────┬─────────────────────────┘
                  │                         │
                  ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SLAM (SuperOdom)                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Feature Extraction → Laser Mapping → IMU Preintegration    │    │
│  │        (10 Hz)           (10 Hz)         (100 Hz future)    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Current:  /laser_odometry (10 Hz)    /registered_scan (10 Hz)      │
│  Future:   /state_estimation (100 Hz) /registered_scan (10 Hz)      │
└─────────────────┬─────────────────────────┬─────────────────────────┘
                  │                         │
                  │    [REMAP TO]           │    [REMAP TO]
                  │  /state_estimation_go2  │  /registered_scan
                  │                         │
        ┌─────────┴─────────────────────────┴─────────┐
        ▼                                             ▼
┌───────────────────────┐                   ┌───────────────────────┐
│   ROUTE PLANNER       │                   │   BASE AUTONOMY       │
│   (FAR Planner)       │                   │                       │
│   (5 Hz)              │                   │  ┌─────────────────┐  │
│                       │                   │  │ Terrain Analysis│  │
│  /terrain_cloud ◄─────┼───────────────────┼──┤ /terrain_map    │  │
│  /odom_world    ◄─────┼───────────────────┼──┤                 │  │
│  /scan_cloud    ◄─────┼───────────────────┼──┤                 │  │
│                       │                   │  └─────────────────┘  │
│  Publishes:           │                   │           │           │
│  /way_point ──────────┼───────────────────┼───────────▼──────────│
│  /navigation_boundary─┼───────────────────┼──►┌─────────────────┐ │
│                       │                   │   │ Local Planner   │ │
└───────────────────────┘                   │   │ /path           │ │
                                            │   └────────┬────────┘ │
                                            │            ▼          │
                                            │   ┌─────────────────┐ │
                                            │   │ Path Follower   │ │
                                            │   │ /cmd_vel        │ │
                                            │   └────────┬────────┘ │
                                            └────────────┼──────────┘
                                                         ▼
                                                   Robot Motion
```

---

## Processing Rates

### Module Processing Rates

| Module | Processing Rate | Notes |
|--------|-----------------|-------|
| **SLAM (SuperOdom) - Laser Mapping** | 10 Hz | Lidar frame rate |
| **SLAM (SuperOdom) - IMU Preintegration** | 100 Hz | IMU rate (future integration) |
| **Local Planner** | 100 Hz | `rclcpp::Rate rate(100)` |
| **Path Follower** | 100 Hz | `rclcpp::Rate rate(100)` |
| **Terrain Analysis** | 100 Hz | `rclcpp::Rate rate(100)` |
| **Terrain Analysis Ext** | 100 Hz | `rclcpp::Rate rate(100)` |
| **Vehicle Simulator** | 200 Hz | `rclcpp::Rate rate(200)` |
| **FAR Planner (Route)** | 5 Hz | `main_run_freq: 5.0` |

### State Estimation Rate

| Configuration | Rate | Source Topic |
|---------------|------|--------------|
| **Current** | 10 Hz | `/super_odometry/laser_odometry` |
| **Future** | 100 Hz | `/super_odometry/state_estimation` (IMU preintegration) |

### Required vs Available Rate

- **Base Autonomy designed for**: ~100 Hz
- **Current SuperOdom output**: 10 Hz
- **Future SuperOdom output**: 100 Hz (with IMU preintegration)

---

## State Estimation Rate Impact Analysis

### Current Status: 10 Hz (SuperOdom Laser Odometry)

The current setup uses `/super_odometry/laser_odometry` at **10 Hz**. This is below the designed rate but functional with adjustments.

### Impact of Odometry Rates

| Odom Rate | Position Error at 1 m/s | Recommended Max Speed | Status |
|-----------|-------------------------|----------------------|--------|
| 100 Hz | ~1 cm | 1.0 m/s | **Future** (IMU preintegration) |
| 50 Hz | ~2 cm | 0.8 m/s | - |
| 30 Hz | ~3.3 cm | 0.5 m/s | - |
| **10 Hz** | **~10 cm** | **0.3 m/s** | **Current** |

### Issues at 10 Hz State Estimation (Current)

1. **Path Follower Control Loop**
   - Robot position updates only every 100ms instead of 10ms
   - Control loop uses stale position data for ~10 iterations between updates
   - Acceleration ramp is tuned for 100 Hz

2. **Motion Latency**
   - At max speed (1 m/s): 10 cm position error between updates
   - Collision avoidance reaction time increases from ~10ms to ~100ms

3. **Recommendations for Low-Rate Operation**
   - Reduce `maxSpeed` parameter (0.3-0.5 m/s)
   - Increase `lookAheadDis` parameter
   - Lower `maxAccel` to smooth out jerky behavior
   - Use more conservative obstacle thresholds

---

## Key Observations

1. **SuperOdom is the core sensor processor** - All other modules depend on its outputs:
   - Current: `/super_odometry/laser_odometry` (10 Hz) and `/super_odometry/registered_scan`
   - Future: `/super_odometry/state_estimation` (100 Hz) with IMU preintegration

2. **Route Planner sits above Base Autonomy** - It provides high-level goals (`/way_point`) and boundary constraints (`/navigation_boundary`) while Base Autonomy handles local collision avoidance

3. **Topic remapping connects modules** - Launch files remap SuperOdom topics:
   - `/super_odometry/laser_odometry` → `/state_estimation_go2`
   - `/super_odometry/registered_scan` → `/registered_scan`
   - Base autonomy nodes: `/state_estimation` → `/state_estimation_go2` (via `<set_remap>`)

4. **Event-driven processing** - Most modules process data when new sensor data arrives, not at fixed rates

5. **10 Hz limitation is temporary** - Once IMU preintegration is enabled, the system will operate at full 100 Hz capability

---

## Source Files Reference

| Module | Source File |
|--------|-------------|
| SLAM - Feature Extraction | `src/slam/SuperOdom/super_odometry/src/FeatureExtraction/featureExtraction.cpp` |
| SLAM - Laser Mapping | `src/slam/SuperOdom/super_odometry/src/LaserMapping/laserMapping.cpp` |
| SLAM - IMU Preintegration | `src/slam/SuperOdom/super_odometry/src/ImuPreintegration/imuPreintegration.cpp` |
| Sensor Scan Generation | `src/base_autonomy/sensor_scan_generation/src/sensorScanGeneration.cpp` |
| Terrain Analysis | `src/base_autonomy/terrain_analysis/src/terrainAnalysis.cpp` |
| Terrain Analysis Ext | `src/base_autonomy/terrain_analysis_ext/src/terrainAnalysisExt.cpp` |
| Local Planner | `src/base_autonomy/local_planner/src/localPlanner.cpp` |
| Path Follower | `src/base_autonomy/local_planner/src/pathFollower.cpp` |
| FAR Planner | `src/route_planner/far_planner/src/far_planner.cpp` |

---

## Configuration Files

| Module | Config File |
|--------|-------------|
| SuperOdom (Livox Mid360) | `src/slam/SuperOdom/super_odometry/config/livox_mid360.yaml` |
| SuperOdom (Velodyne VLP-16) | `src/slam/SuperOdom/super_odometry/config/vlp_16.yaml` |
| SuperOdom (Ouster OS1-128) | `src/slam/SuperOdom/super_odometry/config/os1_128.yaml` |
| FAR Planner | `src/route_planner/far_planner/config/default.yaml` |

---

## Launch Files

### SuperOdom Integration Launch Files

| File | Description |
|------|-------------|
| `src/slam/SuperOdom/super_odometry/launch/superodom_autonomy.launch.py` | SuperOdom with topic remappings for base autonomy |
| `src/base_autonomy/vehicle_simulator/launch/system_real_robot_superodom.launch` | Real robot system with SuperOdom |
| `src/base_autonomy/vehicle_simulator/launch/system_real_robot_with_route_planner_superodom.launch` | Real robot with route planner using SuperOdom |

### Shell Scripts

| Script | Description |
|--------|-------------|
| `./system_real_robot_superodom.sh` | Launch real robot with SuperOdom (base autonomy only) |
| `./system_real_robot_with_route_planner_superodom.sh` | Launch real robot with SuperOdom + FAR Planner |
| `./system_simulation_superodom.sh` | Launch simulation with SuperOdom (bag replay) |
| `./system_simulation_with_route_planner_superodom.sh` | Launch simulation with SuperOdom + FAR Planner |

---

## Usage

### Running with SuperOdom (Livox Mid360)

**Real Robot - Base Autonomy Only:**
```bash
cd autonomy_stack_go2
./system_real_robot_superodom.sh
```

**Real Robot - With Route Planner:**
```bash
cd autonomy_stack_go2
./system_real_robot_with_route_planner_superodom.sh
```

### Simulation (Bag Replay)

**Step 1:** Start the simulation system in one terminal:
```bash
cd autonomy_stack_go2
./system_simulation_superodom.sh
# Or with route planner:
./system_simulation_with_route_planner_superodom.sh
```

**Step 2:** In another terminal, play your bag file with clock:
```bash
ros2 bag play <your_bag_file> --clock
```

**Required bag topics:**
- `/livox/lidar` - Livox point cloud
- `/livox/imu` - IMU data

**SuperOdom outputs:**
- `/state_estimation_go2` (10Hz odometry)
- `/registered_scan` (registered point cloud)

**Key differences in simulation:**
- `use_sim_time: true` - Uses bag timestamps
- `is_real_robot: false` - No commands sent to Go2
- No actual robot motion

### Current Configuration (10 Hz)

The current setup uses `/super_odometry/laser_odometry` at **10 Hz**. The launch files automatically:
- Remap SuperOdom outputs to base autonomy expected topics
- Set `maxSpeed` to 0.5 m/s (reduced for 10 Hz odometry)

### Future Configuration (100 Hz)

When IMU preintegration is enabled:
1. Edit `superodom_autonomy.launch.py`
2. Change the remapping from `/super_odometry/laser_odometry` to `/super_odometry/state_estimation`
3. Increase `maxSpeed` back to 1.0 m/s in the system launch files

---

## Integration Notes

### Topic Remappings (Handled Automatically)

The `superodom_autonomy.launch.py` handles these remappings:

| SuperOdom Output | Published Topic | Base Autonomy Consumes |
|------------------|-----------------|------------------------|
| `/super_odometry/laser_odometry` | `/state_estimation_go2` | `/state_estimation` (remapped) |
| `/super_odometry/registered_scan` | `/registered_scan` | `/registered_scan` |

### Current Limitations (10 Hz)

- Max speed reduced to 0.5 m/s
- Position updates every 100ms
- Suitable for slow navigation and testing

### When 100 Hz IMU Odometry is Ready

Update `superodom_autonomy.launch.py`:

```python
# Change this remapping in superodom_autonomy.launch.py:
("/super_odometry/laser_odometry", "/state_estimation_go2"),
# To:
("/super_odometry/state_estimation", "/state_estimation_go2"),
```

Then increase `maxSpeed` in the launch files to 1.0 m/s.

---

*Generated from codebase analysis*
