"""将真实 ROS2 话题事件流渲染为带中文说明的演示视频."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, FPS = 1280, 720, 10
BG = '#101827'
CARD = '#1c2940'
TEXT = '#eaf1ff'
MUTED = '#a6b6d1'
ACCENT = '#52d9bf'
YELLOW = '#ffcc7a'


class DemoRenderer:
    """用实际事件更新状态面板，不生成虚构执行结果."""

    def __init__(self, font_path):
        self.fonts = {
            size: ImageFont.truetype(str(font_path), size)
            for size in (18, 20, 22, 24, 28, 36, 42)
        }
        self.status = None
        self.progress = {}

    def base(self, label):
        """创建固定大小的深色演示画布."""
        frame = Image.new('RGB', (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(frame)
        self.text(draw, (48, 28), 'ROS2 第四次任务 · 多目标任务执行仿真', 36)
        self.text(draw, (50, 83), label, 20, MUTED)
        draw.line((48, 122, 1232, 122), fill='#32435e', width=2)
        self.text(draw, (48, 680),
                  'Ubuntu 24.04  /  ROS2 Jazzy  /  Python  /  软件模拟', 18, MUTED)
        return frame, draw

    def text(self, draw, xy, value, size=24, fill=TEXT):
        """使用中文字体绘制文字."""
        draw.text(xy, str(value), font=self.fonts[size], fill=fill)

    def explanation(self, ending=False):
        """用文字说明项目目标、方法、平台及实际完成结果."""
        frame, draw = self.base('真实 ROS2 话题记录可视化回放（非桌面录屏）')
        title = '演示结果' if ending else '项目目标与实现思路'
        self.text(draw, (60, 155), title, 42, ACCENT)
        if ending:
            lines = [
                '完成 4 个目标：T1 → T4 → T2 → T3。',
                'T2 首次失败，重试一次成功；共执行 5 次尝试。',
                '成功目标从队列移除，重复反馈不会触发再次执行。',
                '最终 COMPLETED，当前目标为空、待执行队列为空。',
                '另已验证：持续失败跳过、反馈超时停止、手动停止。',
                '全部流程通过 ROS2 节点话题通信完成，无需真实硬件。',
            ]
        else:
            lines = [
                '目标：接收多个目标，依次选择、执行、反馈并更新列表。',
                '节点：目标输入 → 任务管理 ⇄ 执行模拟 → 集中显示。',
                '规则：分值高者优先，同分按编号；一次只执行一个。',
                '反馈：成功后移除；失败最多重试一次，仍失败则跳过。',
                '异常：停止或超时取消当前动作，终止整轮调度。',
                '下页将按实际时间回放 4 个目标的完整执行过程。',
            ]
        for index, line in enumerate(lines):
            self.text(draw, (65, 250 + index * 59), line, 28)
        return frame

    def receive(self, event):
        """消费已记录的状态、进度或最终报告事件."""
        if event['topic'] in ('target_status', 'target_report'):
            self.status = event['data']
        elif event['topic'] == 'target_progress':
            data = event['data']
            self.progress[data['command_id']] = data

    def dashboard(self, elapsed):
        """展示当前目标、按优先级排列的队列和逐次反馈结果."""
        frame, draw = self.base(
            f'实际话题时间 +{elapsed:04.1f}s  |  分值降序，同分按编号升序  |  动作 3 秒/次')
        data = self.status
        if not data:
            self.text(draw, (60, 190), '正在启动节点，等待目标输入……', 36, ACCENT)
            return frame
        for box in ((48, 145, 615, 410), (638, 145, 1232, 410),
                    (48, 430, 1232, 655)):
            draw.rounded_rectangle(box, radius=16, fill=CARD)
        self.text(draw, (72, 161), f'状态：{data["state"]}', 28, ACCENT)
        current = data['current']
        if current:
            target = current['target']
            self.text(draw, (72, 213),
                      f'{target["id"]}  {target["category"]}  /  {target["score"]} 分', 36)
            self.text(draw, (72, 268),
                      f'位置 ({target["x"]}, {target["y"]}) m   第 {current["attempt"]} 次执行',
                      22, MUTED)
            progress = self.progress.get(current['command_id'], {})
            percent = progress.get('progress', 0)
            self.text(draw, (72, 310),
                      f'{progress.get("phase", "准备")}   {percent}%', 24, ACCENT)
            draw.rounded_rectangle((72, 365, 585, 381), radius=8, fill='#32435e')
            if percent:
                draw.rounded_rectangle(
                    (72, 365, 72 + int(513 * percent / 100), 381),
                    radius=8, fill=ACCENT)
        else:
            self.text(draw, (72, 224), '当前目标：无', 36)
            label = '任务结束，保持等待' if data['state'] == 'COMPLETED' else '等待开始'
            self.text(draw, (72, 300), label, 24, MUTED)
        self.text(draw, (662, 161), '待执行队列（按优先级）', 28)
        for index, target in enumerate(data['pending'][:4]):
            self.text(draw, (670, 215 + index * 43),
                      f'{index + 1}.   {target["id"]}   {target["category"]}'
                      f'          {target["score"]} 分', 24, MUTED)
        if not data['pending']:
            self.text(draw, (670, 232), '空队列', 28, ACCENT)
        self.text(draw, (72, 445),
                  f'逐次反馈     成功 {len(data["completed"])} 个  /  '
                  f'跳过 {len(data["failed"])} 个', 24)
        if not data['history']:
            self.text(draw, (72, 498), '尚无执行结果，等待反馈后才会安排下一个目标。', 22, MUTED)
        for index, row in enumerate(data['history'][-5:]):
            success = row['status'] == 'success'
            label = '成功，移出队列' if success else '失败，准备重试'
            self.text(draw, (78, 490 + index * 30),
                      f'{row["target_id"]}   第 {row["attempt"]} 次执行    {label}',
                      20, ACCENT if success else YELLOW)
        return frame


def main():
    """读取真实事件 JSONL，输出 MP4 和预览图."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--font', type=Path, default=Path(
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'))
    args = parser.parse_args()
    events = [json.loads(line) for line in args.trace.read_text('utf-8').splitlines()]
    events.sort(key=lambda item: item['time'])
    reports = [event['data'] for event in events if event['topic'] == 'target_report']
    if (not reports or reports[-1]['state'] != 'COMPLETED'
            or [t['id'] for t in reports[-1]['completed']]
            != ['T1', 'T4', 'T2', 'T3'] or len(reports[-1]['history']) != 5):
        raise ValueError('此模板只用于本工程默认四目标、一次重试成功的真实演示记录')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    renderer = DemoRenderer(args.font)
    writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*'mp4v'),
                             FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError('OpenCV 无法打开 MP4 编码器')

    def write(frame):
        writer.write(cv2.cvtColor(np.asarray(frame), cv2.COLOR_RGB2BGR))

    try:
        intro = renderer.explanation()
        for _ in range(8 * FPS):
            write(intro)
        index = 0
        for tick in range(int((events[-1]['time'] + 2) * FPS) + 1):
            elapsed = tick / FPS
            while index < len(events) and events[index]['time'] <= elapsed:
                renderer.receive(events[index])
                index += 1
            frame = renderer.dashboard(elapsed)
            if renderer.status and renderer.status['current']:
                preview = args.output.with_suffix('.png')
                if not preview.exists():
                    frame.save(preview)
            write(frame)
        ending = renderer.explanation(ending=True)
        for _ in range(8 * FPS):
            write(ending)
    finally:
        writer.release()
    capture = cv2.VideoCapture(str(args.output))
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    print(f'已生成 {args.output}，{WIDTH}x{HEIGHT}，{count / FPS:.1f} 秒，{count} 帧')


if __name__ == '__main__':
    main()
