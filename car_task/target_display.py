"""将第四次任务的状态、队列与进度集中显示为中文日志."""

import json

from car_task import target_transport as wire
from car_task.runtime import run_node
from rclpy.node import Node
from std_msgs.msg import String


class TargetDisplayNode(Node):
    """仅在业务状态变化时显示快照，避免心跳日志刷屏."""

    def __init__(self):
        super().__init__('target_display')
        self.last_status = None
        self.create_subscription(
            String, wire.STATUS, self.on_status, wire.retained_qos())
        self.create_subscription(String, wire.PROGRESS, self.on_progress, 10)
        self.create_subscription(
            String, wire.REPORT, self.on_report, wire.retained_qos())

    def on_status(self, message):
        """显示当前目标、按实际执行顺序排列的队列及结果."""
        if message.data == self.last_status:
            return
        self.last_status = message.data
        data = json.loads(message.data)
        current = data['current']
        label = (f'{current["target"]["id"]} '
                 f'(第{current["attempt"]}次)' if current else '无')
        pending = [f'{t["id"]}({t["score"]}分)' for t in data['pending']]
        done = [t['id'] for t in data['completed']]
        failed = [t['id'] for t in data['failed']]
        self.get_logger().info(
            f'[{data["state"]}] 当前={label} 待执行={pending} '
            f'成功={done} 跳过={failed}；{data["reason"]}'
        )

    def on_progress(self, message):
        """显示当前执行编号和动作进度."""
        data = json.loads(message.data)
        self.get_logger().info(
            f'{data["target_id"]} {data["phase"]} {data["progress"]}%')

    def on_report(self, message):
        """展示含每次尝试记录的最终报告."""
        self.get_logger().info(f'[最终报告] {message.data}')


def main(args=None):
    """运行集中显示节点."""
    run_node(TargetDisplayNode, args)
