"""集中显示智能车任务信息的 ROS 2 节点."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, String


class DisplayNode(Node):
    """订阅流程中的主要话题，便于在终端演示."""

    def __init__(self):
        super().__init__('display_node')

        self.last_state = None
        self.create_subscription(
            String,
            '/task_state',
            self.state_callback,
            10
        )
        self.create_subscription(
            Int32,
            '/motion_progress',
            self.progress_callback,
            10
        )
        self.create_subscription(
            String,
            '/vision_result',
            self.vision_callback,
            10
        )
        self.create_subscription(
            String,
            '/task_report',
            self.report_callback,
            10
        )

        self.get_logger().info('显示节点已启动')

    def state_callback(self, message):
        """只在状态变化时显示新状态."""
        if message.data == self.last_state:
            return
        self.last_state = message.data
        self.get_logger().info(f'[任务状态] {message.data}')

    def progress_callback(self, message):
        """显示小车的模拟行驶进度."""
        self.get_logger().info(f'[行驶进度] {message.data}%')

    def vision_callback(self, message):
        """显示模拟视觉识别结果."""
        self.get_logger().info(f'[视觉结果] {message.data}')

    def report_callback(self, message):
        """显示最终任务报告."""
        self.get_logger().info(f'[任务报告] {message.data}')


def main(args=None):
    """启动集中显示节点."""
    rclpy.init(args=args)
    node = DisplayNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
