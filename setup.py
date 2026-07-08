from setuptools import setup, find_packages

setup(
    name='werewolf',
    version='0.1.0',
    description='A LLM-based werewolf game environment.',
    keywords='werewolf, gym',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'gymnasium>=0.29.0',
        'numpy>=1.18.0,<2.0.0',
        'pydantic>=2.0.0',
        'openai>=1.50.0',
        'colorama>=0.4.6',
        'tenacity>=8.0.0',
        'PyYAML>=6.0',
        'tiktoken>=0.5.0',
    ],
    extras_require={
        'visualizer': ['gradio>=4.0.0'],
        'gpu': ['torch>=2.0.0', 'transformers>=4.30.0'],
    },
)
