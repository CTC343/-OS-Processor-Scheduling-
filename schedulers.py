"""
调度算法模块
实现 FCFS、抢占式SJF(SRTF)、RR(时间片轮转) 三种调度算法
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
from models import Process, ProcessStatus, ScheduleEvent, GanttEntry, ScheduleResult

# 进程配色方案（甘特图用）
PROCESS_COLORS = [
    '#4A90D9',  # 蓝
    '#E85D75',  # 红粉
    '#50C878',  # 绿
    '#F5A623',  # 橙
    '#9B59B6',  # 紫
    '#1ABC9C',  # 青
    '#E74C3C',  # 红
    '#3498DB',  # 天蓝
    '#E67E22',  # 深橙
    '#2ECC71',  # 翠绿
]


class Scheduler(ABC):
    """调度器基类"""

    def __init__(self, processes: List[Process]):
        # 深拷贝进程列表，避免修改原始数据
        self.processes = [p.copy() for p in processes]
        self.events: List[ScheduleEvent] = []
        self.gantt: List[GanttEntry] = []
        self.current_time = 0
        self.total_time = 0

        # 分配颜色
        for i, p in enumerate(self.processes):
            p.color = PROCESS_COLORS[i % len(PROCESS_COLORS)]

    @abstractmethod
    def run(self) -> ScheduleResult:
        """执行调度，返回调度结果"""
        pass

    def _get_process_by_name(self, name: str) -> Process:
        """根据名称查找进程"""
        for p in self.processes:
            if p.name == name:
                return p
        return None

    def _check_arrivals(self, time: int):
        """检查在指定时间到达的进程"""
        for p in self.processes:
            if p.arrival_time == time and p.status == ProcessStatus.WAITING:
                p.status = ProcessStatus.READY
                self.events.append(ScheduleEvent(
                    time=time,
                    process_name=p.name,
                    event_type="arrive",
                    detail=f"{p.name} 到达"
                ))

    def _finish_process(self, process: Process, time: int):
        """标记进程完成"""
        process.status = ProcessStatus.FINISHED
        process.finish_time = time
        process.turnaround_time = process.finish_time - process.arrival_time
        if process.burst_time > 0:
            process.weighted_turnaround_time = process.turnaround_time / process.burst_time
        self.events.append(ScheduleEvent(
            time=time,
            process_name=process.name,
            event_type="finish",
            detail=f"{process.name} 完成 (周转时间={process.turnaround_time}, 带权周转={process.weighted_turnaround_time:.2f})",
            color=process.color
        ))

    def _build_result(self) -> ScheduleResult:
        """构建调度结果"""
        if not self.processes:
            return ScheduleResult(processes=[])

        total_time = max(p.finish_time for p in self.processes if p.finish_time is not None)
        cpu_busy = sum(p.burst_time for p in self.processes)
        avg_tt = sum(p.turnaround_time for p in self.processes) / len(self.processes)
        avg_wtt = sum(p.weighted_turnaround_time for p in self.processes) / len(self.processes)
        cpu_util = cpu_busy / total_time * 100 if total_time > 0 else 0
        throughput = len(self.processes) / total_time if total_time > 0 else 0

        return ScheduleResult(
            processes=self.processes,
            gantt=self.gantt,
            events=self.events,
            total_time=total_time,
            avg_turnaround=avg_tt,
            avg_weighted_turnaround=avg_wtt,
            cpu_utilization=cpu_util,
            throughput=throughput
        )


class FCFSScheduler(Scheduler):
    """先来先服务调度算法"""

    def run(self) -> ScheduleResult:
        # 按到达时间排序
        self.processes.sort(key=lambda p: p.arrival_time)
        current_time = 0

        for process in self.processes:
            # 如果CPU空闲等待进程到达
            if current_time < process.arrival_time:
                current_time = process.arrival_time

            # 检查到达事件
            self._check_arrivals(process.arrival_time)

            # 开始运行
            process.status = ProcessStatus.RUNNING
            process.start_time = current_time
            self.events.append(ScheduleEvent(
                time=current_time,
                process_name=process.name,
                event_type="start",
                detail=f"{process.name} 开始运行",
                color=process.color
            ))

            # 甘特图条目
            end_time = current_time + process.burst_time
            self.gantt.append(GanttEntry(
                process_name=process.name,
                start_time=current_time,
                end_time=end_time,
                color=process.color
            ))

            # 进程完成
            current_time = end_time
            process.remaining_time = 0
            self._finish_process(process, current_time)

            # 检查在运行期间到达的其他进程
            for p in self.processes:
                if p.status == ProcessStatus.WAITING and p.arrival_time <= current_time:
                    p.status = ProcessStatus.READY
                    self.events.append(ScheduleEvent(
                        time=p.arrival_time,
                        process_name=p.name,
                        event_type="arrive",
                        detail=f"{p.name} 到达"
                    ))

        return self._build_result()


class SJFScheduler(Scheduler):
    """抢占式最短剩余时间优先调度算法 (SRTF)"""

    def run(self) -> ScheduleResult:
        current_time = 0
        max_time = sum(p.burst_time for p in self.processes) + max(p.arrival_time for p in self.processes) + 1
        current_process = None
        gantt_start = -1

        while current_time <= max_time:
            # 检查到达
            self._check_arrivals(current_time)

            # 获取就绪队列中剩余时间最短的进程
            ready = [p for p in self.processes
                     if p.status in (ProcessStatus.READY, ProcessStatus.RUNNING)
                     and p.remaining_time > 0]

            if not ready:
                # 检查是否所有进程都完成
                if all(p.status == ProcessStatus.FINISHED for p in self.processes):
                    break
                current_time += 1
                continue

            # 选择剩余时间最短的
            ready.sort(key=lambda p: (p.remaining_time, p.arrival_time))
            selected = ready[0]

            # 抢占检测：如果切换了进程
            if current_process != selected:
                # 结束上一个甘特条目
                if current_process is not None and gantt_start >= 0:
                    self.gantt.append(GanttEntry(
                        process_name=current_process.name,
                        start_time=gantt_start,
                        end_time=current_time,
                        color=current_process.color
                    ))
                    current_process.status = ProcessStatus.READY

                # 开始新进程
                current_process = selected
                current_process.status = ProcessStatus.RUNNING
                if current_process.start_time is None:
                    current_process.start_time = current_time
                gantt_start = current_time

                self.events.append(ScheduleEvent(
                    time=current_time,
                    process_name=current_process.name,
                    event_type="start",
                    detail=f"{current_process.name} 开始运行 (剩余={current_process.remaining_time})",
                    color=current_process.color
                ))

            # 执行一个时间单位
            current_process.remaining_time -= 1
            current_time += 1

            # 检查是否完成
            if current_process.remaining_time == 0:
                # 结束甘特条目
                self.gantt.append(GanttEntry(
                    process_name=current_process.name,
                    start_time=gantt_start,
                    end_time=current_time,
                    color=current_process.color
                ))
                self._finish_process(current_process, current_time)
                current_process = None
                gantt_start = -1

        return self._build_result()


class RRScheduler(Scheduler):
    """时间片轮转调度算法"""

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
            # 检查到达
            self._check_arrivals(current_time)

            # 将新到达的进程加入就绪队列
            for p in self.processes:
                if p.arrival_time == current_time and p.status == ProcessStatus.READY:
                    if p not in ready_queue:
                        ready_queue.append(p)

            # 检查时间片是否用完
            if current_process is not None and quantum_used >= self.time_quantum:
                # 结束当前甘特条目
                self.gantt.append(GanttEntry(
                    process_name=current_process.name,
                    start_time=gantt_start,
                    end_time=current_time,
                    color=current_process.color
                ))

                if current_process.remaining_time > 0:
                    current_process.status = ProcessStatus.READY
                    ready_queue.append(current_process)
                    self.events.append(ScheduleEvent(
                        time=current_time,
                        process_name=current_process.name,
                        event_type="quantum_end",
                        detail=f"{current_process.name} 时间片用完，回到就绪队列 (剩余={current_process.remaining_time})"
                    ))
                current_process = None
                quantum_used = 0

            # 如果当前没有运行的进程，从就绪队列取
            if current_process is None:
                if ready_queue:
                    current_process = ready_queue.pop(0)
                    current_process.status = ProcessStatus.RUNNING
                    if current_process.start_time is None:
                        current_process.start_time = current_time
                    gantt_start = current_time
                    quantum_used = 0
                    self.events.append(ScheduleEvent(
                        time=current_time,
                        process_name=current_process.name,
                        event_type="start",
                        detail=f"{current_process.name} 开始运行 (剩余={current_process.remaining_time})",
                        color=current_process.color
                    ))
                else:
                    # 检查是否全部完成
                    if all(p.status == ProcessStatus.FINISHED for p in self.processes):
                        break
                    current_time += 1
                    continue

            # 执行一个时间单位
            current_process.remaining_time -= 1
            quantum_used += 1
            current_time += 1

            # 检查是否完成
            if current_process.remaining_time == 0:
                self.gantt.append(GanttEntry(
                    process_name=current_process.name,
                    start_time=gantt_start,
                    end_time=current_time,
                    color=current_process.color
                ))
                self._finish_process(current_process, current_time)
                current_process = None
                quantum_used = 0

        return self._build_result()
