import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.engine.simulator import SimulationResult, Simulator
from src.models.process import Process
from src.schedulers import (
    FCFSScheduler,
    PriorityScheduler,
    RoundRobinScheduler,
    SJFScheduler,
)


def _read_processes(path: Optional[str]) -> List[Process]:
    if path is None:
        return [
            Process("P1", arrival_time=0, burst_time=5, priority=2),
            Process("P2", arrival_time=1, burst_time=3, priority=1),
            Process("P3", arrival_time=2, burst_time=1, priority=3),
        ]

    try:
        data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError("No se pudo leer '{}': {}".format(path, error)) from error
    except json.JSONDecodeError as error:
        raise ValueError("JSON invalido en '{}': {}".format(path, error)) from error

    if not isinstance(data, list) or not data:
        raise ValueError("El JSON debe contener una lista no vacia de procesos.")

    processes = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError("El elemento {} debe ser un objeto JSON.".format(index))
        try:
            process_data: Dict[str, Any] = item
            processes.append(Process(**process_data))
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Proceso invalido en la posicion {}: {}".format(index, error)
            ) from error
    return processes


def _format_gantt(result: SimulationResult) -> str:
    parts = [str(result.gantt[0].start)]
    for segment in result.gantt:
        label = segment.pid if segment.pid is not None else "Libre"
        parts.extend(["--", label, "--", str(segment.end)])
    return " ".join(parts)


def _print_result(result: SimulationResult) -> None:
    print("Gantt: {}".format(_format_gantt(result)))
    print(
        "{:<8}{:>9}{:>8}{:>8}{:>6}{:>10}{:>8}{:>11}".format(
            "PID",
            "Llegada",
            "Rafaga",
            "Inicio",
            "Fin",
            "Retorno",
            "Espera",
            "Respuesta",
        )
    )
    for process in result.processes:
        print(
            "{:<8}{:>9}{:>8}{:>8}{:>6}{:>10}{:>8}{:>11}".format(
                process.pid,
                process.arrival_time,
                process.burst_time,
                process.first_start_time,
                process.completion_time,
                process.turnaround_time,
                process.waiting_time,
                process.response_time,
            )
        )
    print("Espera promedio: {:.2f}".format(result.average_waiting_time))
    print("Retorno promedio: {:.2f}".format(result.average_turnaround_time))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador local de planificacion de procesos de CPU."
    )
    parser.add_argument(
        "--algorithm",
        choices=("fcfs", "sjf", "rr", "priority"),
        default="fcfs",
        help="Estrategia de planificacion (por defecto: fcfs).",
    )
    parser.add_argument("--quantum", type=int, help="Quantum requerido por Round Robin.")
    parser.add_argument("--input", help="Archivo JSON con la lista de procesos.")
    args = parser.parse_args()

    if args.algorithm == "rr" and args.quantum is None:
        parser.error("--quantum es obligatorio con --algorithm rr.")
    if args.algorithm != "rr" and args.quantum is not None:
        parser.error("--quantum solo se utiliza con --algorithm rr.")

    try:
        processes = _read_processes(args.input)
        schedulers = {
            "fcfs": FCFSScheduler,
            "sjf": SJFScheduler,
            "rr": lambda: RoundRobinScheduler(args.quantum),
            "priority": PriorityScheduler,
        }
        result = Simulator(schedulers[args.algorithm]()).run(processes)
    except ValueError as error:
        parser.error(str(error))
    _print_result(result)


if __name__ == "__main__":
    main()
