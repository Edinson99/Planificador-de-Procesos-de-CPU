from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set


class ProcessState(Enum):
    NEW = "Nuevo"
    READY = "Listo"
    RUNNING = "Ejecucion"
    BLOCKED = "Bloqueado"
    TERMINATED = "Terminado"


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
    remaining_time: int = field(init=False)
    state: ProcessState = field(default=ProcessState.NEW, init=False)
    first_start_time: Optional[int] = field(default=None, init=False)
    completion_time: Optional[int] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not self.pid:
            raise ValueError("El PID no puede estar vacio.")
        if self.arrival_time < 0:
            raise ValueError("El tiempo de llegada no puede ser negativo.")
        if self.burst_time <= 0:
            raise ValueError("La rafaga de CPU debe ser mayor que cero.")
        if (self.io_after is None) != (self.io_duration is None):
            raise ValueError("io_after e io_duration deben especificarse juntos.")
        if self.io_after is not None:
            if not 0 < self.io_after < self.burst_time:
                raise ValueError("io_after debe estar entre 1 y burst_time - 1.")
            if self.io_duration is None or self.io_duration <= 0:
                raise ValueError("io_duration debe ser mayor que cero.")
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
        return self.io_duration or 0

    @property
    def waiting_time(self) -> int:
        return self.turnaround_time - self.burst_time - self.blocked_time

    @property
    def response_time(self) -> int:
        if self.first_start_time is None:
            raise ValueError("El proceso aun no ha comenzado.")
        return self.first_start_time - self.arrival_time
