"""
操作系统处理机调度模拟系统
主入口文件

功能：
- FCFS（先来先服务）调度算法
- 抢占式 SJF（SRTF）调度算法
- RR（时间片轮转）调度算法
"""

import sys
import os

# 确保当前目录在搜索路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# PyInstaller 打包后修正工作目录
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from gui import SchedulerApp


def main():
    """程序主入口"""
    app = SchedulerApp()
    app.run()


if __name__ == "__main__":
    main()
