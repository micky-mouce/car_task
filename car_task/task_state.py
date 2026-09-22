import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


class TaskStateNode(Node):

    def __init__(self):
        super().__init__('task_state_node')

        # 初始状态
        self.state = 'IDLE'

        # 发布当前状态
        self.state_publisher = self.create_publisher(
            String,
            '/task_state',
            10
        )

        # 接收启动指令
        self.create_subscription(
            Bool,
            '/start_command',
            self.start_callback,
            10
        )

        # 接收任务事件
        self.create_subscription(
            String,
            '/task_event',
            self.event_callback,
            10
        )

        # 每秒发布一次当前状态
        self.create_timer(1.0, self.publish_state)

        self.get_logger().info('状态节点已启动，当前状态：IDLE')

    def start_callback(self, message):
        # 只有 IDLE 状态可以接收启动指令
        if message.data is True and self.state == 'IDLE':
            self.change_state('RUNNING')
        else:
            self.get_logger().warning('当前状态不能执行启动操作')

    def event_callback(self, message):
        event = message.data.strip().lower()

        # 规定每个状态收到什么事件后进入下一个状态
        transitions = {
            ('RUNNING', 'scan'): 'SCAN',
            ('SCAN', 'scan_done'): 'REPORT',
            ('REPORT', 'report_done'): 'SAFE_STOP'
        }

        next_state = transitions.get((self.state, event))

        if next_state is None:
            self.get_logger().warning(
                f'无效操作：当前状态={self.state}，收到事件={event}'
            )
            return

        self.change_state(next_state)

    def change_state(self, new_state):
        old_state = self.state
        self.state = new_state

        self.get_logger().info(
            f'状态变化：{old_state} -> {new_state}'
        )

        self.publish_state()

    def publish_state(self):
        message = String()
        message.data = self.state
        self.state_publisher.publish(message)


def main(args=None):
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
