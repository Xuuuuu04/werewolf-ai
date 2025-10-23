from setuptools import setup
import os

setup(
    name='werewolf',
    version='0.1',
    description='A project for werewolf game.',
    keywords='werewolf, gym',
    packages=[
        'werewolf',
    ],
    install_requires=[
        'colorama>=0.4.6',      # 控制台彩色输出
        'gymnasium>=0.29.0',     # 替代gym
        'numpy>=1.18.0,<2.0.0',  
        'openai>=1.50.0',
        'pydantic>=2.0.0',
        'PyYAML>=6.0',
        'tenacity>=8.0.0',
        'tiktoken>=0.5.0',
        'torch>=2.0.0',  
        'transformers>=4.30.0'
    ],
)