"""覆盖多目标调度的顺序、去重、有限重试与终止边界."""

from copy import deepcopy

from car_task.target_model import TargetScheduler, validate_targets
import pytest


TARGETS = [
    {'id': 'T3', 'category': '兵', 'score': 1, 'x': 0.2, 'y': 0.3},
    {'id': 'T2', 'category': '马', 'score': 5, 'x': 1.0, 'y': 0.3},
    {'id': 'T1', 'category': '车', 'score': 9, 'x': 2.0, 'y': 0.3},
]


def result(command, status='success'):
    """构造带目标编号和指令编号的匹配反馈."""
    return {'target_id': command['target']['id'],
            'command_id': command['command_id'], 'status': status}


def scheduler(max_retries=1):
    """创建已加载并启动的独立调度器."""
    model = TargetScheduler(max_retries)
    model.load(deepcopy(TARGETS))
    assert model.start()
    return model


def test_serial_priority_and_no_reexecution():
    """按分值选择，未收到结果不下发，完成后不重启."""
    model = scheduler()
    for target_id in ('T1', 'T2', 'T3'):
        command = model.dispatch()
        assert command['target']['id'] == target_id
        assert model.dispatch() is None
        assert not model.start()
        assert model.feedback(result(command))
        assert not model.feedback(result(command))
    assert model.state == 'COMPLETED'
    assert not model.pending
    assert model.dispatch() is None
    assert not model.start()
    assert len(model.completed) == 3


def test_failure_retry_and_exhaustion():
    """失败只重试一次，持续失败移出队列，其余目标继续执行."""
    model = scheduler()
    first = model.dispatch()
    assert model.feedback(result(first, 'failure'))
    retry = model.dispatch()
    assert retry['target'] == first['target']
    assert retry['attempt'] == 2
    assert retry['command_id'] != first['command_id']
    assert not model.feedback(result(first))
    assert model.feedback(result(retry, 'failure'))
    assert [t['id'] for t in model.failed] == ['T1']
    assert model.dispatch()['target']['id'] == 'T2'


def test_retry_can_succeed():
    """失败重试成功只计入一次已完成目标."""
    model = scheduler()
    assert model.feedback(result(model.dispatch(), 'failure'))
    assert model.feedback(result(model.dispatch()))
    assert len(model.completed) == 1
    assert len(model.history) == 2
    assert not model.failed
    assert [t['id'] for t in model.pending] == ['T2', 'T3']


@pytest.mark.parametrize('payload', [
    None, [], 'success', {},
    {'target_id': 'T1', 'command_id': 'wrong', 'status': 'success'},
])
def test_invalid_feedback_preserves_current(payload):
    """错误和非对象反馈不能推进队列."""
    model = scheduler()
    command = model.dispatch()
    assert not model.feedback(payload)
    assert model.active == command
    assert len(model.pending) == 2


def test_wrong_target_and_status_are_rejected():
    """指令编号匹配仍须检查目标编号和结果值."""
    model = scheduler()
    command = model.dispatch()
    for field, value in [('target_id', 'T9'), ('status', True)]:
        payload = result(command)
        payload[field] = value
        assert not model.feedback(payload)
    assert model.active == command


def test_stop_rejects_late_feedback_and_future_dispatch():
    """停止保留未执行列表，迟到成功也不能继续调度."""
    model = scheduler()
    command = model.dispatch()
    assert model.stop('超时') == command
    assert model.state == 'STOPPED'
    assert model.active is None
    assert [t['id'] for t in model.cancelled] == ['T1']
    assert len(model.pending) == 2
    assert not model.feedback(result(command))
    assert model.dispatch() is None
    assert model.stop('再次停止') is None


def test_load_empty_update_and_same_score():
    """空输入允许结束；启动前替换目标；同分按编号稳定排序."""
    model = TargetScheduler()
    assert not model.start()
    model.load(TARGETS)
    tied = deepcopy(TARGETS)
    for target in tied:
        target['score'] = 5
    model.load(tied)
    assert [t['id'] for t in model.pending] == ['T1', 'T2', 'T3']
    model.load([])
    assert model.start()
    assert model.state == 'COMPLETED'
    with pytest.raises(ValueError):
        model.load(TARGETS)


@pytest.mark.parametrize('payload', [
    {}, [None], TARGETS + [TARGETS[0]],
    [dict(TARGETS[0], id='')], [dict(TARGETS[0], id=1)],
    [dict(TARGETS[0], score=True)], [dict(TARGETS[0], x='1')],
    [dict(TARGETS[0], y=float('inf'))],
    [dict(TARGETS[0], score=float('nan'))],
    [dict(TARGETS[0], category=None)],
])
def test_bad_target_batch_is_atomic(payload):
    """非法数据被整体拒绝，不覆盖已收到的合法目标."""
    model = TargetScheduler()
    model.load(TARGETS)
    previous = deepcopy(model.pending)
    with pytest.raises(ValueError):
        model.load(payload)
    assert model.pending == previous
    assert model.loaded


@pytest.mark.parametrize('value', [-1, 1.5, True])
def test_invalid_retry_budget(value):
    """拒绝无效重试预算，避免无限重试或隐式类型转换."""
    with pytest.raises(ValueError):
        TargetScheduler(value)


def test_zero_retry_skips_immediately():
    """重试预算为零时第一次失败就跳过."""
    model = scheduler(0)
    assert model.feedback(result(model.dispatch(), 'failure'))
    assert [t['id'] for t in model.failed] == ['T1']
    assert model.dispatch()['target']['id'] == 'T2'


def test_valid_targets_are_copied():
    """外部修改输入对象不会修改已加载数据."""
    payload = deepcopy(TARGETS)
    targets = validate_targets(payload)
    payload[0]['score'] = 100
    assert targets[0]['score'] == 1
