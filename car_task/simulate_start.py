import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool


class SimulateStartNode(Node):

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
        message = Bool()
        message.data = True

        self.publisher.publish(message)
        self.get_logger().info('已发送启动指令：True')

        # 只发送一次
        self.timer.cancel()


def main(args=None):
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
