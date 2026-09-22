"""模拟按键启动信号的 ROS 2 节点."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool


class SimulateStartNode(Node):
    """节点启动两秒后发布一次启动指令."""

    def __init__(self):
        super().__init__('simulate_start_node')

        # 创建发布者，向 /start_command 话题发送消息
        self.publisher = self.create_publisher(
            Bool,
            '/start_command',
            10
        )

        # 程序启动2秒后发送启动指令
        self.timer = self.create_timer(2.0, self.send_start)

        self.get_logger().info('模拟启动节点已运行，2秒后启动小车')

    def send_start(self):
        """发布一次真值指令并停止定时器."""
        message = Bool()
        message.data = True

        self.publisher.publish(message)
        self.get_logger().info('已发送启动指令：True')

        # 只发送一次
        self.timer.cancel()


def main(args=None):
    """启动模拟按键节点."""
    rclpy.init(args=args)
    node = SimulateStartNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
