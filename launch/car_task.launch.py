"""一键启动智能车任务演示的所有节点."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """返回完整任务流程的启动描述."""
    return LaunchDescription([
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
            name='simulate_start',
            output='screen',
        ),
    ])
