"""ROS2 多目标调度节点：输入、串行下发、结果更新及异常处理."""

import json
import math
import time

from car_task import target_transport as wire
from car_task.runtime import run_node
from car_task.target_model import TargetScheduler
from rclpy.node import Node
from std_msgs.msg import Bool, String


class TargetManagerNode(Node):
    """将纯业务模型连接到话题，并用单调时钟检测反馈超时."""

    def __init__(self):
        super().__init__('target_manager')
        retries = self.declare_parameter('max_retries', 1).value
        self.timeout = float(self.declare_parameter('result_timeout', 8.0).value)
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError('result_timeout 必须为正的有限秒数')
        self.model = TargetScheduler(retries)
        self.start_requested = False
        self.sent_at = None
        self.reported = False
        self.command_pub = self.create_publisher(String, wire.COMMAND, 10)
        self.status_pub = self.create_publisher(
            String, wire.STATUS, wire.retained_qos())
        self.report_pub = self.create_publisher(
            String, wire.REPORT, wire.retained_qos())
        self.create_subscription(
            String, wire.TARGETS, self.on_targets, wire.retained_qos())
        self.create_subscription(Bool, 'start_command', self.on_start, 10)
        self.create_subscription(Bool, wire.STOP, self.on_stop, 10)
        self.create_subscription(String, wire.RESULT, self.on_result, 10)
        self.create_timer(0.1, self.tick)
        self.create_timer(1.0, self.publish_status)
        self.publish_status()
        self.get_logger().info('等待输入和启动；分值优先，同分按编号；一次执行一个')

    def on_targets(self, message):
        """启动前接收完整目标列表，非法数据不覆盖已有列表."""
        try:
            self.model.load(json.loads(message.data))
        except (ValueError, TypeError) as error:
            self.get_logger().warning(f'拒绝目标输入：{error}')
            return
        self.publish_status()

    def on_start(self, message):
        """允许输入之前先收到按键，重复按键不会重复派发."""
        if message.data and self.model.state == 'IDLE':
            self.start_requested = True

    def on_stop(self, message):
        """收到停止指令后取消当前模拟执行，终止本轮调度."""
        if message.data:
            self.stop('收到停止指令')

    def on_result(self, message):
        """只处理当前编号与指令均匹配的有效反馈."""
        try:
            payload = json.loads(message.data)
        except ValueError:
            self.get_logger().warning('忽略非 JSON 反馈')
            return
        if not self.model.feedback(payload):
            self.get_logger().warning('忽略重复、迟到、错号或格式错误的反馈')
            return
        self.sent_at = None
        self.get_logger().info(self.model.reason)
        self.publish_status()
        self.finish_if_needed()

    def tick(self):
        """连接就绪后启动，等待反馈期间禁止下发第二个目标."""
        ready = (self.command_pub.get_subscription_count() > 0
                 and self.count_publishers(wire.RESULT) > 0)
        if self.start_requested and self.model.loaded and ready:
            if self.model.start():
                self.publish_status()
        if self.model.active and self.sent_at is not None:
            if time.monotonic() - self.sent_at >= self.timeout:
                self.stop('反馈超时：取消当前执行并停止整轮，防止执行状态不明时继续')
            return
        if ready:
            command = self.model.dispatch()
            if command:
                self.sent_at = time.monotonic()
                wire.publish_json(self.command_pub, command)
                self.get_logger().info(
                    f'下发 {command["target"]["id"]}，'
                    f'第 {command["attempt"]} 次执行'
                )
                self.publish_status()
        self.finish_if_needed()

    def stop(self, reason):
        """停止后发送带原指令编号的取消消息，并生成终态报告."""
        if self.model.state in ('COMPLETED', 'STOPPED'):
            return
        active = self.model.stop(reason)
        self.sent_at = None
        if active:
            wire.publish_json(self.command_pub, {
                'operation': 'cancel', 'command_id': active['command_id'],
            })
        self.get_logger().warning(reason)
        self.publish_status()
        self.finish_if_needed()

    def finish_if_needed(self):
        """只发布一次最终报告，完成后保持等待，不重新执行目标."""
        if self.model.state in ('COMPLETED', 'STOPPED') and not self.reported:
            self.reported = True
            wire.publish_json(self.report_pub, self.model.snapshot())
            self.get_logger().info('本轮结束，已发布最终报告；重新演示请重启 launch')

    def publish_status(self):
        """发布当前目标、剩余队列、状态及历史结果."""
        wire.publish_json(self.status_pub, self.model.snapshot())


def main(args=None):
    """运行目标管理节点."""
    run_node(TargetManagerNode, args)
