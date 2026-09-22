"""定义与 ROS 无关的任务状态模型."""

from enum import Enum


class TaskState(str, Enum):
    """任务可能处于的状态."""

    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    SCANNING = 'SCANNING'
    REPORTING = 'REPORTING'
    SAFE_STOP = 'SAFE_STOP'


class TaskEvent(str, Enum):
    """可导致任务状态变化的事件."""

    START = 'start'
    ARRIVED = 'arrived'
    SCAN_DONE = 'scan_done'
    REPORT_DONE = 'report_done'


class InvalidTransitionError(ValueError):
    """当事件不适用于当前状态时抛出."""

    def __init__(self, state: TaskState, event: TaskEvent):
        self.state = state
        self.event = event
        super().__init__(
            f'当前状态 {state.value} 不能处理事件 {event.value}'
        )


class TaskStateMachine:
    """只处理业务状态转移，不依赖 ROS 节点和消息."""

    _TRANSITIONS = {
        (TaskState.IDLE, TaskEvent.START): TaskState.RUNNING,
        (TaskState.RUNNING, TaskEvent.ARRIVED): TaskState.SCANNING,
        (TaskState.SCANNING, TaskEvent.SCAN_DONE): TaskState.REPORTING,
        (TaskState.REPORTING, TaskEvent.REPORT_DONE): TaskState.SAFE_STOP,
    }

    def __init__(self, initial_state: TaskState = TaskState.IDLE):
        self._state = initial_state

    @property
    def state(self) -> TaskState:
        """返回当前任务状态."""
        return self._state

    def transition(self, event: TaskEvent) -> TaskState:
        """处理事件并返回新状态."""
        next_state = self._TRANSITIONS.get((self._state, event))
        if next_state is None:
            raise InvalidTransitionError(self._state, event)

        self._state = next_state
        return self._state
