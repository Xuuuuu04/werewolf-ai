"""pytest 公共夹具。

使 `src` 路径下的 werewolf 包可被 tests/ 下测试导入。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)
