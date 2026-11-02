"""第四次任务共用的话题、JSON 发布与持久状态 QoS."""

import json

from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

TARGETS = 'target_list'
COMMAND = 'target_command'
RESULT = 'target_result'
PROGRESS = 'target_progress'
STATUS = 'target_status'
REPORT = 'target_report'
STOP = 'stop_command'


def retained_qos():
    """保留最后一条目标输入、状态或报告，供晚加入的节点读取."""
    return QoSProfile(
        depth=1, reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )


def publish_json(publisher, payload):
    """以标准 String 消息发布 UTF-8 JSON."""
    publisher.publish(String(data=json.dumps(payload, ensure_ascii=False)))
