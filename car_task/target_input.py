"""从 JSON 文件读取模拟目标，通过 ROS2 话题发送整批输入."""

import json
from pathlib import Path

from car_task.runtime import run_node
from car_task.target_model import validate_targets
from car_task.target_transport import publish_json, retained_qos, TARGETS
from rclpy.node import Node
from std_msgs.msg import String


class TargetInputNode(Node):
    """发送一次持久化目标消息，保持在线以便后来订阅者获取."""

    def __init__(self):
        super().__init__('target_input')
        path = self.declare_parameter('target_file', '').value
        targets = validate_targets(json.loads(Path(path).read_text('utf-8')))
        self.publisher = self.create_publisher(String, TARGETS, retained_qos())
        publish_json(self.publisher, targets)
        self.get_logger().info(
            f'输入 {len(targets)} 个目标：'
            f'{[target["id"] for target in targets]}（模拟数据）'
        )


def main(args=None):
    """运行目标输入节点."""
    run_node(TargetInputNode, args)
