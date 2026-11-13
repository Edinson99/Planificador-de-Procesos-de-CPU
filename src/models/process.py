from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class ProcessState(Enum):
    NEW = "Nuevo"
    READY = "Listo"
    RUNNING = "Ejecucion"
    BLOCKED = "Bloqueado"
    TERMINATED = "Terminado"


@dataclass(frozen=True)
class IOEvent:
    after_cpu: int
    duration: int

    def __post_init__(self) -> None:
        if type(self.after_cpu) is not int or self.after_cpu <= 0:
            raise ValueError("after_cpu debe ser mayor que cero.")
        if type(self.duration) is not int or self.duration <= 0:
            raise ValueError("La duracion de E/S debe ser mayor que cero.")


_ALLOWED_TRANSITIONS: Dict[ProcessState, Set[ProcessState]] = {
    ProcessState.NEW: {ProcessState.READY},
    ProcessState.READY: {ProcessState.RUNNING},
    ProcessState.RUNNING: {
        ProcessState.READY,
        ProcessState.BLOCKED,
        ProcessState.TERMINATED,
    },
    ProcessState.BLOCKED: {ProcessState.READY},
    ProcessState.TERMINATED: set(),
}


@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0
    io_after: Optional[int] = None
    io_duration: Optional[int] = None
    io_events: List[IOEvent] = field(default_factory=list)
    remaining_time: int = field(init=False)
    state: ProcessState = field(default=ProcessState.NEW, init=False)
    first_start_time: Optional[int] = field(default=None, init=False)
    completion_time: Optional[int] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.pid, str) or not self.pid.strip():
            raise ValueError("El PID no puede estar vacio.")
        if type(self.arrival_time) is not int or self.arrival_time < 0:
            raise ValueError("El tiempo de llegada no puede ser negativo.")
        if type(self.burst_time) is not int or self.burst_time <= 0:
            raise ValueError("La rafaga de CPU debe ser mayor que cero.")
        if type(self.priority) is not int:
            raise ValueError("La prioridad debe ser un entero.")
        if (self.io_after is None) != (self.io_duration is None):
            raise ValueError("io_after e io_duration deben especificarse juntos.")
        if self.io_events is None:
            self.io_events = []
        else:
            self.io_events = list(self.io_events)
        if self.io_after is not None:
            if self.io_events:
                raise ValueError(
                    "Usa io_events o io_after/io_duration, pero no ambos."
                )
            self.io_events.append(IOEvent(self.io_after, self.io_duration))
        previous_after_cpu = 0
        for event in self.io_events:
            if not isinstance(event, IOEvent):
                raise ValueError("Cada evento de E/S debe ser una instancia IOEvent.")
            if event.after_cpu >= self.burst_time:
                raise ValueError(
                    "after_cpu debe ser menor que la rafaga total de CPU."
                )
            if event.after_cpu <= previous_after_cpu:
                raise ValueError(
                    "Los eventos de E/S deben ordenarse por after_cpu sin repetirse."
                )
            previous_after_cpu = event.after_cpu
        self.remaining_time = self.burst_time

    def transition_to(self, new_state: ProcessState) -> None:
        if new_state not in _ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(
                "Transicion no permitida: {} -> {} para {}.".format(
                    self.state.value, new_state.value, self.pid
                )
            )
        self.state = new_state

    @property
    def turnaround_time(self) -> int:
        completion_time = self.completion_time
        if completion_time is None:
            raise ValueError("El proceso aun no ha terminado.")
        return completion_time - self.arrival_time

    @property
    def blocked_time(self) -> int:
        return sum(event.duration for event in self.io_events)

    @property
    def waiting_time(self) -> int:
        return self.turnaround_time - self.burst_time - self.blocked_time

    @property
    def response_time(self) -> int:
        if self.first_start_time is None:
            raise ValueError("El proceso aun no ha comenzado.")
        return self.first_start_time - self.arrival_time
