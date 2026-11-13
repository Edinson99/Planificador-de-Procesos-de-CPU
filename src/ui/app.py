import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Sequence, Tuple

from src.engine.simulator import GanttSegment, SimulationResult, Simulator
from src.models.process import IOEvent, Process
from src.process_io import load_processes_file, save_processes_file
from src.schedulers import create_scheduler


_ALGORITHMS = {
    "FIFO (No expropiable)": "fcfs",
    "Menos tiempo primero (No expropiable)": "sjf",
    "SRTF (Expropiable)": "srtf",
    "Round Robin (Expropiable)": "rr",
    "Prioridades (No expropiable)": "priority",
    "Prioridades expropiativas": "priority_preemptive",
}
_SPEEDS = {
    "Lenta": 500,
    "Normal": 120,
    "Rapida": 25,
}
_STATES = {
    "Bloqueado": "#19c91b",
    "Listo": "#13cbd2",
    "Ejecucion": "#ff3020",
}


def _statistics(values: Sequence[int]) -> Tuple[int, float, int, float]:
    mean = sum(values) / len(values)
    deviation = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
    return min(values), mean, max(values), deviation


def _format_stat(value: float) -> str:
    return "{:.2f}".format(value).replace(".", ",")


class SchedulerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Simulador de Planificacion de la CPU")
        self.root.geometry("1120x760")
        self.root.minsize(850, 620)

        self.algorithm_var = tk.StringVar(value="FIFO (No expropiable)")
        self.speed_var = tk.StringVar(value="Normal")
        self.show_processes_var = tk.BooleanVar(value=False)
        self.quantum_var = tk.StringVar(value="2")
        self._next_pid = 1
        self._result: Optional[SimulationResult] = None
        self._playback_tick = 0
        self._playback_after: Optional[str] = None
        self.timeline_info_var = tk.StringVar(value="Selecciona un tick del grafico para ver las colas.")

        self._build_ui()

    def _build_ui(self) -> None:
        self._build_menu()

        container = ttk.Frame(self.root, padding=(12, 8))
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        self.process_frame = ttk.LabelFrame(container, text="Procesos", padding=6)
        self._build_process_table()

        self.gantt_canvas = tk.Canvas(
            container,
            background="white",
            highlightthickness=1,
            highlightbackground="#c4c4c4",
        )
        self.gantt_canvas.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.gantt_canvas.bind("<Configure>", self._on_canvas_resize)
        self.gantt_scroll_x = ttk.Scrollbar(
            container, orient=tk.HORIZONTAL, command=self.gantt_canvas.xview
        )
        self.gantt_scroll_x.grid(row=2, column=0, sticky="ew")
        self.gantt_canvas.configure(xscrollcommand=self.gantt_scroll_x.set)
        self.gantt_canvas.bind("<Button-1>", self._select_timeline_tick)

        ttk.Label(
            container,
            textvariable=self.timeline_info_var,
            anchor=tk.W,
            padding=(6, 4),
        ).grid(row=3, column=0, sticky="ew")
        self.stats_frame = ttk.Frame(container)
        self.stats_frame.grid(row=4, column=0, sticky="ew", pady=(8, 4))
        for column in range(4):
            self.stats_frame.columnconfigure(column, weight=1)
        self._build_stat_cards()

        playback = ttk.Frame(container)
        playback.grid(row=5, column=0, sticky="ew", pady=(5, 2))
        playback.columnconfigure(0, weight=1)
        playback.columnconfigure(2, weight=1)
        ttk.Style(self.root).configure(
            "Play.TButton", font=("Segoe UI", 22), padding=(12, 0)
        )
        self.play_button = ttk.Button(
            playback,
            text="▶",
            command=self._toggle_playback,
            width=5,
            style="Play.TButton",
        )
        self.play_button.grid(row=0, column=1, pady=4)
        ttk.Button(
            playback,
            text="◀ Tick",
            command=lambda: self._step_timeline(-1),
        ).grid(row=0, column=0, sticky="e", padx=(0, 10))
        ttk.Button(
            playback,
            text="Tick ▶",
            command=lambda: self._step_timeline(1),
        ).grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Button(
            playback,
            text="Reiniciar",
            command=self._reset_playback,
        ).grid(row=0, column=3, sticky="w", padx=(14, 0))

        legend = ttk.Frame(container)
        legend.grid(row=6, column=0, sticky="w", pady=(4, 0))
        ttk.Label(legend, text="Leyenda:").pack(side=tk.LEFT, padx=(0, 12))
        for label, color in _STATES.items():
            ttk.Label(
                legend,
                text=label,
                foreground=color,
                font=("Segoe UI", 9, "bold"),
            ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(
            container,
            text="Configura procesos desde Archivo y ejecuta con el boton de reproduccion.",
            foreground="#666666",
        ).grid(row=7, column=0, sticky="e", pady=(4, 0))
        self._draw_empty_state()

    def _build_process_table(self) -> None:
        self.process_frame.columnconfigure(0, weight=1)
        self.process_frame.rowconfigure(0, weight=1)
        self.process_table = ttk.Treeview(
            self.process_frame,
            columns=("pid", "arrival", "burst", "priority", "io"),
            show="headings",
            selectmode="extended",
            height=4,
        )
        for key, title, width in (
            ("pid", "Nombre", 110),
            ("arrival", "Tiempo de llegada", 145),
            ("burst", "Tiempo de CPU", 130),
            ("priority", "Prioridad", 110),
            ("io", "E/S", 120),
        ):
            self.process_table.heading(key, text=title)
            self.process_table.column(key, width=width, anchor=tk.CENTER)
        scroll = ttk.Scrollbar(
            self.process_frame,
            orient=tk.VERTICAL,
            command=self.process_table.yview,
        )
        self.process_table.configure(yscrollcommand=scroll.set)
        self.process_table.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

    def _build_stat_cards(self) -> None:
        self.cpu_values = {
            "Tiempo": tk.StringVar(value="--"),
            "Idle": tk.StringVar(value="--"),
            "Ocupado": tk.StringVar(value="--"),
            "Utilizacion": tk.StringVar(value="--"),
            "Rendimiento": tk.StringVar(value="--"),
            "Cambios contexto": tk.StringVar(value="--"),
        }
        cpu_card = ttk.LabelFrame(self.stats_frame, text="CPU", padding=(9, 6))
        cpu_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self._add_stat_rows(cpu_card, self.cpu_values)

        self.metric_values: Dict[str, Dict[str, tk.StringVar]] = {}
        for column, (key, title) in enumerate(
            (
                ("response", "Tiempo de respuesta"),
                ("turnaround", "Tiempo turnaround"),
                ("waiting", "Tiempo de espera"),
            ),
            start=1,
        ):
            values = {
                label: tk.StringVar(value="--")
                for label in ("Min", "Media", "Max", "Desviacion estandar")
            }
            self.metric_values[key] = values
            card = ttk.LabelFrame(
                self.stats_frame, text=title, padding=(9, 6)
            )
            card.grid(row=0, column=column, sticky="nsew", padx=3)
            self._add_stat_rows(card, values)

    @staticmethod
    def _add_stat_rows(
        card: ttk.LabelFrame, values: Dict[str, tk.StringVar]
    ) -> None:
        for row, (label, variable) in enumerate(values.items()):
            ttk.Label(card, text=label).grid(row=row, column=0, sticky="w")
            ttk.Label(card, textvariable=variable, font=("Segoe UI", 9, "bold")).grid(
                row=row, column=1, sticky="e", padx=(8, 0)
            )

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Abrir escenario...", command=self._open_scenario)
        file_menu.add_command(
            label="Guardar escenario como...", command=self._save_scenario
        )
        file_menu.add_separator()
        file_menu.add_command(label="Agregar proceso", command=self._open_add_dialog)
        file_menu.add_command(
            label="Quitar proceso seleccionado", command=self._remove_selected
        )
        file_menu.add_command(label="Limpiar procesos", command=self._clear_processes)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.destroy)
        menu_bar.add_cascade(label="Archivo", menu=file_menu)

        options_menu = tk.Menu(menu_bar, tearoff=False)
        algorithm_menu = tk.Menu(options_menu, tearoff=False)
        for label in _ALGORITHMS:
            algorithm_menu.add_radiobutton(
                label=label,
                variable=self.algorithm_var,
                value=label,
                command=self._algorithm_changed,
            )
        options_menu.add_cascade(label="Algoritmos", menu=algorithm_menu)

        speed_menu = tk.Menu(options_menu, tearoff=False)
        for label in _SPEEDS:
            speed_menu.add_radiobutton(
                label=label,
                variable=self.speed_var,
                value=label,
            )
        options_menu.add_cascade(label="Velocidad de simulacion", menu=speed_menu)
        options_menu.add_checkbutton(
            label="Mostrar/Ocultar procesos",
            variable=self.show_processes_var,
            command=self._toggle_process_list,
        )
        options_menu.add_separator()
        options_menu.add_command(
            label="Quantum de Round Robin...",
            command=self._set_quantum,
        )
        menu_bar.add_cascade(label="Opciones", menu=options_menu)
        self.root.config(menu=menu_bar)

    def _algorithm_changed(self) -> None:
        self._invalidate_result()

    def _toggle_process_list(self) -> None:
        if self.show_processes_var.get():
            self.process_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        else:
            self.process_frame.grid_remove()
        self._draw_current_result()

    def _set_quantum(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Quantum de Round Robin")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        ttk.Label(dialog, text="Ticks por turno:").grid(
            row=0, column=0, padx=12, pady=12
        )
        entry = ttk.Entry(dialog, textvariable=self.quantum_var, width=10)
        entry.grid(row=0, column=1, padx=12, pady=12)

        def save() -> None:
            try:
                if int(self.quantum_var.get()) <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Quantum invalido",
                    "El quantum debe ser un entero mayor que cero.",
                    parent=dialog,
                )
                return
            self._invalidate_result()
            dialog.destroy()

        ttk.Button(dialog, text="Aceptar", command=save).grid(
            row=1, column=0, columnspan=2, pady=(0, 12)
        )
        entry.focus_set()
        dialog.bind("<Return>", lambda _event: save())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def _open_add_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Agregar proceso")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        variables = {
            "Nombre": tk.StringVar(value="P{}".format(self._next_available_pid())),
            "Tiempo de llegada": tk.StringVar(value="0"),
            "Tiempo de CPU": tk.StringVar(value="5"),
            "Prioridad": tk.StringVar(value="0"),
            "Eventos E/S (CPU:duracion)": tk.StringVar(),
        }
        fields = list(variables.items())
        for row, (label, variable) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(
                row=row, column=0, sticky="w", padx=12, pady=5
            )
            ttk.Entry(dialog, textvariable=variable, width=22).grid(
                row=row, column=1, padx=12, pady=5
            )

        def add() -> None:
            try:
                process = Process(
                    pid=variables["Nombre"].get().strip(),
                    arrival_time=int(variables["Tiempo de llegada"].get()),
                    burst_time=int(variables["Tiempo de CPU"].get()),
                    priority=int(variables["Prioridad"].get()),
                    io_events=self._parse_io_events(
                        variables["Eventos E/S (CPU:duracion)"].get()
                    ),
                )
                existing = {
                    self.process_table.item(item, "values")[0]
                    for item in self.process_table.get_children()
                }
                if process.pid in existing:
                    raise ValueError(
                        "Ya existe un proceso llamado {}.".format(process.pid)
                    )
            except ValueError as error:
                messagebox.showerror("Datos invalidos", str(error), parent=dialog)
                return

            self._insert_process(process)
            self.show_processes_var.set(True)
            self._invalidate_result()
            self._toggle_process_list()
            dialog.destroy()

        buttons = ttk.Frame(dialog)
        buttons.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(buttons, text="Agregar", command=add).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Cancelar", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )
        dialog.bind("<Return>", lambda _event: add())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    @staticmethod
    def _parse_io_events(value: str) -> List[IOEvent]:
        if not value.strip():
            return []
        events = []
        for item in value.split(","):
            parts = item.strip().split(":")
            if len(parts) != 2:
                raise ValueError(
                    "Escribe cada E/S como CPU:duracion, por ejemplo 2:3, 5:1."
                )
            try:
                event = IOEvent(after_cpu=int(parts[0]), duration=int(parts[1]))
            except ValueError as error:
                raise ValueError(
                    "Cada E/S requiere ticks enteros positivos, por ejemplo 2:3, 5:1."
                ) from error
            if events and event.after_cpu <= events[-1].after_cpu:
                raise ValueError("Los eventos E/S deben estar en orden creciente.")
            events.append(event)
        return events

    @staticmethod
    def _format_io_events(events: List[IOEvent]) -> str:
        if not events:
            return "-"
        return ", ".join(
            "{}:{}".format(event.after_cpu, event.duration) for event in events
        )

    def _insert_process(self, process: Process) -> None:
        self.process_table.insert(
            "",
            tk.END,
            values=(
                process.pid,
                process.arrival_time,
                process.burst_time,
                process.priority,
                self._format_io_events(process.io_events),
            ),
        )

    def _open_scenario(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Abrir escenario",
            filetypes=(("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return
        try:
            processes = load_processes_file(path)
        except ValueError as error:
            messagebox.showerror("No se pudo abrir", str(error), parent=self.root)
            return

        for item in self.process_table.get_children():
            self.process_table.delete(item)
        for process in processes:
            self._insert_process(process)
        self.show_processes_var.set(True)
        self._invalidate_result()
        self._toggle_process_list()

    def _save_scenario(self) -> None:
        try:
            processes = self._processes_from_table()
            if not processes:
                raise ValueError("Agrega al menos un proceso antes de guardar.")
        except ValueError as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar escenario",
            defaultextension=".json",
            filetypes=(("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return
        try:
            save_processes_file(path, processes)
        except ValueError as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self.root)
            return
        messagebox.showinfo("Escenario guardado", path, parent=self.root)

    def _next_available_pid(self) -> int:
        current_ids = {
            self.process_table.item(item, "values")[0]
            for item in self.process_table.get_children()
        }
        while "P{}".format(self._next_pid) in current_ids:
            self._next_pid += 1
        return self._next_pid

    def _remove_selected(self) -> None:
        selected = self.process_table.selection()
        if not selected:
            messagebox.showinfo(
                "Selecciona un proceso",
                "Selecciona uno o mas procesos en la tabla.",
                parent=self.root,
            )
            return
        for item in selected:
            self.process_table.delete(item)
        self._invalidate_result()

    def _clear_processes(self) -> None:
        for item in self.process_table.get_children():
            self.process_table.delete(item)
        self._invalidate_result()

    def _processes_from_table(self) -> List[Process]:
        processes = []
        for item in self.process_table.get_children():
            pid, arrival, burst, priority, io_text = self.process_table.item(
                item, "values"
            )
            processes.append(
                Process(
                    pid=pid,
                    arrival_time=int(arrival),
                    burst_time=int(burst),
                    priority=int(priority),
                    io_events=self._parse_io_events(io_text.replace("/", ":"))
                    if io_text != "-"
                    else [],
                )
            )
        return processes

    def _toggle_playback(self) -> None:
        if self._playback_after is not None:
            self.root.after_cancel(self._playback_after)
            self._playback_after = None
            self.play_button.configure(text="▶")
            return

        if not self._create_result():
            return

        if self._playback_tick >= self._result.makespan:
            self._playback_tick = 0
        self.play_button.configure(text="❚❚")
        self._playback_step()

    def _create_result(self) -> bool:
        if self._result is not None:
            return True
        try:
            processes = self._processes_from_table()
            algorithm = _ALGORITHMS[self.algorithm_var.get()]
            quantum = int(self.quantum_var.get()) if algorithm == "rr" else 2
            scheduler = create_scheduler(algorithm, quantum=quantum)
            self._result = Simulator(scheduler).run(processes)
        except (ValueError, KeyError) as error:
            messagebox.showerror("No se pudo simular", str(error), parent=self.root)
            return False
        self._update_statistics(self._result)
        self._playback_tick = 0
        self._draw_current_result()
        self._show_timeline_tick(0)
        return True

    def _playback_step(self) -> None:
        if self._result is None:
            return
        self._playback_tick += 1
        self._show_timeline_tick(self._playback_tick)
        if self._playback_tick >= self._result.makespan:
            self._playback_after = None
            self.play_button.configure(text="▶")
            return
        self._playback_after = self.root.after(
            _SPEEDS[self.speed_var.get()], self._playback_step
        )

    def _step_timeline(self, amount: int) -> None:
        if self._result is None:
            if not self._create_result():
                return
        self._stop_playback()
        self._show_timeline_tick(
            max(0, min(self._result.makespan, self._playback_tick + amount))
        )

    def _reset_playback(self) -> None:
        self._stop_playback()
        if self._result is not None:
            self._show_timeline_tick(0)

    def _select_timeline_tick(self, event: tk.Event) -> None:
        if self._result is None:
            return
        self._stop_playback()
        scale = self._timeline_scale(self._result.makespan)
        x = self.gantt_canvas.canvasx(event.x)
        tick = int((x - 88) / scale)
        self._show_timeline_tick(max(0, min(self._result.makespan, tick)))

    def _show_timeline_tick(self, tick: int) -> None:
        if self._result is None:
            return
        self._playback_tick = tick
        self._draw_playback_cursor()
        self._update_timeline_info()

    def _update_timeline_info(self) -> None:
        if self._result is None:
            return
        snapshot = self._result.timeline[self._playback_tick]

        def display_queue(processes: Tuple[str, ...]) -> str:
            return ", ".join(processes) if processes else "-"

        self.timeline_info_var.set(
            "t={}: CPU {} | Listos: {} | Bloqueados: {} | Nuevos: {} | "
            "Terminados: {}".format(
                snapshot.time,
                snapshot.running or "ociosa",
                display_queue(snapshot.ready),
                display_queue(snapshot.blocked),
                display_queue(snapshot.new),
                display_queue(snapshot.terminated),
            )
        )

    def _on_segment_enter(self, _event: tk.Event, detail: str) -> None:
        self.timeline_info_var.set(detail)

    def _on_segment_leave(self, _event: tk.Event) -> None:
        self._update_timeline_info()

    def _invalidate_result(self) -> None:
        self._stop_playback()
        self._result = None
        self._playback_tick = 0
        self._clear_statistics()
        self.timeline_info_var.set("Ejecuta la simulacion para consultar las colas.")
        self._draw_empty_state()

    def _stop_playback(self) -> None:
        if self._playback_after is not None:
            self.root.after_cancel(self._playback_after)
            self._playback_after = None
        self.play_button.configure(text="▶")

    def _clear_statistics(self) -> None:
        for variable in self.cpu_values.values():
            variable.set("--")
        for values in self.metric_values.values():
            for variable in values.values():
                variable.set("--")

    def _update_statistics(self, result: SimulationResult) -> None:
        self.cpu_values["Tiempo"].set(str(result.makespan))
        self.cpu_values["Idle"].set(str(result.cpu_idle_time))
        self.cpu_values["Ocupado"].set(str(result.cpu_busy_time))
        self.cpu_values["Utilizacion"].set(
            "{}%".format(_format_stat(result.cpu_utilization))
        )
        self.cpu_values["Rendimiento"].set(
            "{}/tick".format(_format_stat(result.throughput))
        )
        self.cpu_values["Cambios contexto"].set(str(result.context_switches))

        metrics = {
            "response": [process.response_time for process in result.processes],
            "turnaround": [process.turnaround_time for process in result.processes],
            "waiting": [process.waiting_time for process in result.processes],
        }
        for key, values in metrics.items():
            minimum, average, maximum, deviation = _statistics(values)
            for label, value in (
                ("Min", minimum),
                ("Media", average),
                ("Max", maximum),
                ("Desviacion estandar", deviation),
            ):
                self.metric_values[key][label].set(_format_stat(value))

    def _draw_empty_state(self) -> None:
        canvas = self.gantt_canvas
        canvas.delete("all")
        hint = (
            "Agrega procesos desde Archivo > Agregar proceso y pulsa ▶."
            if not self.process_table.get_children()
            else "Pulsa ▶ para iniciar la simulacion."
        )
        canvas.create_text(
            24,
            30,
            anchor=tk.NW,
            text=hint,
            fill="#666666",
            font=("Segoe UI", 11),
        )
        canvas.configure(scrollregion=(0, 0, 900, 120))

    def _draw_current_result(self) -> None:
        if self._result is None:
            return
        self._draw_timeline(self._result)
        self._draw_playback_cursor()
        self._update_timeline_info()

    def _on_canvas_resize(self, _event: tk.Event) -> None:
        if self._result is not None:
            self._draw_current_result()
        elif not self.process_table.get_children():
            self._draw_empty_state()

    def _draw_timeline(self, result: SimulationResult) -> None:
        canvas = self.gantt_canvas
        canvas.delete("all")
        if not result.gantt:
            return

        left = 88
        scale = self._timeline_scale(result.makespan)
        chart_width = left + result.makespan * scale + 15
        row_height = 30
        chart_top = 34
        row_count = 1 + len(result.processes)
        chart_bottom = chart_top + row_count * row_height
        label_step = max(1, math.ceil(result.makespan / 60))

        canvas.create_text(
            10, chart_top + row_height / 2, text="CPU", anchor=tk.W, font=("Segoe UI", 9, "bold")
        )
        for process_index, process in enumerate(result.processes, start=1):
            y = chart_top + process_index * row_height + row_height / 2
            canvas.create_text(
                10, y, text=process.pid, anchor=tk.W, font=("Segoe UI", 9, "bold")
            )

        time_marks = list(range(0, result.makespan + 1, label_step))
        if time_marks[-1] != result.makespan:
            time_marks.append(result.makespan)
        for tick in time_marks:
            x = left + tick * scale
            canvas.create_line(x, 20, x, chart_bottom, fill="#dddddd")
            canvas.create_text(
                x + 2, 8, text=str(tick), anchor=tk.NW, font=("Segoe UI", 8)
            )

        for segment in result.gantt:
            x1 = left + segment.start * scale
            x2 = left + segment.end * scale
            color = "#c8c8c8" if segment.pid is None else _STATES["Ejecucion"]
            detail_tag = "cpu-{}-{}".format(segment.start, segment.end)
            canvas.create_rectangle(
                x1,
                chart_top,
                x2,
                chart_top + row_height - 1,
                fill=color,
                outline="white",
                tags=(detail_tag,),
            )
            canvas.tag_bind(
                detail_tag,
                "<Enter>",
                lambda event, value=segment: self._on_segment_enter(
                    event,
                    "CPU: {} en ticks {}-{}".format(
                        value.pid or "Idle", value.start, value.end
                    ),
                ),
            )
            canvas.tag_bind(
                detail_tag,
                "<Leave>",
                lambda event: self._on_segment_leave(event),
            )
            canvas.create_text(
                (x1 + x2) / 2,
                chart_top + row_height / 2,
                text="Idle" if segment.pid is None else segment.pid,
                fill="#222222" if segment.pid is None else "white",
                font=("Segoe UI", 8, "bold"),
            )

        running_by_tick: List[Optional[str]] = [None] * result.makespan
        for segment in result.gantt:
            for tick in range(segment.start, segment.end):
                running_by_tick[tick] = segment.pid

        for process_index, process in enumerate(result.processes, start=1):
            y1 = chart_top + process_index * row_height
            states = self._process_states(process, result, running_by_tick)
            for state, start, end in self._state_intervals(states):
                x1 = left + start * scale
                x2 = left + end * scale
                detail_tag = "state-{}-{}-{}".format(process.pid, start, end)
                canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y1 + row_height - 1,
                    fill=_STATES[state],
                    outline="white",
                    tags=(detail_tag,),
                )
                canvas.tag_bind(
                    detail_tag,
                    "<Enter>",
                    lambda event, pid=process.pid, value=state, begin=start, finish=end: self._on_segment_enter(
                        event,
                        "{}: {} en ticks {}-{}".format(
                            pid, value, begin, finish
                        ),
                    ),
                )
                canvas.tag_bind(
                    detail_tag,
                    "<Leave>",
                    lambda event: self._on_segment_leave(event),
                )

        for process in result.processes:
            arrival_x = left + process.arrival_time * scale
            canvas.create_line(
                arrival_x,
                chart_top - 5,
                arrival_x,
                chart_bottom,
                fill="#718096",
                dash=(2, 3),
            )

        canvas.configure(scrollregion=(0, 0, chart_width, chart_bottom + 16))

    @staticmethod
    def _process_states(
        process: Process,
        result: SimulationResult,
        running_by_tick: List[Optional[str]],
    ) -> List[Optional[str]]:
        completion_time = process.completion_time
        if completion_time is None:
            raise ValueError("El proceso aun no ha terminado.")
        states: List[Optional[str]] = [None] * result.makespan
        blocked_intervals = SchedulerApp._io_block_intervals(process, result.gantt)

        for tick in range(process.arrival_time, completion_time):
            if any(start <= tick < end for start, end in blocked_intervals):
                states[tick] = "Bloqueado"
            elif running_by_tick[tick] == process.pid:
                states[tick] = "Ejecucion"
            else:
                states[tick] = "Listo"
        return states

    @staticmethod
    def _state_intervals(
        states: List[Optional[str]],
    ) -> List[Tuple[str, int, int]]:
        intervals: List[Tuple[str, int, int]] = []
        start = 0
        current = None
        for tick, state in enumerate(states + [None]):
            if state != current:
                if current is not None:
                    intervals.append((current, start, tick))
                current = state
                start = tick
        return intervals

    @staticmethod
    def _io_block_intervals(
        process: Process, gantt: List[GanttSegment]
    ) -> List[Tuple[int, int]]:
        intervals = []
        cpu_ticks = 0
        event_index = 0
        for segment in gantt:
            if segment.pid == process.pid:
                cpu_ticks += segment.end - segment.start
                while (
                    event_index < len(process.io_events)
                    and cpu_ticks >= process.io_events[event_index].after_cpu
                ):
                    event = process.io_events[event_index]
                    if cpu_ticks != event.after_cpu:
                        raise ValueError(
                            "No se encontro el evento de E/S para {}.".format(
                                process.pid
                            )
                        )
                    intervals.append((segment.end, segment.end + event.duration))
                    event_index += 1
        if event_index != len(process.io_events):
            raise ValueError("Faltan eventos de E/S para {}.".format(process.pid))
        return intervals

    @staticmethod
    def _io_block_time(process: Process, gantt: List[GanttSegment]) -> int:
        return SchedulerApp._io_block_intervals(process, gantt)[0][0]

    def _draw_playback_cursor(self) -> None:
        if self._result is None:
            return
        self.gantt_canvas.delete("playback_cursor")
        scale = self._timeline_scale(self._result.makespan)
        x = 88 + self._playback_tick * scale
        canvas_height = max(self.gantt_canvas.winfo_height(), 100)
        self.gantt_canvas.create_line(
            x,
            18,
            x,
            canvas_height,
            fill="#161616",
            width=2,
            tags="playback_cursor",
        )
        scroll_width = 88 + self._result.makespan * scale + 15
        view_width = self.gantt_canvas.winfo_width()
        scroll_to = max(0, x - view_width + 40)
        self.gantt_canvas.xview_moveto(min(1.0, scroll_to / max(1, scroll_width)))

    def _timeline_scale(self, makespan: int) -> int:
        visible_width = max(self.gantt_canvas.winfo_width() - 100, 400)
        return max(11, min(30, visible_width // min(makespan, 55)))


def launch_app() -> None:
    root = tk.Tk()
    SchedulerApp(root)
    root.mainloop()
