"""
打包脚本 — 用于构建可分发的安装包
"""
from setuptools import setup, find_packages

setup(
    name='majiang-sz',
    version='1.0.0',
    description='四川麻将辅助分析工具',
    packages=find_packages(include=['engine*', 'detection*']),
    package_data={
        'detection': ['*.yaml'],
    },
    # web/ 目录和 app.py 作为数据文件包含
    data_files=[
        ('web', [
            'web/index.html', 'web/style.css', 'web/app.js',
            'web/manifest.json', 'web/sw.js',
            'web/icon-192.png', 'web/icon-512.png',
        ]),
    ],
    install_requires=[
        'flask>=3.0',
        'flask-cors>=4.0',
    ],
    extras_require={
        'detection': ['ultralytics>=8.0', 'opencv-python>=4.8', 'pillow>=10.0'],
        'dev': ['pytest>=8.0'],
    },
    entry_points={
        'console_scripts': ['majiang=app:main'],
    },
    python_requires='>=3.9',
)
