"""管理智能车任务流程的状态机节点."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


class TaskStateNode(Node):
    """根据启动指令和任务事件切换小车状态."""

    def __init__(self):
        super().__init__('task_state_node')

        self.state = 'IDLE'
        self.vision_result = '暂无识别结果'
        self.report_timer = None

        self.state_publisher = self.create_publisher(
            String,
            '/task_state',
            10
        )
        self.report_publisher = self.create_publisher(
            String,
            '/task_report',
            10
        )

        self.create_subscription(
            Bool,
            '/start_command',
            self.start_callback,
            10
        )

        self.create_subscription(
            String,
            '/task_event',
            self.event_callback,
            10
        )
        self.create_subscription(
            String,
            '/vision_result',
            self.vision_result_callback,
            10
        )

        self.create_timer(1.0, self.publish_state)

        self.get_logger().info('状态节点已启动，当前状态：IDLE')

    def start_callback(self, message):
        """在空闲状态接收一次启动指令."""
        if message.data is True and self.state == 'IDLE':
            self.change_state('RUNNING')
        elif message.data is True:
            self.get_logger().warning('当前状态不能执行启动操作')

    def event_callback(self, message):
        """根据当前状态处理任务事件."""
        event = message.data.strip().lower()

        transitions = {
            ('RUNNING', 'arrived'): 'SCANNING',
            ('SCANNING', 'scan_done'): 'REPORTING',
        }

        next_state = transitions.get((self.state, event))

        if next_state is None:
            self.get_logger().warning(
                f'无效操作：当前状态={self.state}，收到事件={event}'
            )
            return

        self.change_state(next_state)

        if next_state == 'REPORTING':
            self.report_timer = self.create_timer(
                1.5,
                self.finish_report
            )

    def vision_result_callback(self, message):
        """保存最新的视觉识别结果."""
        self.vision_result = message.data

    def finish_report(self):
        """发布任务报告并进入安全停车状态."""
        if self.report_timer is not None:
            self.report_timer.cancel()

        message = String()
        message.data = f'任务完成；{self.vision_result}'
        self.report_publisher.publish(message)
        self.get_logger().info(f'已发布任务报告：{message.data}')
        self.change_state('SAFE_STOP')

    def change_state(self, new_state):
        """更新并立即发布任务状态."""
        old_state = self.state
        self.state = new_state

        self.get_logger().info(
            f'状态变化：{old_state} -> {new_state}'
        )

        self.publish_state()

    def publish_state(self):
        """发布当前任务状态."""
        message = String()
        message.data = self.state
        self.state_publisher.publish(message)


def main(args=None):
    """启动任务状态节点."""
    rclpy.init(args=args)
    node = TaskStateNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
