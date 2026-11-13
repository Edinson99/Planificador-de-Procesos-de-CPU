from abc import ABC, abstractmethod
from typing import List, Optional

from src.models.process import Process


class Scheduler(ABC):
    quantum: Optional[int] = None

    @abstractmethod
    def select_next(self, ready: List[Process]) -> Process:
        """Retira y devuelve el siguiente proceso de la cola de listos."""
