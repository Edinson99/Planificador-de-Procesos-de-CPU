from typing import List

from src.models.process import Process
from src.schedulers.base import Scheduler


class SRTFScheduler(Scheduler):
    def select_next(self, ready: List[Process]) -> Process:
        index = min(
            range(len(ready)),
            key=lambda item: (
                ready[item].remaining_time,
                ready[item].arrival_time,
            ),
        )
        return ready.pop(index)

    def should_preempt(self, current: Process, ready: List[Process]) -> bool:
        return any(process.remaining_time < current.remaining_time for process in ready)
