"""管理智能车任务流程的状态机节点."""

from car_task import topics
from car_task.runtime import run_node
from car_task.task_model import InvalidTransitionError
from car_task.task_model import TaskEvent, TaskState, TaskStateMachine
from rclpy.node import Node
from std_msgs.msg import Bool, String


class TaskStateNode(Node):
    """根据启动指令和任务事件切换小车状态."""

    def __init__(self):
        super().__init__('task_state_node')

        self.state_machine = TaskStateMachine()
        self.vision_result = None

        self.state_publisher = self.create_publisher(
            String,
            topics.TASK_STATE,
            10
        )
        self.report_publisher = self.create_publisher(
            String,
            topics.TASK_REPORT,
            10
        )

        self.create_subscription(
            Bool,
            topics.START_COMMAND,
            self.start_callback,
            10
        )

        self.create_subscription(
            String,
            topics.TASK_EVENT,
            self.event_callback,
            10
        )
        self.create_subscription(
            String,
            topics.VISION_RESULT,
            self.vision_result_callback,
            10
        )

        self.create_timer(1.0, self.publish_state)

        self.get_logger().info('状态节点已启动，当前状态：IDLE')

    def start_callback(self, message):
        """在空闲状态接收一次启动指令."""
        if message.data is not True:
            return

        self.handle_event(TaskEvent.START)

    def event_callback(self, message):
        """根据当前状态处理任务事件."""
        try:
            event = TaskEvent(message.data.strip().lower())
        except ValueError:
            self.get_logger().warning(
                f'收到未知任务事件：{message.data}'
            )
            return

        if event not in (TaskEvent.ARRIVED, TaskEvent.SCAN_DONE):
            self.get_logger().warning(
                f'话题不接收内部任务事件：{event.value}'
            )
            return

        self.handle_event(event)

    def vision_result_callback(self, message):
        """保存最新的视觉识别结果."""
        if self.state_machine.state not in (
                TaskState.SCANNING, TaskState.REPORTING):
            self.get_logger().warning('当前状态不接收视觉结果')
            return

        self.vision_result = message.data
        self.try_finish_report()

    def handle_event(self, event):
        """将事件交给独立状态机处理."""
        old_state = self.state_machine.state
        try:
            new_state = self.state_machine.transition(event)
        except InvalidTransitionError as error:
            self.get_logger().warning(str(error))
            return

        self.get_logger().info(
            f'状态变化：{old_state.value} -> {new_state.value}'
        )
        self.publish_state()

        if new_state is TaskState.RUNNING:
            self.vision_result = None
        elif new_state is TaskState.REPORTING:
            self.try_finish_report()

    def try_finish_report(self):
        """扫描完成且已获得结果时发布报告."""
        if self.state_machine.state is not TaskState.REPORTING:
            return
        if self.vision_result is None:
            return

        message = String()
        message.data = f'任务完成；{self.vision_result}'
        self.report_publisher.publish(message)
        self.get_logger().info(f'已发布任务报告：{message.data}')
        self.handle_event(TaskEvent.REPORT_DONE)

    def publish_state(self):
        """发布当前任务状态."""
        message = String()
        message.data = self.state_machine.state.value
        self.state_publisher.publish(message)


def main(args=None):
    """启动任务状态节点."""
    run_node(TaskStateNode, args)


if __name__ == '__main__':
    main()
