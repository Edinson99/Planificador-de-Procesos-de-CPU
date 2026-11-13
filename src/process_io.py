import json
from pathlib import Path
from typing import Any, Dict, List, Union

from src.models.process import IOEvent, Process


def load_processes_file(path: Union[str, Path]) -> List[Process]:
    try:
        content = Path(path).read_text(encoding="utf-8")
        data: Any = json.loads(content)
    except OSError as error:
        raise ValueError("No se pudo leer '{}': {}".format(path, error)) from error
    except UnicodeDecodeError as error:
        raise ValueError(
            "El archivo '{}' no esta codificado en UTF-8.".format(path)
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError("JSON invalido en '{}': {}".format(path, error)) from error

    if not isinstance(data, list) or not data:
        raise ValueError("El JSON debe contener una lista no vacia de procesos.")

    processes = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError("El elemento {} debe ser un objeto JSON.".format(index))
        try:
            process_data: Dict[str, Any] = dict(item)
            if "io_events" in process_data:
                io_events = process_data["io_events"]
                if not isinstance(io_events, list):
                    raise ValueError("io_events debe ser una lista.")
                process_data["io_events"] = [
                    _read_io_event(event, event_index)
                    for event_index, event in enumerate(io_events)
                ]
            processes.append(Process(**process_data))
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Proceso invalido en la posicion {}: {}".format(index, error)
            ) from error

    _validate_unique_pids(processes)
    return processes


def save_processes_file(path: Union[str, Path], processes: List[Process]) -> None:
    if not processes:
        raise ValueError("No hay procesos para guardar.")
    _validate_unique_pids(processes)
    data = [
        {
            "pid": process.pid,
            "arrival_time": process.arrival_time,
            "burst_time": process.burst_time,
            "priority": process.priority,
            "io_events": [
                {"after_cpu": event.after_cpu, "duration": event.duration}
                for event in process.io_events
            ],
        }
        for process in processes
    ]
    try:
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise ValueError("No se pudo guardar '{}': {}".format(path, error)) from error


def _read_io_event(value: Any, index: int) -> IOEvent:
    if not isinstance(value, dict):
        raise ValueError("El evento E/S {} debe ser un objeto.".format(index))
    try:
        after_cpu = value["after_cpu"]
        duration = value["duration"]
        if type(after_cpu) is not int or type(duration) is not int:
            raise ValueError
        return IOEvent(after_cpu=after_cpu, duration=duration)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "Evento E/S {} invalido: requiere after_cpu y duration enteros.".format(
                index
            )
        ) from error


def _validate_unique_pids(processes: List[Process]) -> None:
    if len({process.pid for process in processes}) != len(processes):
        raise ValueError("Los PID de los procesos deben ser unicos.")
