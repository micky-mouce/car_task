"""模拟象棋棋子视觉识别的 ROS 2 节点."""

import json

from car_task import topics
from car_task.recognition_model import recognize
from car_task.runtime import run_node
from car_task.task_model import TaskEvent, TaskState
from rclpy.node import Node
from std_msgs.msg import String


class VisionSimulatorNode(Node):
    """收到扫描状态后发布固定的模拟识别结果."""

    def __init__(self):
        super().__init__('vision_simulator_node')

        self.team = self.declare_parameter('team', 'red').value
        recognize(self.team)
        self.scanning = False
        self.completed = False
        self.scan_timer = None

        self.result_publisher = self.create_publisher(
            String,
            topics.VISION_RESULT,
            10
        )
        self.event_publisher = self.create_publisher(
            String,
            topics.TASK_EVENT,
            10
        )
        self.create_subscription(
            String,
            topics.TASK_STATE,
            self.state_callback,
            10
        )

        self.get_logger().info('视觉模拟节点已启动，等待 SCANNING 状态')

    def state_callback(self, message):
        """在状态机进入 SCANNING 时启动一次识别."""
        if message.data != TaskState.SCANNING.value:
            return
        if self.scanning or self.completed:
            return

        self.scanning = True
        self.get_logger().info('正在识别棋子颜色和类型……')
        self.scan_timer = self.create_timer(2.0, self.finish_scan)

    def finish_scan(self):
        """发布模拟识别结果和扫描完成事件."""
        self.scanning = False
        self.completed = True
        if self.scan_timer is not None:
            self.scan_timer.cancel()

        result = String()
        result.data = json.dumps(recognize(self.team), ensure_ascii=False)
        self.result_publisher.publish(result)
        self.get_logger().info(f'识别完成：{result.data}')

        event = String()
        event.data = TaskEvent.SCAN_DONE.value
        self.event_publisher.publish(event)


def main(args=None):
    """启动视觉模拟节点."""
    run_node(VisionSimulatorNode, args)


if __name__ == '__main__':
    main()
