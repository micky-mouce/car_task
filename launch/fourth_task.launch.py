"""第四次任务：多目标选择、串行执行、反馈更新与异常演示."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """返回可配置异常类型和动作时长的启动描述."""
    arguments = [
        DeclareLaunchArgument('auto_start', default_value='true'),
        DeclareLaunchArgument('target_file', default_value=PathJoinSubstitution([
            FindPackageShare('car_task'), 'config', 'fourth_targets.json'])),
        DeclareLaunchArgument('max_retries', default_value='1'),
        DeclareLaunchArgument('result_timeout', default_value='8.0'),
        DeclareLaunchArgument('execution_seconds', default_value='3.0'),
        DeclareLaunchArgument('fail_once_ids', default_value='T2'),
        DeclareLaunchArgument('fail_always_ids', default_value=''),
        DeclareLaunchArgument('silent_ids', default_value=''),
    ]

    def parameter(name, value_type):
        return ParameterValue(LaunchConfiguration(name), value_type=value_type)

    return LaunchDescription(arguments + [
        Node(package='car_task', executable='target_input', output='screen',
             parameters=[{'target_file': parameter('target_file', str)}]),
        Node(package='car_task', executable='target_manager', output='screen',
             parameters=[{'max_retries': parameter('max_retries', int),
                          'result_timeout': parameter('result_timeout', float)}]),
        Node(package='car_task', executable='target_executor', output='screen',
             parameters=[{
                 'execution_seconds': parameter('execution_seconds', float),
                 'fail_once_ids': parameter('fail_once_ids', str),
                 'fail_always_ids': parameter('fail_always_ids', str),
                 'silent_ids': parameter('silent_ids', str),
             }]),
        Node(package='car_task', executable='target_display', output='screen'),
        Node(package='car_task', executable='simulate_start', output='screen',
             condition=IfCondition(LaunchConfiguration('auto_start'))),
    ])
