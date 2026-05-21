"""
数据模型模块
定义进程(Process)类及相关数据结构
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProcessStatus(Enum):
    """进程状态枚举"""
    WAITING = "等待"      # 尚未到达
    READY = "就绪"        # 已到达，在就绪队列
    RUNNING = "运行"      # 正在CPU上执行
    FINISHED = "完成"      # 执行完毕


@dataclass
class Process:
    """进程数据类"""
    name: str                          # 进程名
    arrival_time: int                  # 到达时间
    burst_time: int                    # 服务时间(总需要CPU时间)
    remaining_time: int = 0            # 剩余服务时间
    finish_time: Optional[int] = None  # 完成时间
    turnaround_time: Optional[float] = None       # 周转时间
    weighted_turnaround_time: Optional[float] = None  # 带权周转时间
    status: ProcessStatus = ProcessStatus.WAITING  # 当前状态
    start_time: Optional[int] = None   # 首次开始运行时间
    color: str = ""                    # 甘特图显示颜色

    def __post_init__(self):
        """初始化后自动设置剩余时间"""
        if self.remaining_time == 0:
            self.remaining_time = self.burst_time

    def reset(self):
        """重置进程状态（用于重新模拟）"""
        self.remaining_time = self.burst_time
        self.finish_time = None
        self.turnaround_time = None
        self.weighted_turnaround_time = None
        self.status = ProcessStatus.WAITING
        self.start_time = None

    def copy(self):
        """创建进程的深拷贝"""
        p = Process(
            name=self.name,
            arrival_time=self.arrival_time,
            burst_time=self.burst_time,
            color=self.color
        )
        return p


@dataclass
class ScheduleEvent:
    """调度事件记录（用于甘特图和日志）"""
    time: int              # 事件发生时间
    process_name: str      # 涉及的进程名
    event_type: str        # 事件类型: arrive/start/preempt/finish/quantum_end
    detail: str = ""       # 事件描述
    color: str = ""        # 进程颜色


@dataclass
class GanttEntry:
    """甘特图条目"""
    process_name: str      # 进程名
    start_time: int        # 开始时间
    end_time: int          # 结束时间
    color: str = ""        # 颜色


@dataclass
class ScheduleResult:
    """调度结果"""
    processes: list                    # 进程列表（含计算后的指标）
    gantt: list = field(default_factory=list)        # 甘特图数据
    events: list = field(default_factory=list)        # 事件日志
    total_time: int = 0               # 总运行时间
    avg_turnaround: float = 0.0       # 平均周转时间
    avg_weighted_turnaround: float = 0.0  # 平均带权周转时间
    cpu_utilization: float = 0.0      # CPU利用率
    throughput: float = 0.0           # 吞吐量
