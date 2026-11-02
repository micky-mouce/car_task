"""通过真实 ROS2 节点通信验证第四次任务，并可保存演示事件流."""

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from car_task import target_transport as wire
import rclpy
from std_msgs.msg import Bool, String


def run_scenario(name, arguments, output, duration, domain_id, inject=True):
    """隔离 ROS 域启动实际 launch，收集并核验执行、结果及终态."""
    os.environ['ROS_DOMAIN_ID'] = str(domain_id)
    rclpy.init()
    node = rclpy.create_node('fourth_task_verifier')
    events, commands, reports, statuses, results, progress = [], [], [], [], [], []
    started_at = time.monotonic()

    def receive(topic, bucket):
        def callback(message):
            payload = json.loads(message.data)
            bucket.append(payload)
            events.append({'time': time.monotonic() - started_at,
                           'topic': topic, 'data': payload})
        return callback

    subscriptions = [
        node.create_subscription(
            String, topic, receive(topic, bucket), qos)
        for topic, bucket, qos in [
            (wire.STATUS, statuses, wire.retained_qos()),
            (wire.REPORT, reports, wire.retained_qos()),
            (wire.COMMAND, commands, 10), (wire.RESULT, results, 10),
            (wire.PROGRESS, progress, 10),
        ]
    ]
    stop_pub = node.create_publisher(Bool, wire.STOP, 10)
    start_pub = node.create_publisher(Bool, 'start_command', 10)
    fake_pub = node.create_publisher(String, wire.RESULT, 10)
    command_pub = node.create_publisher(String, wire.COMMAND, 10)
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / f'{name}.log'
    log_file = log_path.open('w', encoding='utf-8')
    process = subprocess.Popen(
        ['ros2', 'launch', 'car_task', 'fourth_task.launch.py',
         'auto_start:=false', f'execution_seconds:={duration}', *arguments],
        stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True,
    )
    injected = False
    stopped = False
    started = False
    try:
        deadline = time.monotonic() + 35 + duration * 6
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if process.poll() is not None:
                raise AssertionError(f'launch 提前退出，详见 {log_path}')
            connected = (all(sub.get_publisher_count() > 0
                             for sub in subscriptions)
                         and start_pub.get_subscription_count() > 0)
            if (not started and connected and statuses
                    and statuses[-1]['loaded']):
                start_pub.publish(Bool(data=True))
                started = True
                events.append({'time': time.monotonic() - started_at,
                               'topic': 'start_command', 'data': True})
            if inject and name == 'retry' and commands and not injected:
                command = commands[0]
                # 有效指令重复投递；错误编号和错误格式反馈均不应推进队列。
                wire.publish_json(command_pub, command)
                wire.publish_json(fake_pub, {
                    'target_id': 'T999', 'command_id': command['command_id'],
                    'status': 'success',
                })
                wire.publish_json(fake_pub, [])
                injected = True
            if name == 'stop' and progress and not stopped:
                stop_pub.publish(Bool(data=True))
                stopped = True
                events.append({'time': time.monotonic() - started_at,
                               'topic': wire.STOP, 'data': True})
            if reports:
                # 终态后继续观察，检查是否仍发出执行指令或重复报告。
                end = time.monotonic() + 1.0
                while time.monotonic() < end:
                    rclpy.spin_once(node, timeout_sec=0.05)
                break
        assert len(reports) == 1, f'{name}: 未得到唯一终态报告，见 {log_path}'
        report = reports[0]
        executions = [c for c in commands if c['operation'] == 'execute']
        # retry 场景注入了一条完全相同的指令，执行器应去重。
        unique_commands = {c['command_id']: c for c in executions}
        ids = [c['target']['id'] for c in unique_commands.values()]
        if name in ('retry', 'skip'):
            assert ids == ['T1', 'T4', 'T2', 'T2', 'T3'], ids
            assert report['state'] == 'COMPLETED', report
            expected = ['T1', 'T4', 'T2', 'T3'] if name == 'retry' else [
                'T1', 'T4', 'T3']
            assert [t['id'] for t in report['completed']] == expected, report
            assert [t['id'] for t in report['failed']] == (
                [] if name == 'retry' else ['T2']), report
            assert len(report['history']) == 5, report
            assert not report['pending'] and not report['cancelled'], report
        else:
            assert report['state'] == 'STOPPED', report
            assert ids == ['T1'], ids
            assert len(report['cancelled']) == 1, report
            assert len(report['pending']) == 3, report
            assert not report['completed'], report
            assert any(c['operation'] == 'cancel' for c in commands), commands
            assert ('超时' if name == 'timeout' else '停止指令') in report['reason']
        assert report['current'] is None
        # 每条已完成指令恰好一个反馈；伪造反馈单独排除。
        actual_results = [r for r in results if isinstance(r, dict)
                          and r.get('target_id') != 'T999']
        feedback_ids = [r['command_id'] for r in actual_results]
        assert len(feedback_ids) == len(set(feedback_ids)), actual_results
        if name in ('timeout', 'stop'):
            assert not actual_results, actual_results
        # 每次下发下一条指令前，前一条的反馈必须已被调度器记入历史。
        for status in statuses:
            current = status['current']
            if current:
                index = list(unique_commands).index(current['command_id'])
                assert len(status['history']) == index, status
        (output / f'{name}.jsonl').write_text(
            ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in events),
            encoding='utf-8',
        )
        (output / f'{name}_report.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        print(f'PASS {name}: state={report["state"]}, commands={ids}')
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
        log_file.close()
        for subscription in subscriptions:
            node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()


def main():
    """运行所有异常场景，或以正常时长录制默认演示事件流."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('artifacts/fourth'))
    parser.add_argument('--demo', action='store_true', help='以默认 3 秒动作录制重试流程')
    parser.add_argument('--domain-id', type=int, default=121)
    args = parser.parse_args()
    scenarios = {
        'retry': [],
        'skip': ['fail_always_ids:=T2'],
        'timeout': ['silent_ids:=T1', 'result_timeout:=1.2'],
        'stop': [],
    }
    if args.demo:
        scenarios = {'retry': []}
    for index, (name, arguments) in enumerate(scenarios.items()):
        run_scenario(name, arguments, args.output,
                     3.0 if args.demo else 0.5, args.domain_id + index,
                     inject=not args.demo)


if __name__ == '__main__':
    main()
