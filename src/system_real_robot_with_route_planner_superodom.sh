#!/bin/bash
# Launch script for real robot with Route Planner using SuperOdom (Livox Mid360)
# 
# SuperOdom provides:
#   - /state_estimation (10Hz laser odometry, 100Hz IMU odom in future)
#   - /registered_scan (registered point cloud)
#
# Note: Max speed is reduced to 0.5 m/s for 10Hz odometry.
#       Increase when 100Hz IMU odometry is enabled.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd $SCRIPT_DIR
source ./install/setup.bash
ros2 launch vehicle_simulator system_real_robot_with_route_planner_superodom.launch.py
