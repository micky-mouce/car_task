"""无需 ROS 的业务逻辑检查；不作为 ROS 通信验证."""

import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from car_task.recognition_model import recognize
from car_task.task_model import (
    InvalidTransitionError, TaskEvent, TaskState, TaskStateMachine,
)


class LogicChecks(unittest.TestCase):
    def test_flow(self):
        machine = TaskStateMachine()
        for event, expected in zip(TaskEvent, list(TaskState)[1:]):
            self.assertEqual(machine.transition(event), expected)

    def test_all_invalid_events(self):
        valid = dict(zip(list(TaskState)[:-1], TaskEvent))
        for state in TaskState:
            for event in TaskEvent:
                if valid.get(state) == event:
                    continue
                with self.subTest(state=state, event=event):
                    machine = TaskStateMachine(state)
                    with self.assertRaises(InvalidTransitionError):
                        machine.transition(event)
                    self.assertEqual(machine.state, state)

    def test_teams_and_priority(self):
        for team, ids in [('red', [1, 2, 3]), ('green', [4, 5])]:
            result = recognize(team)
            queue = result['grab_queue']
            self.assertEqual([p['id'] for p in queue], ids)
            self.assertEqual([p['priority'] for p in queue],
                             list(range(1, len(ids) + 1)))
            self.assertTrue(all(p['color'] == team for p in queue))
            self.assertTrue(all(1 <= p['score'] <= 10 for p in queue))
        with self.assertRaises(ValueError):
            recognize('blue')

    def test_python_syntax(self):
        for path in ROOT.rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
