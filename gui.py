"""
主界面模块
使用 tkinter + ttkbootstrap 构建现代化GUI
包含：进程管理、算法选择、甘特图、状态表、日志、性能指标
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import random
import os

try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    from ttkbootstrap.scrolled import ScrolledFrame
    USE_BOOTSTRAP = True
except ImportError:
    USE_BOOTSTRAP = False

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.font_manager as fm
    # --- 中文字体配置（确保甘特图中文正常显示）---
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
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from models import Process, ProcessStatus, ScheduleResult
from schedulers import FCFSScheduler, SJFScheduler, RRScheduler

# ============================================================
# 配色方案
# ============================================================
COLORS = {
    'bg': '#F7F8FA',
    'card': '#FFFFFF',
    'primary': '#4A90D9',
    'primary_hover': '#357ABD',
    'success': '#50C878',
    'success_hover': '#3DAE63',
    'danger': '#E85D75',
    'danger_hover': '#D44A63',
    'warning': '#F5A623',
    'warning_hover': '#E09515',
    'text': '#2C3E50',
    'text_light': '#7F8C8D',
    'border': '#E1E5EA',
    'header_bg': '#4A90D9',
    'header_fg': '#FFFFFF',
}

# 进程配色
PROCESS_COLORS = [
    '#4A90D9', '#E85D75', '#50C878', '#F5A623', '#9B59B6',
    '#1ABC9C', '#E74C3C', '#3498DB', '#E67E22', '#2ECC71',
]


class SchedulerApp:
    """处理机调度模拟系统主界面"""

    def __init__(self):
        # 创建主窗口
        if USE_BOOTSTRAP:
            self.root = ttkb.Window(
                title="操作系统处理机调度模拟",
                themename="cosmo",
                size=(1400, 900),
                minsize=(1100, 700)
            )
        else:
            self.root = tk.Tk()
            self.root.title("操作系统处理机调度模拟")
            self.root.geometry("1400x900")
            self.root.minsize(1100, 700)
            self.root.configure(bg=COLORS['bg'])

        # 居中显示
        self.root.update_idletasks()
        w, h = 1400, 900
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # 状态变量
        self.processes: list[Process] = []
        self.schedule_result: ScheduleResult = None
        self.is_running = False
        self.is_paused = False
        self.animation_speed = 0.5  # 秒/时间单位
        self.current_step = 0
        self.animation_timer = None

        # 默认测试数据
        self.default_data = [
            ("P1", 0, 3),
            ("P2", 2, 6),
            ("P3", 4, 4),
            ("P4", 6, 5),
            ("P5", 8, 2),
        ]

        # 初始化界面
        self._build_ui()
        self._load_default_data()

    def _build_ui(self):
        """构建主界面"""
        # 主容器
        main_frame = tk.Frame(self.root, bg=COLORS['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 顶部标题
        self._build_header(main_frame)

        # 中间内容区域 - 使用 PanedWindow 实现可拖拽分隔
        content = tk.Frame(main_frame, bg=COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # 左侧面板 (进程输入)
        left_panel = tk.Frame(content, bg=COLORS['card'], relief=tk.FLAT, bd=0,
                              highlightbackground=COLORS['border'], highlightthickness=1)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        left_panel.configure(width=380)
        left_panel.pack_propagate(False)
        self._build_left_panel(left_panel)

        # 右侧面板 (结果展示)
        right_panel = tk.Frame(content, bg=COLORS['card'], relief=tk.FLAT, bd=0,
                               highlightbackground=COLORS['border'], highlightthickness=1)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self._build_right_panel(right_panel)

    def _build_header(self, parent):
        """构建顶部标题区"""
        header = tk.Frame(parent, bg=COLORS['primary'], height=70)
        header.pack(fill=tk.X, pady=(0, 5))
        header.pack_propagate(False)

        tk.Label(header, text="操作系统处理机调度模拟",
                 font=("微软雅黑", 20, "bold"), fg="white", bg=COLORS['primary']
                 ).pack(pady=(10, 0))
        tk.Label(header, text="FCFS / SJF / RR 调度算法实验系统",
                 font=("微软雅黑", 11), fg="#B8D4F0", bg=COLORS['primary']
                 ).pack(pady=(2, 10))

    def _build_left_panel(self, parent):
        """构建左侧输入区"""
        # 标题
        title_frame = tk.Frame(parent, bg=COLORS['card'])
        title_frame.pack(fill=tk.X, padx=15, pady=(15, 5))
        tk.Label(title_frame, text="📋 进程管理",
                 font=("微软雅黑", 13, "bold"), fg=COLORS['text'], bg=COLORS['card']
                 ).pack(side=tk.LEFT)

        # 进程表格
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

        # 新增进程输入区
        input_frame = tk.LabelFrame(parent, text="添加进程", font=("微软雅黑", 10),
                                     bg=COLORS['card'], fg=COLORS['text'],
                                     padx=10, pady=8)
        input_frame.pack(fill=tk.X, padx=15, pady=5)

        fields = [("进程名:", "P"), ("到达时间:", "0"), ("服务时间:", "1")]
        self.entry_name = self._make_input(input_frame, "进程名:", 0)
        self.entry_arrival = self._make_input(input_frame, "到达时间:", 1)
        self.entry_burst = self._make_input(input_frame, "服务时间:", 2)

        # 按钮区 - 进程操作
        btn_frame = tk.Frame(parent, bg=COLORS['card'])
        btn_frame.pack(fill=tk.X, padx=15, pady=5)

        self._make_btn(btn_frame, "➕ 添加", self._add_process, COLORS['primary']).pack(side=tk.LEFT, padx=2)
        self._make_btn(btn_frame, "❌ 删除选中", self._delete_process, COLORS['danger']).pack(side=tk.LEFT, padx=2)
        self._make_btn(btn_frame, "🗑 清空", self._clear_processes, COLORS['warning']).pack(side=tk.LEFT, padx=2)
        self._make_btn(btn_frame, "🎲 随机", self._random_processes, '#9B59B6').pack(side=tk.LEFT, padx=2)

        # 算法选择区
        algo_frame = tk.LabelFrame(parent, text="调度算法", font=("微软雅黑", 10),
                                    bg=COLORS['card'], fg=COLORS['text'],
                                    padx=10, pady=8)
        algo_frame.pack(fill=tk.X, padx=15, pady=5)

        self.algo_var = tk.StringVar(value="FCFS")
        algos = [("FCFS (先来先服务)", "FCFS"), ("抢占式 SJF (SRTF)", "SJF"), ("RR (时间片轮转)", "RR")]
        for text, val in algos:
            rb = tk.Radiobutton(algo_frame, text=text, variable=self.algo_var, value=val,
                                font=("微软雅黑", 10), bg=COLORS['card'], fg=COLORS['text'],
                                activebackground=COLORS['card'], selectcolor=COLORS['card'],
                                command=self._on_algo_change)
            rb.pack(anchor=tk.W, pady=2)

        # 时间片输入（RR用）
        self.quantum_frame = tk.Frame(algo_frame, bg=COLORS['card'])
        tk.Label(self.quantum_frame, text="时间片:", font=("微软雅黑", 10),
                 bg=COLORS['card'], fg=COLORS['text']).pack(side=tk.LEFT)
        self.quantum_var = tk.StringVar(value="2")
        quantum_entry = tk.Entry(self.quantum_frame, textvariable=self.quantum_var,
                                 width=8, font=("微软雅黑", 10),
                                 relief=tk.SOLID, bd=1)
        quantum_entry.pack(side=tk.LEFT, padx=5)
        self.quantum_frame.pack_forget()  # 默认隐藏

        # 速度控制
        speed_frame = tk.LabelFrame(parent, text="运行速度", font=("微软雅黑", 10),
                                     bg=COLORS['card'], fg=COLORS['text'],
                                     padx=10, pady=8)
        speed_frame.pack(fill=tk.X, padx=15, pady=5)

        self.speed_var = tk.DoubleVar(value=0.5)
        speed_scale = tk.Scale(speed_frame, from_=0.1, to=2.0, resolution=0.1,
                               orient=tk.HORIZONTAL, variable=self.speed_var,
                               font=("微软雅黑", 9), bg=COLORS['card'], fg=COLORS['text'],
                               highlightthickness=0, length=300,
                               command=self._on_speed_change)
        speed_scale.pack(fill=tk.X)
        tk.Label(speed_frame, text="慢 ← → 快", font=("微软雅黑", 8),
                 bg=COLORS['card'], fg=COLORS['text_light']).pack()

        # 控制按钮区
        ctrl_frame = tk.Frame(parent, bg=COLORS['card'])
        ctrl_frame.pack(fill=tk.X, padx=15, pady=(10, 15))

        self.btn_start = self._make_btn(ctrl_frame, "▶ 开始模拟", self._start_simulation, COLORS['success'])
        self.btn_start.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        self.btn_pause = self._make_btn(ctrl_frame, "⏸ 暂停", self._toggle_pause, COLORS['warning'])
        self.btn_pause.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        self.btn_reset = self._make_btn(ctrl_frame, "🔄 重置", self._reset, COLORS['danger'])
        self.btn_reset.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

    def _build_right_panel(self, parent):
        """构建右侧结果区"""
        # 使用 Notebook 标签页
        if USE_BOOTSTRAP:
            self.notebook = ttkb.Notebook(parent)
        else:
            self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标签1: 甘特图
        gantt_frame = tk.Frame(self.notebook, bg=COLORS['card'])
        self.notebook.add(gantt_frame, text="  📊 甘特图  ")
        self._build_gantt_tab(gantt_frame)

        # 标签2: 实时状态
        status_frame = tk.Frame(self.notebook, bg=COLORS['card'])
        self.notebook.add(status_frame, text="  📋 实时状态  ")
        self._build_status_tab(status_frame)

        # 标签3: 性能指标
        perf_frame = tk.Frame(self.notebook, bg=COLORS['card'])
        self.notebook.add(perf_frame, text="  📈 性能指标  ")
        self._build_perf_tab(perf_frame)

        # 标签4: 调度日志
        log_frame = tk.Frame(self.notebook, bg=COLORS['card'])
        self.notebook.add(log_frame, text="  📝 调度日志  ")
        self._build_log_tab(log_frame)

    def _build_gantt_tab(self, parent):
        """构建甘特图标签页"""
        # 工具栏
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
        """绘制空白甘特图"""
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
        """构建实时状态标签页"""
        columns = ("clock", "running", "arrival", "burst", "executed", "remaining", "status")
        self.status_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)

        headers = [("clock", "时钟", 60), ("running", "当前运行", 80),
                   ("arrival", "到达时间", 80), ("burst", "服务时间", 80),
                   ("executed", "已运行", 70), ("remaining", "剩余时间", 80),
                   ("status", "状态", 70)]
        for col, text, width in headers:
            self.status_tree.heading(col, text=text)
            self.status_tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.status_tree.yview)
        self.status_tree.configure(yscrollcommand=scrollbar.set)
        self.status_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10, side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, pady=10, side=tk.RIGHT)

    def _build_perf_tab(self, parent):
        """构建性能指标标签页"""
        # 总体指标
        summary_frame = tk.LabelFrame(parent, text="📊 系统整体指标",
                                       font=("微软雅黑", 12, "bold"),
                                       bg=COLORS['card'], fg=COLORS['text'],
                                       padx=20, pady=15)
        summary_frame.pack(fill=tk.X, padx=15, pady=10)

        self.summary_labels = {}
        metrics = [("avg_turnaround", "平均周转时间"), ("avg_weighted", "平均带权周转时间"),
                   ("cpu_util", "CPU 利用率"), ("throughput", "吞吐量")]
        for i, (key, text) in enumerate(metrics):
            row, col = divmod(i, 2)
            frame = tk.Frame(summary_frame, bg=COLORS['card'])
            frame.grid(row=row, column=col, padx=20, pady=8, sticky=tk.W)
            tk.Label(frame, text=f"{text}:", font=("微软雅黑", 11),
                     bg=COLORS['card'], fg=COLORS['text_light']).pack(side=tk.LEFT)
            lbl = tk.Label(frame, text="--", font=("微软雅黑", 13, "bold"),
                           bg=COLORS['card'], fg=COLORS['primary'])
            lbl.pack(side=tk.LEFT, padx=8)
            self.summary_labels[key] = lbl

        # 各进程指标
        detail_frame = tk.LabelFrame(parent, text="📋 各进程指标",
                                      font=("微软雅黑", 12, "bold"),
                                      bg=COLORS['card'], fg=COLORS['text'],
                                      padx=10, pady=10)
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        columns = ("name", "arrival", "burst", "finish", "turnaround", "weighted")
        self.perf_tree = ttk.Treeview(detail_frame, columns=columns, show="headings", height=8)
        headers = [("name", "进程"), ("arrival", "到达时间"), ("burst", "服务时间"),
                   ("finish", "完成时间"), ("turnaround", "周转时间"), ("weighted", "带权周转")]
        for col, text in headers:
            self.perf_tree.heading(col, text=text)
            self.perf_tree.column(col, width=100, anchor=tk.CENTER)
        self.perf_tree.pack(fill=tk.BOTH, expand=True)

    def _build_log_tab(self, parent):
        """构建调度日志标签页"""
        toolbar = tk.Frame(parent, bg=COLORS['card'])
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        self._make_btn(toolbar, "🗑 清空日志", self._clear_log, COLORS['warning']).pack(side=tk.RIGHT)

        self.log_text = tk.Text(parent, font=("Consolas", 10), bg='#FAFBFC',
                                fg=COLORS['text'], relief=tk.FLAT, bd=0,
                                wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10), side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, pady=(0, 10), side=tk.RIGHT)

        # 日志颜色标签
        self.log_text.tag_configure("arrive", foreground="#3498DB")
        self.log_text.tag_configure("start", foreground="#27AE60")
        self.log_text.tag_configure("finish", foreground="#E74C3C")
        self.log_text.tag_configure("preempt", foreground="#F39C12")
        self.log_text.tag_configure("quantum_end", foreground="#9B59B6")
        self.log_text.tag_configure("info", foreground="#7F8C8D")

    # ============================================================
    # 辅助方法
    # ============================================================

    def _make_input(self, parent, label, row):
        """创建输入框"""
        tk.Label(parent, text=label, font=("微软雅黑", 10),
                 bg=COLORS['card'], fg=COLORS['text']).grid(row=row, column=0, sticky=tk.W, pady=3)
        entry = tk.Entry(parent, width=20, font=("微软雅黑", 10),
                         relief=tk.SOLID, bd=1)
        entry.grid(row=row, column=1, padx=5, pady=3, sticky=tk.EW)
        parent.columnconfigure(1, weight=1)
        return entry

    def _make_btn(self, parent, text, command, color):
        """创建现代化按钮"""
        if USE_BOOTSTRAP:
            style_map = {
                COLORS['primary']: 'primary',
                COLORS['success']: 'success',
                COLORS['danger']: 'danger',
                COLORS['warning']: 'warning',
                '#9B59B6': 'info',
            }
            style = style_map.get(color, 'primary')
            btn = ttkb.Button(parent, text=text, command=command,
                              bootstyle=style, width=10)
        else:
            btn = tk.Button(parent, text=text, command=command,
                            font=("微软雅黑", 10), fg="white", bg=color,
                            activebackground=color, activeforeground="white",
                            relief=tk.FLAT, bd=0, padx=12, pady=6, cursor="hand2")
            # hover 效果
            hover_color = self._lighten_color(color)
            btn.bind("<Enter>", lambda e, b=btn, c=hover_color: b.configure(bg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.configure(bg=c))
        return btn

    def _lighten_color(self, hex_color):
        """使颜色变亮"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, r + 30)
        g = min(255, g + 30)
        b = min(255, b + 30)
        return f'#{r:02x}{g:02x}{b:02x}'

    # ============================================================
    # 进程管理
    # ============================================================

    def _load_default_data(self):
        """加载默认测试数据"""
        for name, arrival, burst in self.default_data:
            p = Process(name=name, arrival_time=arrival, burst_time=burst,
                        color=PROCESS_COLORS[len(self.processes) % len(PROCESS_COLORS)])
            self.processes.append(p)
            self.process_tree.insert("", tk.END, values=(name, arrival, burst))

    def _add_process(self):
        """添加进程"""
        name = self.entry_name.get().strip()
        arrival_str = self.entry_arrival.get().strip()
        burst_str = self.entry_burst.get().strip()

        if not name:
            messagebox.showwarning("提示", "请输入进程名")
            return

        try:
            arrival = int(arrival_str)
            burst = int(burst_str)
            if arrival < 0 or burst <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "到达时间需≥0，服务时间需>0")
            return

        # 检查重名
        if any(p.name == name for p in self.processes):
            messagebox.showwarning("提示", f"进程 {name} 已存在")
            return

        color = PROCESS_COLORS[len(self.processes) % len(PROCESS_COLORS)]
        p = Process(name=name, arrival_time=arrival, burst_time=burst, color=color)
        self.processes.append(p)
        self.process_tree.insert("", tk.END, values=(name, arrival, burst))

        # 自动填充下一个进程名
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, f"P{len(self.processes) + 1}")

    def _delete_process(self):
        """删除选中进程"""
        selected = self.process_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要删除的进程")
            return

        for item in selected:
            values = self.process_tree.item(item, "values")
            name = values[0]
            self.processes = [p for p in self.processes if p.name != name]
            self.process_tree.delete(item)

    def _clear_processes(self):
        """清空所有进程"""
        self.processes.clear()
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)

    def _random_processes(self):
        """随机生成进程"""
        self._clear_processes()
        count = random.randint(4, 7)
        arrival = 0
        for i in range(count):
            burst = random.randint(1, 10)
            color = PROCESS_COLORS[i % len(PROCESS_COLORS)]
            p = Process(name=f"P{i+1}", arrival_time=arrival, burst_time=burst, color=color)
            self.processes.append(p)
            self.process_tree.insert("", tk.END, values=(p.name, arrival, burst))
            arrival += random.randint(0, 3)

    # ============================================================
    # 算法选择
    # ============================================================

    def _on_algo_change(self):
        """算法切换时显示/隐藏时间片输入"""
        if self.algo_var.get() == "RR":
            self.quantum_frame.pack(fill=tk.X, pady=(5, 0))
        else:
            self.quantum_frame.pack_forget()

    def _on_speed_change(self, value):
        """速度变化"""
        self.animation_speed = float(value)

    # ============================================================
    # 模拟控制
    # ============================================================

    def _start_simulation(self):
        """开始模拟"""
        if not self.processes:
            messagebox.showwarning("提示", "请先添加进程")
            return

        if self.is_running:
            return

        # 重置
        self._reset()

        # 根据选择的算法创建调度器
        algo = self.algo_var.get()
        try:
            if algo == "FCFS":
                scheduler = FCFSScheduler(self.processes)
            elif algo == "SJF":
                scheduler = SJFScheduler(self.processes)
            elif algo == "RR":
                quantum = int(self.quantum_var.get())
                if quantum <= 0:
                    messagebox.showwarning("提示", "时间片必须大于0")
                    return
                scheduler = RRScheduler(self.processes, time_quantum=quantum)
            else:
                return

            # 执行调度（非动画，一次性计算）
            self.schedule_result = scheduler.run()

            # 启动动画
            self.is_running = True
            self.is_paused = False
            self.current_step = 0
            self.btn_start.configure(state=tk.DISABLED)
            self._animate_result()

        except Exception as e:
            messagebox.showerror("错误", f"调度执行出错: {str(e)}")

    def _animate_result(self):
        """动画展示调度结果"""
        if not self.is_running or not self.schedule_result:
            return

        if self.is_paused:
            self.animation_timer = self.root.after(100, self._animate_result)
            return

        events = self.schedule_result.events
        if self.current_step >= len(events):
            # 动画结束，显示最终结果
            self._show_final_result()
            self.is_running = False
            self.btn_start.configure(state=tk.NORMAL)
            return

        # 显示当前事件
        event = events[self.current_step]
        self._append_log(event.detail, event.event_type)

        # 更新甘特图（逐步显示）
        self._update_gantt_partial()

        # 更新状态表
        self._update_status_table()

        self.current_step += 1
        delay = int(self.animation_speed * 500)
        self.animation_timer = self.root.after(delay, self._animate_result)

    def _toggle_pause(self):
        """暂停/继续"""
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.configure(text="▶ 继续")
        else:
            self.btn_pause.configure(text="⏸ 暂停")

    def _reset(self):
        """重置"""
        if self.animation_timer:
            self.root.after_cancel(self.animation_timer)
            self.animation_timer = None

        self.is_running = False
        self.is_paused = False
        self.current_step = 0
        self.schedule_result = None
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_pause.configure(text="⏸ 暂停")

        # 清空显示
        self._draw_empty_gantt()
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for item in self.perf_tree.get_children():
            self.perf_tree.delete(item)
        for key in self.summary_labels:
            self.summary_labels[key].configure(text="--")
        self._clear_log()

    # ============================================================
    # 结果展示
    # ============================================================

    def _update_gantt_partial(self):
        """逐步更新甘特图"""
        if not HAS_MATPLOTLIB or not self.schedule_result:
            return

        # 确定当前时间点
        if self.current_step <= 0:
            return

        events = self.schedule_result.events[:self.current_step]
        current_time = events[-1].time if events else 0

        self.ax.clear()

        # 收集到目前为止的甘特条目
        visible_gantt = [g for g in self.schedule_result.gantt if g.start_time <= current_time]

        if not visible_gantt:
            self.ax.set_xlim(0, max(current_time + 2, 10))
            self.ax.set_ylim(0, 1)
            self.ax.set_xlabel("时间", fontsize=11)
            self.ax.set_title("甘特图 (运行中...)", fontsize=13, fontweight='bold')
            self.ax.grid(True, axis='x', alpha=0.3)
            self.fig.tight_layout()
            self.canvas.draw()
            return

        # 获取进程列表（按首次出现顺序）
        seen = []
        for g in self.schedule_result.gantt:
            if g.process_name not in seen:
                seen.append(g.process_name)

        y_pos = {name: i for i, name in enumerate(seen)}

        for g in visible_gantt:
            # 截断到当前时间
            end = min(g.end_time, current_time + 1)
            if end <= g.start_time:
                continue
            y = y_pos[g.process_name]
            self.ax.barh(y, end - g.start_time, left=g.start_time, height=0.6,
                         color=g.color, edgecolor='white', linewidth=1.5, alpha=0.9)
            # 显示时间标签
            mid = g.start_time + (end - g.start_time) / 2
            self.ax.text(mid, y, g.process_name, ha='center', va='center',
                         fontsize=9, fontweight='bold', color='white')

        self.ax.set_yticks(range(len(seen)))
        self.ax.set_yticklabels(seen, fontsize=10)
        self.ax.set_xlim(0, self.schedule_result.total_time + 1)
        self.ax.set_ylim(-0.5, len(seen) - 0.5)
        self.ax.set_xlabel("时间", fontsize=11)
        self.ax.set_ylabel("进程", fontsize=11)
        self.ax.set_title("甘特图 (运行中...)", fontsize=13, fontweight='bold')
        self.ax.grid(True, axis='x', alpha=0.3)
        self.ax.invert_yaxis()
        self.fig.tight_layout()
        self.canvas.draw()

    def _update_status_table(self):
        """更新实时状态表"""
        if not self.schedule_result or self.current_step <= 0:
            return

        event = self.schedule_result.events[self.current_step - 1]
        clock = event.time

        # 清空旧数据
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)

        # 显示每个进程的当前状态
        for p in self.schedule_result.processes:
            # 判断在该时钟的状态
            executed = p.burst_time - p.remaining_time if p.remaining_time is not None else 0

            # 简化：根据事件推断状态
            status = "等待"
            running_name = event.process_name

            if p.name == running_name and event.event_type in ("start",):
                status = "运行"
                running_name = p.name
            elif p.status == ProcessStatus.FINISHED and p.finish_time and p.finish_time <= clock:
                status = "完成"
                executed = p.burst_time
            elif p.arrival_time <= clock:
                status = "就绪"

            # 使用实际完成数据
            if self.schedule_result and p.finish_time and p.finish_time <= clock:
                status = "完成"
                remaining = 0
                executed = p.burst_time
            elif p.arrival_time > clock:
                status = "等待"
                remaining = p.burst_time
                executed = 0
            else:
                remaining = max(0, p.burst_time - executed)

            color_tag = ""
            if status == "运行":
                color_tag = "running"
            elif status == "完成":
                color_tag = "finished"

            self.status_tree.insert("", tk.END, values=(
                clock, running_name if status == "运行" else "--",
                p.arrival_time, p.burst_time, executed, remaining, status
            ))

    def _show_final_result(self):
        """显示最终结果"""
        if not self.schedule_result:
            return

        # 更新甘特图（完整版）
        self._draw_full_gantt()

        # 更新状态表（最终状态）
        self._show_final_status()

        # 更新性能指标
        self._show_performance()

        # 完成日志
        self._append_log("=" * 40, "info")
        self._append_log("模拟完成！", "finish")
        self._append_log(f"总运行时间: {self.schedule_result.total_time}", "info")
        self._append_log(f"平均周转时间: {self.schedule_result.avg_turnaround:.2f}", "info")
        self._append_log(f"平均带权周转时间: {self.schedule_result.avg_weighted_turnaround:.2f}", "info")

    def _draw_full_gantt(self):
        """绘制完整甘特图"""
        if not HAS_MATPLOTLIB or not self.schedule_result:
            return

        self.ax.clear()
        gantt = self.schedule_result.gantt

        if not gantt:
            self._draw_empty_gantt()
            return

        seen = []
        for g in gantt:
            if g.process_name not in seen:
                seen.append(g.process_name)

        y_pos = {name: i for i, name in enumerate(seen)}

        for g in gantt:
            y = y_pos[g.process_name]
            self.ax.barh(y, g.end_time - g.start_time, left=g.start_time,
                         height=0.6, color=g.color, edgecolor='white',
                         linewidth=1.5, alpha=0.9, zorder=2)
            mid = g.start_time + (g.end_time - g.start_time) / 2
            self.ax.text(mid, y, g.process_name, ha='center', va='center',
                         fontsize=10, fontweight='bold', color='white', zorder=3)

        self.ax.set_yticks(range(len(seen)))
        self.ax.set_yticklabels(seen, fontsize=10)
        self.ax.set_xlim(0, self.schedule_result.total_time + 1)
        self.ax.set_ylim(-0.5, len(seen) - 0.5)
        self.ax.set_xlabel("时间", fontsize=11)
        self.ax.set_ylabel("进程", fontsize=11)

        algo_name = self.algo_var.get()
        self.ax.set_title(f"甘特图 - {algo_name} 调度结果", fontsize=13, fontweight='bold')
        self.ax.grid(True, axis='x', alpha=0.3, zorder=0)
        self.ax.invert_yaxis()

        # 时间刻度
        self.ax.set_xticks(range(0, self.schedule_result.total_time + 2))
        self.fig.tight_layout()
        self.canvas.draw()

    def _show_final_status(self):
        """显示最终状态表"""
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)

        for p in self.schedule_result.processes:
            self.status_tree.insert("", tk.END, values=(
                p.finish_time, "--",
                p.arrival_time, p.burst_time,
                p.burst_time, 0, "完成"
            ))

    def _show_performance(self):
        """显示性能指标"""
        r = self.schedule_result

        # 总体指标
        self.summary_labels["avg_turnaround"].configure(text=f"{r.avg_turnaround:.2f}")
        self.summary_labels["avg_weighted"].configure(text=f"{r.avg_weighted_turnaround:.2f}")
        self.summary_labels["cpu_util"].configure(text=f"{r.cpu_utilization:.1f}%")
        self.summary_labels["throughput"].configure(text=f"{r.throughput:.3f} 进程/时间单位")

        # 各进程指标
        for item in self.perf_tree.get_children():
            self.perf_tree.delete(item)

        for p in r.processes:
            self.perf_tree.insert("", tk.END, values=(
                p.name, p.arrival_time, p.burst_time,
                p.finish_time, p.turnaround_time,
                f"{p.weighted_turnaround_time:.2f}"
            ))

    # ============================================================
    # 日志
    # ============================================================

    def _append_log(self, text, tag="info"):
        """追加日志"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_log(self):
        """清空日志"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    # ============================================================
    # 导出功能
    # ============================================================

    def _export_gantt(self):
        """导出甘特图为PNG"""
        if not HAS_MATPLOTLIB or not self.schedule_result:
            messagebox.showinfo("提示", "请先运行模拟")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")],
            initialfile="gantt_chart.png"
        )
        if path:
            self.fig.savefig(path, dpi=150, bbox_inches='tight',
                             facecolor=COLORS['card'])
            messagebox.showinfo("成功", f"甘特图已导出到:\n{path}")

    def run(self):
        """运行应用"""
        self.root.mainloop()
