"""第四次任务的目标校验、串行调度与结果管理，不依赖 ROS."""

import math
import uuid


def validate_targets(payload):
    """完整校验一批目标，拒绝重复编号和非有限数值."""
    if not isinstance(payload, list):
        raise ValueError('目标输入必须为 JSON 数组')
    targets, ids = [], set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError('每个目标必须为对象')
        target_id = item.get('id')
        if not isinstance(target_id, str) or not target_id.strip():
            raise ValueError('id 必须为非空字符串')
        if target_id in ids:
            raise ValueError(f'重复目标编号：{target_id}')
        if not isinstance(item.get('category'), str) or not item['category']:
            raise ValueError(f'{target_id} 缺少类别')
        target = {'id': target_id, 'category': item['category']}
        for key in ('score', 'x', 'y'):
            value = item.get(key)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value)):
                raise ValueError(f'{target_id}.{key} 必须为有限数值')
            target[key] = value
        targets.append(target)
        ids.add(target_id)
    return targets


class TargetScheduler:
    """分值降序、同分编号升序；一次只允许一个待反馈指令."""

    def __init__(self, max_retries=1):
        if isinstance(max_retries, bool) or not isinstance(max_retries, int):
            raise ValueError('max_retries 必须为整数')
        if max_retries < 0:
            raise ValueError('max_retries 不能为负数')
        self.max_retries = max_retries
        self.run_id = uuid.uuid4().hex
        self.state = 'IDLE'
        self.loaded = False
        self.pending = []
        self.active = None
        self.completed = []
        self.failed = []
        self.cancelled = []
        self.history = []
        self.attempts = {}
        self.reason = '等待目标输入和启动指令'

    def load(self, payload):
        """启动前以整批替换方式更新目标，校验失败时保留原数据."""
        if self.state != 'IDLE':
            raise ValueError('运行中或结束后不接受目标更新')
        targets = validate_targets(payload)
        self.pending = sorted(targets, key=lambda t: (-t['score'], t['id']))
        self.loaded = True

    def start(self):
        """目标已加载后接受一次启动，空列表直接完成."""
        if self.state != 'IDLE' or not self.loaded:
            return False
        self.state = 'RUNNING' if self.pending else 'COMPLETED'
        self.reason = '按分值降序执行；失败有限重试' if self.pending else '无待执行目标'
        return True

    def dispatch(self):
        """取出一个目标，生成本轮唯一指令编号；有在途目标时拒绝下发."""
        if self.state != 'RUNNING' or self.active or not self.pending:
            return None
        target = self.pending.pop(0)
        attempt = self.attempts.get(target['id'], 0) + 1
        self.attempts[target['id']] = attempt
        self.active = {
            'operation': 'execute', 'target': target, 'attempt': attempt,
            'command_id': f'{self.run_id}:{target["id"]}:{attempt}',
        }
        return dict(self.active)

    def feedback(self, payload):
        """只接受当前指令的成功或失败，忽略重复、错号与迟到反馈."""
        if not isinstance(payload, dict) or not self.active:
            return False
        active = self.active
        if (payload.get('command_id') != active['command_id']
                or payload.get('target_id') != active['target']['id']
                or payload.get('status') not in ('success', 'failure')):
            return False
        target = active['target']
        self.history.append({
            'target_id': target['id'], 'command_id': active['command_id'],
            'attempt': active['attempt'], 'status': payload['status'],
            'detail': str(payload.get('detail', '')),
        })
        self.active = None
        if payload['status'] == 'success':
            self.completed.append(dict(target))
            self.reason = f'{target["id"]} 成功，移除已完成目标'
        elif active['attempt'] <= self.max_retries:
            self.pending.insert(0, target)
            self.reason = f'{target["id"]} 失败，准备第 {active["attempt"]} 次重试'
        else:
            self.failed.append(dict(target))
            self.reason = f'{target["id"]} 重试用尽，跳过并继续'
        if not self.pending:
            self.state = 'COMPLETED'
            self.reason += '；队列处理结束，进入等待'
        return True

    def stop(self, reason):
        """停止整轮调度并返回需取消的指令，超时后也不再下发目标."""
        if self.state in ('COMPLETED', 'STOPPED'):
            return None
        active = self.active
        if active:
            self.cancelled.append(dict(active['target']))
            self.history.append({
                'target_id': active['target']['id'],
                'command_id': active['command_id'],
                'attempt': active['attempt'], 'status': 'cancelled',
                'detail': reason,
            })
        self.active = None
        self.state = 'STOPPED'
        self.reason = reason
        return active

    def snapshot(self):
        """生成可 JSON 序列化的完整状态与结果快照."""
        return {
            'state': self.state, 'loaded': self.loaded,
            'rule': 'score_desc_id_asc', 'current': self.active,
            'pending': self.pending, 'completed': self.completed,
            'failed': self.failed, 'cancelled': self.cancelled,
            'history': self.history, 'reason': self.reason,
        }
