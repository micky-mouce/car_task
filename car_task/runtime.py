"""ROS 节点的通用运行与清理逻辑."""

import rclpy


def run_node(node_type, args=None):
    """初始化、运行并安全销毁指定类型的节点."""
    rclpy.init(args=args)
    node = None

    try:
        node = node_type()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
