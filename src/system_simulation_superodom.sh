#!/bin/bash
# Launch script for SIMULATION using SuperOdom (Livox Mid360)
# 
# Usage:
#   1. Start this script in one terminal:
#      ./system_simulation_superodom.sh
#
#   2. In another terminal, play your bag file with clock:
#      ros2 bag play <your_bag_file> --clock
#
# The bag file should contain:
#   - /livox/lidar (Livox point cloud)
#   - /livox/imu (IMU data)
#
# SuperOdom will output:
#   - /state_estimation_go2 (10Hz odometry)
#   - /registered_scan (registered point cloud)
#
# Note: is_real_robot=false, no commands sent to Go2

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd $SCRIPT_DIR
source ./install/setup.bash
ros2 launch vehicle_simulator system_simulation_superodom.launch.py

# ros2 launch vehicle_simulator system_simulation_superodom.launch.py sensorOffsetX:=0.35 sensorOffsetY:=0.05