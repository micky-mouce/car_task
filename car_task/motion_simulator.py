"""模拟智能车行驶过程的 ROS 2 节点."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, String


class MotionSimulatorNode(Node):
    """在任务运行时发布进度，到达后发布 arrived 事件."""

    def __init__(self):
        super().__init__('motion_simulator_node')

        self.progress = 0
        self.moving = False
        self.completed = False
        self.motion_timer = None

        self.progress_publisher = self.create_publisher(
            Int32,
            '/motion_progress',
            10
        )
        self.event_publisher = self.create_publisher(
            String,
            '/task_event',
            10
        )
        self.create_subscription(
            String,
            '/task_state',
            self.state_callback,
            10
        )

        self.get_logger().info('运动模拟节点已启动，等待 RUNNING 状态')

    def state_callback(self, message):
        """在状态机进入 RUNNING 时开始模拟行驶."""
        if message.data != 'RUNNING':
            return
        if self.moving or self.completed:
            return

        self.moving = True
        self.progress = 0
        self.get_logger().info('小车开始向棋子区域行驶')
        self.publish_progress()
        self.motion_timer = self.create_timer(1.0, self.advance_motion)

    def advance_motion(self):
        """推进模拟行驶进度."""
        self.progress = min(self.progress + 20, 100)
        self.publish_progress()

        if self.progress < 100:
            return

        self.moving = False
        self.completed = True
        if self.motion_timer is not None:
            self.motion_timer.cancel()

        event = String()
        event.data = 'arrived'
        self.event_publisher.publish(event)
        self.get_logger().info('小车已到达棋子区域')

    def publish_progress(self):
        """发布当前行驶百分比."""
        message = Int32()
        message.data = self.progress
        self.progress_publisher.publish(message)


def main(args=None):
    """启动运动模拟节点."""
    rclpy.init(args=args)
    node = MotionSimulatorNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
