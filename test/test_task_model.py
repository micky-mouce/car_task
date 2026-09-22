"""测试与 ROS 无关的任务状态机."""

from car_task.task_model import InvalidTransitionError
from car_task.task_model import TaskEvent, TaskState, TaskStateMachine
import pytest


def test_complete_task_flow():
    """完整任务流程应进入安全停车状态."""
    state_machine = TaskStateMachine()

    assert state_machine.state is TaskState.IDLE
    assert state_machine.transition(TaskEvent.START) is TaskState.RUNNING
    assert state_machine.transition(TaskEvent.ARRIVED) is TaskState.SCANNING
    assert state_machine.transition(TaskEvent.SCAN_DONE) is TaskState.REPORTING
    assert state_machine.transition(TaskEvent.REPORT_DONE) is TaskState.SAFE_STOP


def test_invalid_event_does_not_change_state():
    """非法事件应被拒绝且不改变状态."""
    state_machine = TaskStateMachine()

    with pytest.raises(InvalidTransitionError):
        state_machine.transition(TaskEvent.ARRIVED)

    assert state_machine.state is TaskState.IDLE
