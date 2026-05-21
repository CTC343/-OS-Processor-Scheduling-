"""
操作系统处理机调度模拟系统
单文件合并版 - 用于 PyInstaller 打包

功能：
- FCFS（先来先服务）调度算法
- 抢占式 SJF（SRTF）调度算法
- RR（时间片轮转）调度算法
- 甘特图可视化、动画演示、性能指标统计

Python 3.8+
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import sys
import os
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Optional

# ============================================================
# 第一部分：数据模型
# ============================================================

class ProcessStatus(Enum):
    """进程状态枚举"""
    WAITING = "等待"
    READY = "就绪"
    RUNNING = "运行"
    FINISHED = "完成"


@dataclass
class Process:
    """进程数据类"""
    name: str
    arrival_time: int
    burst_time: int
    remaining_time: int = 0
    finish_time: Optional[int] = None
    turnaround_time: Optional[float] = None
    weighted_turnaround_time: Optional[float] = None
    status: ProcessStatus = ProcessStatus.WAITING
    start_time: Optional[int] = None
    color: str = ""

    def __post_init__(self):
        if self.remaining_time == 0:
            self.remaining_time = self.burst_time

    def reset(self):
        self.remaining_time = self.burst_time
        self.finish_time = None
        self.turnaround_time = None
        self.weighted_turnaround_time = None
        self.status = ProcessStatus.WAITING
        self.start_time = None

    def copy(self):
        return Process(name=self.name, arrival_time=self.arrival_time,
                       burst_time=self.burst_time, color=self.color)


@dataclass
class ScheduleEvent:
    time: int
    process_name: str
    event_type: str
    detail: str = ""
    color: str = ""


@dataclass
class GanttEntry:
    process_name: str
    start_time: int
    end_time: int
    color: str = ""


@dataclass
class ScheduleResult:
    processes: list
    gantt: list = field(default_factory=list)
    events: list = field(default_factory=list)
    total_time: int = 0
    avg_turnaround: float = 0.0
    avg_weighted_turnaround: float = 0.0
    cpu_utilization: float = 0.0
    throughput: float = 0.0


# ============================================================
# 第二部分：调度算法
# ============================================================

PROCESS_COLORS = [
    '#4A90D9', '#E85D75', '#50C878', '#F5A623', '#9B59B6',
    '#1ABC9C', '#E74C3C', '#3498DB', '#E67E22', '#2ECC71',
]


class Scheduler(ABC):
    """调度器基类"""

    def __init__(self, processes: List[Process]):
        self.processes = [p.copy() for p in processes]
        self.events: List[ScheduleEvent] = []
        self.gantt: List[GanttEntry] = []
        self.current_time = 0
        for i, p in enumerate(self.processes):
            p.color = PROCESS_COLORS[i % len(PROCESS_COLORS)]

    @abstractmethod
    def run(self) -> ScheduleResult:
        pass

    def _check_arrivals(self, time: int):
        for p in self.processes:
            if p.arrival_time == time and p.status == ProcessStatus.WAITING:
                p.status = ProcessStatus.READY
                self.events.append(ScheduleEvent(time=time, process_name=p.name,
                                                  event_type="arrive", detail=f"{p.name} 到达"))

    def _finish_process(self, process: Process, time: int):
        process.status = ProcessStatus.FINISHED
        process.finish_time = time
        process.turnaround_time = process.finish_time - process.arrival_time
        if process.burst_time > 0:
            process.weighted_turnaround_time = process.turnaround_time / process.burst_time
        self.events.append(ScheduleEvent(
            time=time, process_name=process.name, event_type="finish",
            detail=f"{process.name} 完成 (周转={process.turnaround_time}, 带权={process.weighted_turnaround_time:.2f})",
            color=process.color))

    def _build_result(self) -> ScheduleResult:
        if not self.processes:
            return ScheduleResult(processes=[])
        total_time = max(p.finish_time for p in self.processes if p.finish_time is not None)
        cpu_busy = sum(p.burst_time for p in self.processes)
        avg_tt = sum(p.turnaround_time for p in self.processes) / len(self.processes)
        avg_wtt = sum(p.weighted_turnaround_time for p in self.processes) / len(self.processes)
        return ScheduleResult(
            processes=self.processes, gantt=self.gantt, events=self.events,
            total_time=total_time, avg_turnaround=avg_tt, avg_weighted_turnaround=avg_wtt,
            cpu_utilization=cpu_busy / total_time * 100 if total_time > 0 else 0,
            throughput=len(self.processes) / total_time if total_time > 0 else 0)


class FCFSScheduler(Scheduler):
    def run(self) -> ScheduleResult:
        self.processes.sort(key=lambda p: p.arrival_time)
        current_time = 0
        for process in self.processes:
            if current_time < process.arrival_time:
                current_time = process.arrival_time
            self._check_arrivals(process.arrival_time)
            process.status = ProcessStatus.RUNNING
            process.start_time = current_time
            self.events.append(ScheduleEvent(time=current_time, process_name=process.name,
                                              event_type="start", detail=f"{process.name} 开始运行",
                                              color=process.color))
            end_time = current_time + process.burst_time
            self.gantt.append(GanttEntry(process_name=process.name,
                                          start_time=current_time, end_time=end_time, color=process.color))
            current_time = end_time
            process.remaining_time = 0
            self._finish_process(process, current_time)
            for p in self.processes:
                if p.status == ProcessStatus.WAITING and p.arrival_time <= current_time:
                    p.status = ProcessStatus.READY
                    self.events.append(ScheduleEvent(time=p.arrival_time, process_name=p.name,
                                                      event_type="arrive", detail=f"{p.name} 到达"))
        return self._build_result()


class SJFScheduler(Scheduler):
    def run(self) -> ScheduleResult:
        current_time = 0
        max_time = sum(p.burst_time for p in self.processes) + max(p.arrival_time for p in self.processes) + 1
        current_process = None
        gantt_start = -1
        while current_time <= max_time:
            self._check_arrivals(current_time)
            ready = [p for p in self.processes
                     if p.status in (ProcessStatus.READY, ProcessStatus.RUNNING) and p.remaining_time > 0]
            if not ready:
                if all(p.status == ProcessStatus.FINISHED for p in self.processes):
                    break
                current_time += 1
                continue
            ready.sort(key=lambda p: (p.remaining_time, p.arrival_time))
            selected = ready[0]
            if current_process != selected:
                if current_process is not None and gantt_start >= 0:
                    self.gantt.append(GanttEntry(process_name=current_process.name,
                                                  start_time=gantt_start, end_time=current_time,
                                                  color=current_process.color))
                    current_process.status = ProcessStatus.READY
                current_process = selected
                current_process.status = ProcessStatus.RUNNING
                if current_process.start_time is None:
                    current_process.start_time = current_time
                gantt_start = current_time
                self.events.append(ScheduleEvent(time=current_time, process_name=current_process.name,
                                                  event_type="start",
                                                  detail=f"{current_process.name} 开始运行 (剩余={current_process.remaining_time})",
                                                  color=current_process.color))
            current_process.remaining_time -= 1
            current_time += 1
            if current_process.remaining_time == 0:
                self.gantt.append(GanttEntry(process_name=current_process.name,
                                              start_time=gantt_start, end_time=current_time,
                                              color=current_process.color))
                self._finish_process(current_process, current_time)
                current_process = None
                gantt_start = -1
        return self._build_result()


class RRScheduler(Scheduler):
    def __init__(self, processes: List[Process], time_quantum: int = 1):
        super().__init__(processes)
        self.time_quantum = time_quantum

    def run(self) -> ScheduleResult:
        ready_queue: List[Process] = []
        current_time = 0
        max_time = sum(p.burst_time for p in self.processes) + max(p.arrival_time for p in self.processes) + 1
        current_process = None
        quantum_used = 0
        gantt_start = -1
        while current_time <= max_time:
            self._check_arrivals(current_time)
            for p in self.processes:
                if p.arrival_time == current_time and p.status == ProcessStatus.READY:
                    if p not in ready_queue:
                        ready_queue.append(p)
            if current_process is not None and quantum_used >= self.time_quantum:
                self.gantt.append(GanttEntry(process_name=current_process.name,
                                              start_time=gantt_start, end_time=current_time,
                                              color=current_process.color))
                if current_process.remaining_time > 0:
                    current_process.status = ProcessStatus.READY
                    ready_queue.append(current_process)
                    self.events.append(ScheduleEvent(time=current_time, process_name=current_process.name,
                                                      event_type="quantum_end",
                                                      detail=f"{current_process.name} 时间片用完，回到就绪队列 (剩余={current_process.remaining_time})"))
                current_process = None
                quantum_used = 0
            if current_process is None:
                if ready_queue:
                    current_process = ready_queue.pop(0)
                    current_process.status = ProcessStatus.RUNNING
                    if current_process.start_time is None:
                        current_process.start_time = current_time
                    gantt_start = current_time
                    quantum_used = 0
                    self.events.append(ScheduleEvent(time=current_time, process_name=current_process.name,
                                                      event_type="start",
                                                      detail=f"{current_process.name} 开始运行 (剩余={current_process.remaining_time})",
                                                      color=current_process.color))
                else:
                    if all(p.status == ProcessStatus.FINISHED for p in self.processes):
                        break
                    current_time += 1
                    continue
            current_process.remaining_time -= 1
            quantum_used += 1
            current_time += 1
            if current_process.remaining_time == 0:
                self.gantt.append(GanttEntry(process_name=current_process.name,
                                              start_time=gantt_start, end_time=current_time,
                                              color=current_process.color))
                self._finish_process(current_process, current_time)
                current_process = None
                quantum_used = 0
        return self._build_result()


# ============================================================
# 第三部分：GUI 界面
# ============================================================

try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    USE_BOOTSTRAP = True
except ImportError:
    USE_BOOTSTRAP = False

import matplotlib
matplotlib.use('TkAgg')

# --- 中文字体配置（确保甘特图中文正常显示）---
import matplotlib.font_manager as fm
_cn_font_found = False
for _cn in ['Microsoft YaHei', 'SimHei', 'STHeiti', 'WenQuanYi Micro Hei',
            'PingFang SC', 'Noto Sans CJK SC', 'Source Han Sans CN']:
    if any(_cn.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        matplotlib.rcParams['font.sans-serif'] = [_cn, 'DejaVu Sans']
        _cn_font_found = True
        break
if not _cn_font_found:
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
# 清除字体缓存以确保新配置生效
try:
    fm._load_fontmanager(try_read_cache=False)
except Exception:
    pass

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

COLORS = {
    'bg': '#F7F8FA', 'card': '#FFFFFF', 'primary': '#4A90D9',
    'success': '#50C878', 'danger': '#E85D75', 'warning': '#F5A623',
    'text': '#2C3E50', 'text_light': '#7F8C8D', 'border': '#E1E5EA',
}


class SchedulerApp:
    """处理机调度模拟系统主界面"""

    def __init__(self):
        # --- 强制中文字体 ---
        _FONT = "Microsoft YaHei"
        _FONT_TITLE = "Microsoft YaHei"

        if USE_BOOTSTRAP:
            self.root = ttkb.Window(title="操作系统处理机调度模拟", themename="cosmo",
                                     size=(1400, 900), minsize=(1100, 700))
        else:
            self.root = tk.Tk()
            self.root.title("操作系统处理机调度模拟")
            self.root.geometry("1400x900")
            self.root.minsize(1100, 700)
            self.root.configure(bg=COLORS['bg'])

        # 设置全局默认字体
        self.root.option_add("*Font", f"{{{_FONT}}} 10")
        self.root.option_add("*TCombobox*Font", f"{{{_FONT}}} 10")
        self.root.option_add("*TEntry*Font", f"{{{_FONT}}} 10")
        self.root.option_add("*TLabel*Font", f"{{{_FONT}}} 10")
        self.root.option_add("*TButton*Font", f"{{{_FONT}}} 10")

        # ttk 样式字体
        style = ttk.Style(self.root)
        style.configure(".", font=(_FONT, 10))
        style.configure("Treeview", font=(_FONT, 10), rowheight=28)
        style.configure("Treeview.Heading", font=(_FONT, 10, "bold"))
        style.configure("TNotebook.Tab", font=(_FONT, 10))
        style.configure("TButton", font=(_FONT, 10))
        style.configure("TLabel", font=(_FONT, 10))
        style.configure("TRadiobutton", font=(_FONT, 10))

        self.root.update_idletasks()
        w, h = 1400, 900
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.processes: list = []
        self.schedule_result = None
        self.is_running = False
        self.is_paused = False
        self.animation_speed = 0.5
        self.current_step = 0
        self.animation_timer = None

        self.default_data = [("P1", 0, 3), ("P2", 2, 6), ("P3", 4, 4), ("P4", 6, 5), ("P5", 8, 2)]

        self._build_ui()
        self._load_default_data()

    def _build_ui(self):
        main_frame = tk.Frame(self.root, bg=COLORS['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._build_header(main_frame)

        content = tk.Frame(main_frame, bg=COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        left_panel = tk.Frame(content, bg=COLORS['card'], relief=tk.FLAT, bd=0,
                              highlightbackground=COLORS['border'], highlightthickness=1)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        left_panel.configure(width=380)
        left_panel.pack_propagate(False)
        self._build_left_panel(left_panel)

        right_panel = tk.Frame(content, bg=COLORS['card'], relief=tk.FLAT, bd=0,
                               highlightbackground=COLORS['border'], highlightthickness=1)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self._build_right_panel(right_panel)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=COLORS['primary'], height=70)
        header.pack(fill=tk.X, pady=(0, 5))
        header.pack_propagate(False)
        tk.Label(header, text="操作系统处理机调度模拟",
                 font=("微软雅黑", 20, "bold"), fg="white", bg=COLORS['primary']).pack(pady=(10, 0))
        tk.Label(header, text="FCFS / SJF / RR 调度算法实验系统",
                 font=("微软雅黑", 11), fg="#B8D4F0", bg=COLORS['primary']).pack(pady=(2, 10))

    def _build_left_panel(self, parent):
        tk.Label(parent, text="📋 进程管理", font=("微软雅黑", 13, "bold"),
                 fg=COLORS['text'], bg=COLORS['card']).pack(anchor=tk.W, padx=15, pady=(15, 5))

        table_frame = tk.Frame(parent, bg=COLORS['card'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        columns = ("name", "arrival", "burst")
        self.process_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        self.process_tree.heading("name", text="进程名")
        self.process_tree.heading("arrival", text="到达时间")
        self.process_tree.heading("burst", text="服务时间")
        self.process_tree.column("name", width=100, anchor=tk.CENTER)
        self.process_tree.column("arrival", width=110, anchor=tk.CENTER)
        self.process_tree.column("burst", width=110, anchor=tk.CENTER)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)
        self.process_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        input_frame = tk.LabelFrame(parent, text="添加进程", font=("微软雅黑", 10),
                                     bg=COLORS['card'], fg=COLORS['text'], padx=10, pady=8)
        input_frame.pack(fill=tk.X, padx=15, pady=5)
        self.entry_name = self._make_input(input_frame, "进程名:", 0)
        self.entry_arrival = self._make_input(input_frame, "到达时间:", 1)
        self.entry_burst = self._make_input(input_frame, "服务时间:", 2)

        btn_frame = tk.Frame(parent, bg=COLORS['card'])
        btn_frame.pack(fill=tk.X, padx=15, pady=5)
        self._make_btn(btn_frame, "➕ 添加", self._add_process, COLORS['primary']).pack(side=tk.LEFT, padx=2)
        self._make_btn(btn_frame, "❌ 删除选中", self._delete_process, COLORS['danger']).pack(side=tk.LEFT, padx=2)
        self._make_btn(btn_frame, "🗑 清空", self._clear_processes, COLORS['warning']).pack(side=tk.LEFT, padx=2)
        self._make_btn(btn_frame, "🎲 随机", self._random_processes, '#9B59B6').pack(side=tk.LEFT, padx=2)

        algo_frame = tk.LabelFrame(parent, text="调度算法", font=("微软雅黑", 10),
                                    bg=COLORS['card'], fg=COLORS['text'], padx=10, pady=8)
        algo_frame.pack(fill=tk.X, padx=15, pady=5)
        self.algo_var = tk.StringVar(value="FCFS")
        for text, val in [("FCFS (先来先服务)", "FCFS"), ("抢占式 SJF (SRTF)", "SJF"), ("RR (时间片轮转)", "RR")]:
            tk.Radiobutton(algo_frame, text=text, variable=self.algo_var, value=val,
                           font=("微软雅黑", 10), bg=COLORS['card'], fg=COLORS['text'],
                           activebackground=COLORS['card'], selectcolor=COLORS['card'],
                           command=self._on_algo_change).pack(anchor=tk.W, pady=2)

        self.quantum_frame = tk.Frame(algo_frame, bg=COLORS['card'])
        tk.Label(self.quantum_frame, text="时间片:", font=("微软雅黑", 10),
                 bg=COLORS['card'], fg=COLORS['text']).pack(side=tk.LEFT)
        self.quantum_var = tk.StringVar(value="2")
        tk.Entry(self.quantum_frame, textvariable=self.quantum_var, width=8,
                 font=("微软雅黑", 10), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=5)
        self.quantum_frame.pack_forget()

        speed_frame = tk.LabelFrame(parent, text="运行速度", font=("微软雅黑", 10),
                                     bg=COLORS['card'], fg=COLORS['text'], padx=10, pady=8)
        speed_frame.pack(fill=tk.X, padx=15, pady=5)
        self.speed_var = tk.DoubleVar(value=0.5)
        tk.Scale(speed_frame, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.speed_var, font=("微软雅黑", 9), bg=COLORS['card'], fg=COLORS['text'],
                 highlightthickness=0, length=300, command=self._on_speed_change).pack(fill=tk.X)
        tk.Label(speed_frame, text="慢 ← → 快", font=("微软雅黑", 8),
                 bg=COLORS['card'], fg=COLORS['text_light']).pack()

        ctrl_frame = tk.Frame(parent, bg=COLORS['card'])
        ctrl_frame.pack(fill=tk.X, padx=15, pady=(10, 15))
        self.btn_start = self._make_btn(ctrl_frame, "▶ 开始模拟", self._start_simulation, COLORS['success'])
        self.btn_start.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.btn_pause = self._make_btn(ctrl_frame, "⏸ 暂停", self._toggle_pause, COLORS['warning'])
        self.btn_pause.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.btn_reset = self._make_btn(ctrl_frame, "🔄 重置", self._reset, COLORS['danger'])
        self.btn_reset.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

    def _build_right_panel(self, parent):
        if USE_BOOTSTRAP:
            self.notebook = ttkb.Notebook(parent)
        else:
            self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        gantt_frame = tk.Frame(self.notebook, bg=COLORS['card'])
        self.notebook.add(gantt_frame, text="  📊 甘特图  ")
        self._build_gantt_tab(gantt_frame)

        status_frame = tk.Frame(self.notebook, bg=COLORS['card'])
        self.notebook.add(status_frame, text="  📋 实时状态  ")
        self._build_status_tab(status_frame)

        perf_frame = tk.Frame(self.notebook, bg=COLORS['card'])
        self.notebook.add(perf_frame, text="  📈 性能指标  ")
        self._build_perf_tab(perf_frame)

        log_frame = tk.Frame(self.notebook, bg=COLORS['card'])
        self.notebook.add(log_frame, text="  📝 调度日志  ")
        self._build_log_tab(log_frame)

    def _build_gantt_tab(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS['card'])
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        self._make_btn(toolbar, "💾 导出PNG", self._export_gantt, COLORS['primary']).pack(side=tk.RIGHT)
        if HAS_MATPLOTLIB:
            self.fig = Figure(figsize=(10, 4), dpi=100, facecolor=COLORS['card'])
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            self._draw_empty_gantt()
        else:
            tk.Label(parent, text="需要安装 matplotlib: pip install matplotlib",
                     font=("微软雅黑", 12), fg=COLORS['danger'], bg=COLORS['card']).pack(expand=True)

    def _draw_empty_gantt(self):
        if not HAS_MATPLOTLIB:
            return
        self.ax.clear()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 1)
        self.ax.set_xlabel("时间", fontsize=11)
        self.ax.set_ylabel("进程", fontsize=11)
        self.ax.set_title("甘特图 (等待模拟运行)", fontsize=13, fontweight='bold')
        self.ax.set_yticks([])
        self.ax.grid(True, axis='x', alpha=0.3)
        self.fig.tight_layout()
        self.canvas.draw()

    def _build_status_tab(self, parent):
        columns = ("clock", "running", "arrival", "burst", "executed", "remaining", "status")
        self.status_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        for col, text, width in [("clock", "时钟", 60), ("running", "当前运行", 80),
                                  ("arrival", "到达时间", 80), ("burst", "服务时间", 80),
                                  ("executed", "已运行", 70), ("remaining", "剩余时间", 80),
                                  ("status", "状态", 70)]:
            self.status_tree.heading(col, text=text)
            self.status_tree.column(col, width=width, anchor=tk.CENTER)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.status_tree.yview)
        self.status_tree.configure(yscrollcommand=scrollbar.set)
        self.status_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10, side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, pady=10, side=tk.RIGHT)

    def _build_perf_tab(self, parent):
        summary_frame = tk.LabelFrame(parent, text="📊 系统整体指标", font=("微软雅黑", 12, "bold"),
                                       bg=COLORS['card'], fg=COLORS['text'], padx=20, pady=15)
        summary_frame.pack(fill=tk.X, padx=15, pady=10)
        self.summary_labels = {}
        for i, (key, text) in enumerate([("avg_turnaround", "平均周转时间"), ("avg_weighted", "平均带权周转时间"),
                                          ("cpu_util", "CPU 利用率"), ("throughput", "吞吐量")]):
            frame = tk.Frame(summary_frame, bg=COLORS['card'])
            frame.grid(row=i // 2, column=i % 2, padx=20, pady=8, sticky=tk.W)
            tk.Label(frame, text=f"{text}:", font=("微软雅黑", 11),
                     bg=COLORS['card'], fg=COLORS['text_light']).pack(side=tk.LEFT)
            lbl = tk.Label(frame, text="--", font=("微软雅黑", 13, "bold"),
                           bg=COLORS['card'], fg=COLORS['primary'])
            lbl.pack(side=tk.LEFT, padx=8)
            self.summary_labels[key] = lbl

        detail_frame = tk.LabelFrame(parent, text="📋 各进程指标", font=("微软雅黑", 12, "bold"),
                                      bg=COLORS['card'], fg=COLORS['text'], padx=10, pady=10)
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        columns = ("name", "arrival", "burst", "finish", "turnaround", "weighted")
        self.perf_tree = ttk.Treeview(detail_frame, columns=columns, show="headings", height=8)
        for col, text in [("name", "进程"), ("arrival", "到达时间"), ("burst", "服务时间"),
                          ("finish", "完成时间"), ("turnaround", "周转时间"), ("weighted", "带权周转")]:
            self.perf_tree.heading(col, text=text)
            self.perf_tree.column(col, width=100, anchor=tk.CENTER)
        self.perf_tree.pack(fill=tk.BOTH, expand=True)

    def _build_log_tab(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS['card'])
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        self._make_btn(toolbar, "🗑 清空日志", self._clear_log, COLORS['warning']).pack(side=tk.RIGHT)
        self.log_text = tk.Text(parent, font=("Consolas", 10), bg='#FAFBFC', fg=COLORS['text'],
                                relief=tk.FLAT, bd=0, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10), side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, pady=(0, 10), side=tk.RIGHT)
        for tag, color in [("arrive", "#3498DB"), ("start", "#27AE60"), ("finish", "#E74C3C"),
                           ("preempt", "#F39C12"), ("quantum_end", "#9B59B6"), ("info", "#7F8C8D")]:
            self.log_text.tag_configure(tag, foreground=color)

    # --- 辅助 ---

    def _make_input(self, parent, label, row):
        tk.Label(parent, text=label, font=("微软雅黑", 10),
                 bg=COLORS['card'], fg=COLORS['text']).grid(row=row, column=0, sticky=tk.W, pady=3)
        entry = tk.Entry(parent, width=20, font=("微软雅黑", 10), relief=tk.SOLID, bd=1)
        entry.grid(row=row, column=1, padx=5, pady=3, sticky=tk.EW)
        parent.columnconfigure(1, weight=1)
        return entry

    def _make_btn(self, parent, text, command, color):
        if USE_BOOTSTRAP:
            style_map = {COLORS['primary']: 'primary', COLORS['success']: 'success',
                         COLORS['danger']: 'danger', COLORS['warning']: 'warning', '#9B59B6': 'info'}
            return ttkb.Button(parent, text=text, command=command, bootstyle=style_map.get(color, 'primary'), width=10)
        btn = tk.Button(parent, text=text, command=command, font=("微软雅黑", 10), fg="white", bg=color,
                        activebackground=color, activeforeground="white", relief=tk.FLAT, bd=0,
                        padx=12, pady=6, cursor="hand2")
        hover = self._lighten(color)
        btn.bind("<Enter>", lambda e, b=btn, c=hover: b.configure(bg=c))
        btn.bind("<Leave>", lambda e, b=btn, c=color: b.configure(bg=c))
        return btn

    def _lighten(self, h):
        h = h.lstrip('#')
        r, g, b = min(255, int(h[:2], 16) + 30), min(255, int(h[2:4], 16) + 30), min(255, int(h[4:6], 16) + 30)
        return f'#{r:02x}{g:02x}{b:02x}'

    # --- 进程管理 ---

    def _load_default_data(self):
        for name, arrival, burst in self.default_data:
            p = Process(name=name, arrival_time=arrival, burst_time=burst,
                        color=PROCESS_COLORS[len(self.processes) % len(PROCESS_COLORS)])
            self.processes.append(p)
            self.process_tree.insert("", tk.END, values=(name, arrival, burst))

    def _add_process(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入进程名"); return
        try:
            arrival, burst = int(self.entry_arrival.get().strip()), int(self.entry_burst.get().strip())
            if arrival < 0 or burst <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "到达时间需≥0，服务时间需>0"); return
        if any(p.name == name for p in self.processes):
            messagebox.showwarning("提示", f"进程 {name} 已存在"); return
        color = PROCESS_COLORS[len(self.processes) % len(PROCESS_COLORS)]
        self.processes.append(Process(name=name, arrival_time=arrival, burst_time=burst, color=color))
        self.process_tree.insert("", tk.END, values=(name, arrival, burst))
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, f"P{len(self.processes) + 1}")

    def _delete_process(self):
        selected = self.process_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要删除的进程"); return
        for item in selected:
            name = self.process_tree.item(item, "values")[0]
            self.processes = [p for p in self.processes if p.name != name]
            self.process_tree.delete(item)

    def _clear_processes(self):
        self.processes.clear()
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)

    def _random_processes(self):
        self._clear_processes()
        arrival = 0
        for i in range(random.randint(4, 7)):
            burst = random.randint(1, 10)
            color = PROCESS_COLORS[i % len(PROCESS_COLORS)]
            self.processes.append(Process(name=f"P{i+1}", arrival_time=arrival, burst_time=burst, color=color))
            self.process_tree.insert("", tk.END, values=(f"P{i+1}", arrival, burst))
            arrival += random.randint(0, 3)

    def _on_algo_change(self):
        if self.algo_var.get() == "RR":
            self.quantum_frame.pack(fill=tk.X, pady=(5, 0))
        else:
            self.quantum_frame.pack_forget()

    def _on_speed_change(self, value):
        self.animation_speed = float(value)

    # --- 模拟控制 ---

    def _start_simulation(self):
        if not self.processes:
            messagebox.showwarning("提示", "请先添加进程"); return
        if self.is_running: return
        self._reset()
        algo = self.algo_var.get()
        try:
            if algo == "FCFS":
                scheduler = FCFSScheduler(self.processes)
            elif algo == "SJF":
                scheduler = SJFScheduler(self.processes)
            elif algo == "RR":
                quantum = int(self.quantum_var.get())
                if quantum <= 0:
                    messagebox.showwarning("提示", "时间片必须大于0"); return
                scheduler = RRScheduler(self.processes, time_quantum=quantum)
            else:
                return
            self.schedule_result = scheduler.run()
            self.is_running, self.is_paused, self.current_step = True, False, 0
            self.btn_start.configure(state=tk.DISABLED)
            self._animate_result()
        except Exception as e:
            messagebox.showerror("错误", f"调度执行出错: {str(e)}")

    def _animate_result(self):
        if not self.is_running or not self.schedule_result: return
        if self.is_paused:
            self.animation_timer = self.root.after(100, self._animate_result); return
        events = self.schedule_result.events
        if self.current_step >= len(events):
            self._show_final_result()
            self.is_running = False
            self.btn_start.configure(state=tk.NORMAL)
            return
        event = events[self.current_step]
        self._append_log(event.detail, event.event_type)
        self._update_gantt_partial()
        self._update_status_table()
        self.current_step += 1
        self.animation_timer = self.root.after(int(self.animation_speed * 500), self._animate_result)

    def _toggle_pause(self):
        if not self.is_running: return
        self.is_paused = not self.is_paused
        self.btn_pause.configure(text="▶ 继续" if self.is_paused else "⏸ 暂停")

    def _reset(self):
        if self.animation_timer:
            self.root.after_cancel(self.animation_timer)
            self.animation_timer = None
        self.is_running, self.is_paused, self.current_step = False, False, 0
        self.schedule_result = None
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_pause.configure(text="⏸ 暂停")
        self._draw_empty_gantt()
        for t in [self.status_tree, self.perf_tree]:
            for item in t.get_children(): t.delete(item)
        for k in self.summary_labels: self.summary_labels[k].configure(text="--")
        self._clear_log()

    # --- 结果展示 ---

    def _update_gantt_partial(self):
        if not HAS_MATPLOTLIB or not self.schedule_result or self.current_step <= 0: return
        events = self.schedule_result.events[:self.current_step]
        current_time = events[-1].time
        self.ax.clear()
        visible = [g for g in self.schedule_result.gantt if g.start_time <= current_time]
        if not visible:
            self.ax.set_xlim(0, max(current_time + 2, 10)); self.ax.set_ylim(0, 1)
            self.ax.set_title("甘特图 (运行中...)", fontsize=13, fontweight='bold')
            self.ax.grid(True, axis='x', alpha=0.3); self.fig.tight_layout(); self.canvas.draw(); return
        seen = []
        for g in self.schedule_result.gantt:
            if g.process_name not in seen: seen.append(g.process_name)
        y_pos = {n: i for i, n in enumerate(seen)}
        for g in visible:
            end = min(g.end_time, current_time + 1)
            if end <= g.start_time: continue
            y = y_pos[g.process_name]
            self.ax.barh(y, end - g.start_time, left=g.start_time, height=0.6,
                         color=g.color, edgecolor='white', linewidth=1.5, alpha=0.9)
            self.ax.text(g.start_time + (end - g.start_time) / 2, y, g.process_name,
                         ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        self.ax.set_yticks(range(len(seen)))
        self.ax.set_yticklabels(seen, fontsize=10)
        self.ax.set_xlim(0, self.schedule_result.total_time + 1)
        self.ax.set_ylim(-0.5, len(seen) - 0.5)
        self.ax.set_xlabel("时间"); self.ax.set_ylabel("进程")
        self.ax.set_title("甘特图 (运行中...)", fontsize=13, fontweight='bold')
        self.ax.grid(True, axis='x', alpha=0.3); self.ax.invert_yaxis()
        self.fig.tight_layout(); self.canvas.draw()

    def _update_status_table(self):
        if not self.schedule_result or self.current_step <= 0: return
        event = self.schedule_result.events[self.current_step - 1]
        clock = event.time
        for item in self.status_tree.get_children(): self.status_tree.delete(item)
        for p in self.schedule_result.processes:
            if p.finish_time and p.finish_time <= clock:
                status, executed, remaining = "完成", p.burst_time, 0
            elif p.arrival_time > clock:
                status, executed, remaining = "等待", 0, p.burst_time
            else:
                status = "运行" if (p.name == event.process_name and event.event_type == "start") else "就绪"
                executed = p.burst_time - p.remaining_time
                remaining = p.remaining_time
            self.status_tree.insert("", tk.END, values=(
                clock, p.name if status == "运行" else "--",
                p.arrival_time, p.burst_time, executed, remaining, status))

    def _show_final_result(self):
        if not self.schedule_result: return
        self._draw_full_gantt()
        self._show_final_status()
        self._show_performance()
        self._append_log("=" * 40, "info")
        self._append_log("✅ 模拟完成！", "finish")
        self._append_log(f"总运行时间: {self.schedule_result.total_time}", "info")
        self._append_log(f"平均周转时间: {self.schedule_result.avg_turnaround:.2f}", "info")
        self._append_log(f"平均带权周转时间: {self.schedule_result.avg_weighted_turnaround:.2f}", "info")

    def _draw_full_gantt(self):
        if not HAS_MATPLOTLIB or not self.schedule_result: return
        self.ax.clear()
        gantt = self.schedule_result.gantt
        if not gantt: self._draw_empty_gantt(); return
        seen = []
        for g in gantt:
            if g.process_name not in seen: seen.append(g.process_name)
        y_pos = {n: i for i, n in enumerate(seen)}
        for g in gantt:
            y = y_pos[g.process_name]
            self.ax.barh(y, g.end_time - g.start_time, left=g.start_time, height=0.6,
                         color=g.color, edgecolor='white', linewidth=1.5, alpha=0.9, zorder=2)
            self.ax.text(g.start_time + (g.end_time - g.start_time) / 2, y, g.process_name,
                         ha='center', va='center', fontsize=10, fontweight='bold', color='white', zorder=3)
        self.ax.set_yticks(range(len(seen)))
        self.ax.set_yticklabels(seen, fontsize=10)
        self.ax.set_xlim(0, self.schedule_result.total_time + 1)
        self.ax.set_ylim(-0.5, len(seen) - 0.5)
        self.ax.set_xlabel("时间"); self.ax.set_ylabel("进程")
        self.ax.set_title(f"甘特图 - {self.algo_var.get()} 调度结果", fontsize=13, fontweight='bold')
        self.ax.grid(True, axis='x', alpha=0.3, zorder=0)
        self.ax.invert_yaxis()
        self.ax.set_xticks(range(0, self.schedule_result.total_time + 2))
        self.fig.tight_layout(); self.canvas.draw()

    def _show_final_status(self):
        for item in self.status_tree.get_children(): self.status_tree.delete(item)
        for p in self.schedule_result.processes:
            self.status_tree.insert("", tk.END, values=(
                p.finish_time, "--", p.arrival_time, p.burst_time, p.burst_time, 0, "完成"))

    def _show_performance(self):
        r = self.schedule_result
        self.summary_labels["avg_turnaround"].configure(text=f"{r.avg_turnaround:.2f}")
        self.summary_labels["avg_weighted"].configure(text=f"{r.avg_weighted_turnaround:.2f}")
        self.summary_labels["cpu_util"].configure(text=f"{r.cpu_utilization:.1f}%")
        self.summary_labels["throughput"].configure(text=f"{r.throughput:.3f} 进程/时间单位")
        for item in self.perf_tree.get_children(): self.perf_tree.delete(item)
        for p in r.processes:
            self.perf_tree.insert("", tk.END, values=(
                p.name, p.arrival_time, p.burst_time, p.finish_time,
                p.turnaround_time, f"{p.weighted_turnaround_time:.2f}"))

    def _append_log(self, text, tag="info"):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _export_gantt(self):
        if not HAS_MATPLOTLIB or not self.schedule_result:
            messagebox.showinfo("提示", "请先运行模拟"); return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                             filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")],
                                             initialfile="gantt_chart.png")
        if path:
            self.fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['card'])
            messagebox.showinfo("成功", f"甘特图已导出到:\n{path}")

    def run(self):
        self.root.mainloop()


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    # PyInstaller 打包后修正工作目录
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    app = SchedulerApp()
    app.run()
