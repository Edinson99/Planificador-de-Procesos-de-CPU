from dataclasses import dataclass
from typing import Dict, List, Optional

from src.models.process import Process, ProcessState
from src.schedulers.base import Scheduler


@dataclass(frozen=True)
class GanttSegment:
    start: int
    end: int
    pid: Optional[str]


@dataclass
class SimulationResult:
    processes: List[Process]
    gantt: List[GanttSegment]

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
        gantt: List[GanttSegment] = []
        current: Optional[Process] = None
        quantum_left: Optional[int] = None
        time = 0

        while any(process.state is not ProcessState.TERMINATED for process in processes):
            for process in processes:
                if (
                    process.state is ProcessState.BLOCKED
                    and blocked_until[process.pid] <= time
                ):
                    process.transition_to(ProcessState.READY)
                    ready.append(process)

            for process in processes:
                if (
                    process.state is ProcessState.NEW
                    and process.arrival_time <= time
                ):
                    process.transition_to(ProcessState.READY)
                    ready.append(process)

            if current is None and ready:
                current = self.scheduler.select_next(ready)
                current.transition_to(ProcessState.RUNNING)
                if current.first_start_time is None:
                    current.first_start_time = time
                quantum_left = self.scheduler.quantum

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
            elif (
                current.io_after is not None
                and current.io_duration is not None
                and current.burst_time - current.remaining_time == current.io_after
            ):
                current.transition_to(ProcessState.BLOCKED)
                blocked_until[current.pid] = time + current.io_duration
                current = None
                quantum_left = None
            elif quantum_left == 0:
                current.transition_to(ProcessState.READY)
                ready.append(current)
                current = None
                quantum_left = None

        return SimulationResult(processes=processes, gantt=gantt)

    @staticmethod
    def _record_tick(
        gantt: List[GanttSegment], time: int, pid: Optional[str]
    ) -> None:
        if gantt and gantt[-1].pid == pid:
            previous = gantt[-1]
            gantt[-1] = GanttSegment(previous.start, time + 1, pid)
        else:
            gantt.append(GanttSegment(time, time + 1, pid))
