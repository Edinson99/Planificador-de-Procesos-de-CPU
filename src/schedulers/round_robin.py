from typing import List

from src.models.process import Process
from src.schedulers.base import Scheduler


class RoundRobinScheduler(Scheduler):
    def __init__(self, quantum: int) -> None:
        if quantum <= 0:
            raise ValueError("El quantum debe ser mayor que cero.")
        self.quantum = quantum

    def select_next(self, ready: List[Process]) -> Process:
        return ready.pop(0)
