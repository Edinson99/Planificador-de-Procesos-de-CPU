from typing import List

from src.models.process import Process
from src.schedulers.base import Scheduler


class FCFSScheduler(Scheduler):
    def select_next(self, ready: List[Process]) -> Process:
        return ready.pop(0)
