# ROS 2 智能车任务流程仿真

## 项目简介

本项目用多个 ROS 2 节点模拟智能车接收任务、行驶到棋子区域、
识别象棋棋子、发布任务报告并安全停车的完整过程。

```text
IDLE -> RUNNING -> SCANNING -> REPORTING -> SAFE_STOP
```

## 节点

- `simulate_start`：启动 2 秒后模拟按键，发布一次启动指令。
- `task_state`：管理整体任务状态，生成最终任务报告。
- `motion_simulator`：模拟小车行驶进度和到达事件。
- `vision_simulator`：模拟棋子颜色、类型和优先目标识别。
- `display_node`：在一个终端中集中显示状态、进度和结果。

## 话题

| 话题 | 类型 | 用途 |
| --- | --- | --- |
| `/start_command` | `std_msgs/msg/Bool` | 模拟启动按键 |
| `/task_state` | `std_msgs/msg/String` | 发布当前任务状态 |
| `/task_event` | `std_msgs/msg/String` | 发布到达、识别完成等事件 |
| `/motion_progress` | `std_msgs/msg/Int32` | 发布行驶进度 |
| `/vision_result` | `std_msgs/msg/String` | 发布模拟棋子识别结果 |
| `/task_report` | `std_msgs/msg/String` | 发布最终任务报告 |

## 系统要求

- Ubuntu 24.04
- ROS 2 Jazzy
- Python 3
- `rclpy`、`std_msgs` 和 `colcon`

## 编译与运行

在 ROS 2 工作空间根目录执行：

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select car_task
source install/setup.bash
ros2 launch car_task car_task.launch.py
```

程序会自动完成整个流程，不需要手动发布话题。正常结果为：

```text
2 秒后收到启动指令
小车行驶进度：0% -> 20% -> ... -> 100%
小车到达棋子区域
完成棋子识别
发布任务报告
进入 SAFE_STOP 状态
```

## 调试与演示

查看节点和话题：

```bash
ros2 node list
ros2 topic list
```

单独查看状态或报告：

```bash
ros2 topic echo /task_state
ros2 topic echo /task_report
```

图形化查看节点通信关系：

```bash
rqt_graph
```

在运行终端按 `Ctrl+C` 停止全部节点。

## 许可证

Apache-2.0
