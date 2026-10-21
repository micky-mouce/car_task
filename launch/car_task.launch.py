"""一键启动智能车任务演示的所有节点."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """返回完整任务流程的启动描述."""
    return LaunchDescription([
        DeclareLaunchArgument('auto_start', default_value='true'),
        DeclareLaunchArgument('team', default_value='red'),
        Node(
            package='car_task',
            executable='task_state',
            name='task_state',
            output='screen',
        ),
        Node(
            package='car_task',
            executable='motion_simulator',
            name='motion_simulator',
            output='screen',
        ),
        Node(
            package='car_task',
            executable='vision_simulator',
            parameters=[{'team': LaunchConfiguration('team')}],
            name='vision_simulator',
            output='screen',
        ),
        Node(
            package='car_task',
            executable='display_node',
            name='display_node',
            output='screen',
        ),
        Node(
            package='car_task',
            executable='simulate_start',
            condition=IfCondition(LaunchConfiguration('auto_start')),
            name='simulate_start',
            output='screen',
        ),
    ])
