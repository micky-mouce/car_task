"""生成用于 ROS 流程演示的模拟棋子数据，不执行图像识别."""


def recognize(team='red'):
    """按自定义分值降序排序本队棋子，同分按编号排序."""
    if team not in ('red', 'green'):
        raise ValueError('team must be red or green')
    pieces = [
        {'id': 1, 'color': 'red', 'category': '车', 'score': 9},
        {'id': 2, 'color': 'red', 'category': '马', 'score': 5},
        {'id': 3, 'color': 'red', 'category': '兵', 'score': 1},
        {'id': 4, 'color': 'green', 'category': '炮', 'score': 6},
        {'id': 5, 'color': 'green', 'category': '卒', 'score': 1},
    ]
    queue = sorted(
        (dict(piece) for piece in pieces if piece['color'] == team),
        key=lambda piece: (-piece['score'], piece['id']),
    )
    for rank, piece in enumerate(queue, 1):
        piece['priority'] = rank
    return {'simulated': True, 'team': team, 'pieces': pieces,
            'grab_queue': queue}
