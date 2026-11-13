import argparse
from pathlib import Path
import sys
from typing import List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.engine.simulator import SimulationResult, Simulator
from src.models.process import Process
from src.process_io import load_processes_file
from src.schedulers import create_scheduler


def _read_processes(path: Optional[str]) -> List[Process]:
    if path is None:
        return [
            Process("P1", arrival_time=0, burst_time=5, priority=2),
            Process("P2", arrival_time=1, burst_time=3, priority=1),
            Process("P3", arrival_time=2, burst_time=1, priority=3),
        ]

    return load_processes_file(path)


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
    print("Utilizacion de CPU: {:.2f}%".format(result.cpu_utilization))
    print("Rendimiento: {:.4f} procesos/tick".format(result.throughput))
    print("Cambios de contexto: {}".format(result.context_switches))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador local de planificacion de procesos de CPU."
    )
    parser.add_argument(
        "--algorithm",
        choices=(
            "fcfs",
            "sjf",
            "srtf",
            "rr",
            "priority",
            "priority_preemptive",
        ),
        default="fcfs",
        help="Estrategia de planificacion (por defecto: fcfs).",
    )
    parser.add_argument("--quantum", type=int, help="Quantum requerido por Round Robin.")
    parser.add_argument("--input", help="Archivo JSON con la lista de procesos.")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre la interfaz grafica de escritorio (Tkinter).",
    )
    args = parser.parse_args()

    if args.gui:
        from src.ui.app import launch_app

        launch_app()
        return

    if args.algorithm == "rr" and args.quantum is None:
        parser.error("--quantum es obligatorio con --algorithm rr.")
    if args.algorithm != "rr" and args.quantum is not None:
        parser.error("--quantum solo se utiliza con --algorithm rr.")

    try:
        processes = _read_processes(args.input)
        quantum = args.quantum if args.quantum is not None else 2
        scheduler = create_scheduler(args.algorithm, quantum=quantum)
        result = Simulator(scheduler).run(processes)
    except ValueError as error:
        parser.error(str(error))
    _print_result(result)


if __name__ == "__main__":
    main()
