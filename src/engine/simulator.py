from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.models.process import Process, ProcessState
from src.schedulers.base import Scheduler


@dataclass(frozen=True)
class GanttSegment:
    start: int
    end: int
    pid: Optional[str]


@dataclass(frozen=True)
class SimulationSnapshot:
    time: int
    running: Optional[str]
    ready: Tuple[str, ...]
    blocked: Tuple[str, ...]
    new: Tuple[str, ...]
    terminated: Tuple[str, ...]


@dataclass
class SimulationResult:
    processes: List[Process]
    gantt: List[GanttSegment]
    timeline: List[SimulationSnapshot] = field(default_factory=list)

    @property
    def makespan(self) -> int:
        return self.gantt[-1].end if self.gantt else 0

    @property
    def average_waiting_time(self) -> float:
        return sum(process.waiting_time for process in self.processes) / len(
            self.processes
        )

    @property
    def average_turnaround_time(self) -> float:
        return sum(process.turnaround_time for process in self.processes) / len(
            self.processes
        )

    @property
    def cpu_busy_time(self) -> int:
        return sum(
            segment.end - segment.start
            for segment in self.gantt
            if segment.pid is not None
        )

    @property
    def cpu_idle_time(self) -> int:
        return self.makespan - self.cpu_busy_time

    @property
    def cpu_utilization(self) -> float:
        if self.makespan == 0:
            return 0.0
        return self.cpu_busy_time / self.makespan * 100

    @property
    def throughput(self) -> float:
        if self.makespan == 0:
            return 0.0
        return len(self.processes) / self.makespan

    @property
    def context_switches(self) -> int:
        switches = 0
        previous_pid: Optional[str] = None
        for segment in self.gantt:
            if (
                previous_pid is not None
                and segment.pid is not None
                and segment.pid != previous_pid
            ):
                switches += 1
            previous_pid = segment.pid
        return switches


class Simulator:
    def __init__(self, scheduler: Scheduler) -> None:
        self.scheduler = scheduler

    def run(self, processes: List[Process]) -> SimulationResult:
        if not processes:
            raise ValueError("Debe proporcionarse al menos un proceso.")
        if len({process.pid for process in processes}) != len(processes):
            raise ValueError("Los PID de los procesos deben ser unicos.")
        if any(process.state is not ProcessState.NEW for process in processes):
            raise ValueError("La simulacion requiere procesos en estado Nuevo.")

        ready: List[Process] = []
        blocked_until: Dict[str, int] = {}
        next_io_event = {process.pid: 0 for process in processes}
        gantt: List[GanttSegment] = []
        timeline: List[SimulationSnapshot] = []
        current: Optional[Process] = None
        quantum_left: Optional[int] = None
        time = 0

        while any(process.state is not ProcessState.TERMINATED for process in processes):
            for process in processes:
                if (
                    process.state is ProcessState.NEW
                    and process.arrival_time <= time
                ):
                    process.transition_to(ProcessState.READY)
                    ready.append(process)

            for process in processes:
                if (
                    process.state is ProcessState.BLOCKED
                    and blocked_until[process.pid] <= time
                ):
                    process.transition_to(ProcessState.READY)
                    ready.append(process)

            if (
                current is not None
                and ready
                and self.scheduler.should_preempt(current, ready)
            ):
                current.transition_to(ProcessState.READY)
                ready.append(current)
                current = None
                quantum_left = None

            if current is None and ready:
                current = self.scheduler.select_next(ready)
                current.transition_to(ProcessState.RUNNING)
                if current.first_start_time is None:
                    current.first_start_time = time
                quantum_left = self.scheduler.quantum

            timeline.append(self._snapshot(time, processes, ready, current))

            if current is None:
                self._record_tick(gantt, time, None)
                time += 1
                continue

            self._record_tick(gantt, time, current.pid)
            current.remaining_time -= 1
            time += 1
            if quantum_left is not None:
                quantum_left -= 1

            if current.remaining_time == 0:
                current.completion_time = time
                current.transition_to(ProcessState.TERMINATED)
                current = None
                quantum_left = None
            elif self._has_due_io_event(current, next_io_event):
                event = current.io_events[next_io_event[current.pid]]
                current.transition_to(ProcessState.BLOCKED)
                blocked_until[current.pid] = time + event.duration
                next_io_event[current.pid] += 1
                current = None
                quantum_left = None
            elif quantum_left == 0:
                current.transition_to(ProcessState.READY)
                ready.append(current)
                current = None
                quantum_left = None

        timeline.append(self._snapshot(time, processes, ready, current))
        return SimulationResult(processes=processes, gantt=gantt, timeline=timeline)

    @staticmethod
    def _has_due_io_event(
        process: Process, next_io_event: Dict[str, int]
    ) -> bool:
        event_index = next_io_event[process.pid]
        return (
            event_index < len(process.io_events)
            and process.burst_time - process.remaining_time
            == process.io_events[event_index].after_cpu
        )

    @staticmethod
    def _snapshot(
        time: int,
        processes: List[Process],
        ready: List[Process],
        current: Optional[Process],
    ) -> SimulationSnapshot:
        return SimulationSnapshot(
            time=time,
            running=current.pid if current is not None else None,
            ready=tuple(process.pid for process in ready),
            blocked=tuple(
                process.pid
                for process in processes
                if process.state is ProcessState.BLOCKED
            ),
            new=tuple(
                process.pid
                for process in processes
                if process.state is ProcessState.NEW
            ),
            terminated=tuple(
                process.pid
                for process in processes
                if process.state is ProcessState.TERMINATED
            ),
        )

    @staticmethod
    def _record_tick(
        gantt: List[GanttSegment], time: int, pid: Optional[str]
    ) -> None:
        if gantt and gantt[-1].pid == pid:
            previous = gantt[-1]
            gantt[-1] = GanttSegment(previous.start, time + 1, pid)
        else:
            gantt.append(GanttSegment(time, time + 1, pid))
