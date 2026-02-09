"""
System launch file for REAL ROBOT using SuperOdom (Livox Mid360).
SuperOdom outputs 10Hz laser odometry to /laser_odom_path.
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource, AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Arguments
    sensor_offset_x = LaunchConfiguration('sensorOffsetX', default='0.3')
    sensor_offset_y = LaunchConfiguration('sensorOffsetY', default='0.0')
    camera_offset_z = LaunchConfiguration('cameraOffsetZ', default='0.0')
    vehicle_x = LaunchConfiguration('vehicleX', default='0.0')
    vehicle_y = LaunchConfiguration('vehicleY', default='0.0')
    max_speed = LaunchConfiguration('maxSpeed', default='0.5')

    # Package directories
    super_odometry_dir = get_package_share_directory('super_odometry')
    local_planner_dir = get_package_share_directory('local_planner')
    terrain_analysis_dir = get_package_share_directory('terrain_analysis')
    vehicle_simulator_dir = get_package_share_directory('vehicle_simulator')

    return LaunchDescription([
        # Declare arguments
        DeclareLaunchArgument('sensorOffsetX', default_value='0.3'),
        DeclareLaunchArgument('sensorOffsetY', default_value='0.0'),
        DeclareLaunchArgument('cameraOffsetZ', default_value='0.0'),
        DeclareLaunchArgument('vehicleX', default_value='0.0'),
        DeclareLaunchArgument('vehicleY', default_value='0.0'),
        DeclareLaunchArgument('maxSpeed', default_value='0.5'),

        # Joystick
        Node(
            package='joy',
            executable='joy_node',
            name='ps3_joy',
            output='screen',
            parameters=[{
                'dev': '/dev/input/js0',
                'deadzone': 0.12,
                'autorepeat_rate': 0.0,
            }]
        ),

        # SuperOdom SLAM (Livox Mid360) - publishes /state_estimation
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(super_odometry_dir, 'launch', 'superodom_autonomy.launch.py')
            )
        ),

        # Local Planner (is_real_robot=true by default)
        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(
                os.path.join(local_planner_dir, 'launch', 'local_planner.launch')
            ),
            launch_arguments={
                'sensorOffsetX': sensor_offset_x,
                'sensorOffsetY': sensor_offset_y,
                'cameraOffsetZ': camera_offset_z,
                'goalX': vehicle_x,
                'goalY': vehicle_y,
                'maxSpeed': max_speed,
            }.items()
        ),

        # Terrain Analysis
        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(
                os.path.join(terrain_analysis_dir, 'launch', 'terrain_analysis.launch')
            )
        ),

        # RVIZ Visualization
        Node(
            package='rviz2',
            executable='rviz2',
            name='rvizGA',
            arguments=['-d', os.path.join(vehicle_simulator_dir, 'rviz', 'vehicle_simulator.rviz')],
            prefix='nice'
        ),
    ])
