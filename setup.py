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
        'gradio==5.9.1',
        'grpcio==1.68.0',
        'gym==0.26.2',
        'numpy==2.2.1',  
        'openai==1.59.3',
        'protobuf==3.20.3',
        'pydantic==2.10.4',
        'PyYAML==6.0.2',
        'setuptools==65.7.0',
        'tenacity==9.0.0',
        'tiktoken==0.7.0',
        'torch==2.4.0',  
        'transformers==4.47.1',
        'vllm==0.6.3.post1'
    ],
)