# ROS 2 智能车任务状态机

## 项目简介

本项目用于演示 ROS 2 节点通信和智能车任务状态切换，实现以下流程：

```text
IDLE -> RUNNING -> SCAN -> REPORT -> SAFE_STOP
```

项目包含两个节点：

- `simulate_start`：模拟启动按钮，运行 2 秒后发送一次启动指令；
- `task_state`：接收启动指令和任务事件，并发布当前任务状态。

使用的话题如下：

| 话题 | 类型 | 用途 |
| --- | --- | --- |
| `/start_command` | `std_msgs/msg/Bool` | 发送启动指令 |
| `/task_event` | `std_msgs/msg/String` | 发送状态切换事件 |
| `/task_state` | `std_msgs/msg/String` | 发布当前状态 |

## 系统要求

- Ubuntu 24.04；
- ROS 2 Jazzy；
- Python 3；
- `rclpy`、`std_msgs` 和 `colcon`。

## 编译

进入包含 `src/car_task` 的 ROS 2 工作空间根目录，例如：

```bash
cd ros2_ws
```

加载 ROS 2 并编译：

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select car_task
source install/setup.bash
```

如果修改了源代码，需要重新执行以上编译命令。

## 运行

每打开一个新终端，都需要先进入工作空间根目录并加载环境：

```bash
cd ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

### 1. 启动状态节点

在终端 1 中运行：

```bash
ros2 run car_task task_state
```

初始状态为 `IDLE`。

### 2. 查看状态

在终端 2 中运行：

```bash
ros2 topic echo /task_state
```

### 3. 模拟启动

在终端 3 中运行：

```bash
ros2 run car_task simulate_start
```

2 秒后，状态将从 `IDLE` 变为 `RUNNING`。启动指令发送完成后，可以在终端 3 按 `Ctrl+C` 关闭模拟启动节点；这不会影响状态节点。

### 4. 切换后续状态

继续在终端 3 中依次执行：

```bash
ros2 topic pub --once /task_event std_msgs/msg/String "{data: scan}"
ros2 topic pub --once /task_event std_msgs/msg/String "{data: scan_done}"
ros2 topic pub --once /task_event std_msgs/msg/String "{data: report_done}"
```

状态应依次变化为：

```text
IDLE -> RUNNING -> SCAN -> REPORT -> SAFE_STOP
```

## 图形化查看通信关系

节点运行时，可以另开终端执行：

```bash
source /opt/ros/jazzy/setup.bash
rqt_graph
```

该工具可以显示节点与话题之间的通信关系。

## 停止程序

在运行程序的终端中按 `Ctrl+C`，即可停止该终端中的节点。

## 许可证

Apache-2.0
