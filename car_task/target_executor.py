"""一次只执行一个目标的移动及抓取模拟器，可注入失败与无反馈异常."""

import json
import math
import time

from car_task import target_transport as wire
from car_task.runtime import run_node
from car_task.target_model import validate_targets
from rclpy.node import Node
from std_msgs.msg import String


class TargetExecutorNode(Node):
    """按定时进度模拟动作，按指令编号去重，并支持取消当前动作."""

    def __init__(self):
        super().__init__('target_executor')
        self.duration = float(
            self.declare_parameter('execution_seconds', 3.0).value)
        if not math.isfinite(self.duration) or self.duration <= 0:
            raise ValueError('execution_seconds 必须为正的有限秒数')
        self.fail_once = self.read_ids('fail_once_ids', 'T2')
        self.fail_always = self.read_ids('fail_always_ids', '')
        self.silent = self.read_ids('silent_ids', '')
        self.active = None
        self.started_at = None
        self.last_progress = None
        self.seen = set()
        self.result_pub = self.create_publisher(String, wire.RESULT, 10)
        self.progress_pub = self.create_publisher(String, wire.PROGRESS, 10)
        self.create_subscription(String, wire.COMMAND, self.on_command, 10)
        self.create_timer(0.1, self.tick)
        self.get_logger().info('执行节点就绪，模拟移动及抓取，不连接真实硬件')

    def read_ids(self, name, default):
        """以逗号分隔的字符串配置异常目标，空串表示不注入异常."""
        value = self.declare_parameter(name, default).value
        return {item.strip() for item in value.split(',') if item.strip()}

    def on_command(self, message):
        """处理执行或取消指令，忙碌时拒绝第二个目标."""
        try:
            command = json.loads(message.data)
            if not isinstance(command, dict):
                raise ValueError('指令必须为对象')
            command_id = command['command_id']
            if not isinstance(command_id, str) or not command_id:
                raise ValueError('缺少有效 command_id')
            if command.get('operation') == 'cancel':
                self.seen.add(command_id)
                if self.active and self.active['command_id'] == command_id:
                    self.get_logger().warning('取消当前模拟动作')
                    self.active = None
                return
            if command.get('operation') != 'execute':
                raise ValueError('未知 operation')
            validate_targets([command['target']])
            attempt = command['attempt']
            if (isinstance(attempt, bool) or not isinstance(attempt, int)
                    or attempt < 1):
                raise ValueError('attempt 必须为正整数')
        except (ValueError, TypeError, KeyError) as error:
            self.get_logger().warning(f'拒绝错误指令：{error}')
            return
        if command_id in self.seen:
            self.get_logger().warning('忽略已处理的重复指令')
            return
        if self.active:
            wire.publish_json(self.result_pub, {
                'command_id': command_id, 'target_id': command['target']['id'],
                'status': 'failure', 'detail': '执行器忙碌，拒绝并行执行',
            })
            return
        self.seen.add(command_id)
        self.active = command
        self.started_at = time.monotonic()
        self.last_progress = None
        self.get_logger().info(
            f'开始 {command["target"]["id"]}，第 {command["attempt"]} 次执行')

    def tick(self):
        """前 70% 模拟移动，随后模拟抓取，结束时生成成功或失败反馈."""
        if not self.active:
            return
        elapsed = time.monotonic() - self.started_at
        progress = min(100, int(elapsed / self.duration * 5) * 20)
        command = self.active
        target_id = command['target']['id']
        if progress != self.last_progress:
            wire.publish_json(self.progress_pub, {
                'command_id': command['command_id'], 'target_id': target_id,
                'progress': progress,
                'phase': '移动' if progress < 70 else '抓取',
            })
            self.last_progress = progress
        if elapsed < self.duration:
            return
        self.active = None
        if target_id in self.silent:
            self.get_logger().warning(f'{target_id} 注入无反馈异常，等待管理器超时')
            return
        failure = (target_id in self.fail_always
                   or (target_id in self.fail_once and command['attempt'] == 1))
        wire.publish_json(self.result_pub, {
            'command_id': command['command_id'], 'target_id': target_id,
            'status': 'failure' if failure else 'success',
            'detail': '模拟抓取失败' if failure else '模拟移动和抓取成功',
        })


def main(args=None):
    """运行目标执行模拟节点."""
    run_node(TargetExecutorNode, args)
