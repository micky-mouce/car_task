"""在已加载安装环境的 ROS2 终端执行，验证真实话题通信."""

import json
import os
import signal
import subprocess
import time

import rclpy
from std_msgs.msg import Bool, Int32, String


def main():
    rclpy.init()
    node = rclpy.create_node('third_task_verifier')
    states, progress, reports = [], [], []
    subscriptions = [
        node.create_subscription(String, '/task_state',
                                 lambda msg: states.append(msg.data), 10),
        node.create_subscription(Int32, '/motion_progress',
                                 lambda msg: progress.append(msg.data), 10),
        node.create_subscription(String, '/task_report',
                                 lambda msg: reports.append(msg.data), 10),
    ]
    start_publisher = node.create_publisher(Bool, '/start_command', 10)
    process = subprocess.Popen(
        ['ros2', 'launch', 'car_task', 'car_task.launch.py',
         'auto_start:=false'],
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            connected = all(
                node.count_publishers(topic) > 0
                for topic in ('/task_state', '/motion_progress', '/task_report')
            )
            if (connected and 'IDLE' in states
                    and start_publisher.get_subscription_count() > 0):
                break
        else:
            raise AssertionError('等待任务节点连接超时')
        start_publisher.publish(Bool(data=True))
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if 'SAFE_STOP' in states and reports:
                break
        expected = ['IDLE', 'RUNNING', 'SCANNING', 'REPORTING', 'SAFE_STOP']
        unique = []
        for state in states:
            if not unique or unique[-1] != state:
                unique.append(state)
        assert unique == expected, unique
        assert progress == [0, 20, 40, 60, 80, 100], progress
        assert len(reports) == 1, reports
        payload = json.loads(reports[0].split('；', 1)[1])
        assert [p['id'] for p in payload['grab_queue']] == [1, 2, 3]
        print('PASS: ROS2 状态、行驶进度、棋子排序及最终停车均已验证。')
    finally:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        for subscription in subscriptions:
            node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
