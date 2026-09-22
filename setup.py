from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'car_task'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        (
            'share/' + package_name,
            ['package.xml']
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Micky_Mouce',
    maintainer_email='hellsee005@gmail.com',
    description=(
        'ROS 2 intelligent car task flow, motion, and vision '
        'collaboration simulator'
    ),
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'simulate_start = car_task.simulate_start:main',
            'task_state = car_task.task_state:main',
            'motion_simulator = car_task.motion_simulator:main',
            'vision_simulator = car_task.vision_simulator:main',
            'display_node = car_task.display_node:main',
        ],
    },
)
