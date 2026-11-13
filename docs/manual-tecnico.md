# Manual técnico

## 1. Alcance y arquitectura

El proyecto es un simulador local, determinista y de una sola CPU. La
simulación usa ticks lógicos; no crea procesos del sistema operativo ni depende
de esperas o hilos para calcular los resultados. La separación principal es:

| Capa | Responsabilidad |
| --- | --- |
| Modelo | Datos del proceso, eventos de E/S, estados y métricas individuales. |
| Planificación | Selección del siguiente proceso y decisión de expropiación. |
| Motor | Reloj lógico, colas, máquina de estados, Gantt e instantáneas. |
| Entrada/salida | Validación, carga y guardado de escenarios JSON. |
| Presentación | GUI Tkinter y CLI. |

## 2. Estructura del código

```text
src/
  main.py                       Entrada de CLI y GUI
  process_io.py                 Lectura y escritura de escenarios JSON
  engine/
    simulator.py                Simulador, resultado, Gantt e instantáneas
  models/
    process.py                  Process, IOEvent, ProcessState y métricas
  schedulers/
    base.py                     Interfaz y política de expropiación
    fcfs.py                     FCFS/FIFO
    sjf.py                      SJF no expropiativo
    srtf.py                     SRTF expropiativo
    round_robin.py              Round Robin
    priority.py                 Prioridades no expropiativas
    preemptive_priority.py      Prioridades expropiativas
  ui/
    app.py                      Aplicación Tkinter
tests/
  test_simulator.py             Pruebas originales de planificación
  test_advanced_simulation.py   Pruebas de nuevas políticas, E/S y JSON
  test_gui_logic.py             Pruebas de estadísticas y lógica del gráfico
docs/
  manual-usuario.md
  manual-tecnico.md
  algorithms.md
  state-diagram.md
```

## 3. Modelo de dominio

### `Process`

`Process` contiene el identificador, llegada, ráfaga de CPU, prioridad, tiempo
restante, estado, primer inicio, finalización y una lista de eventos `IOEvent`.
Los eventos usan:

- `after_cpu`: número acumulado de ticks de CPU ejecutados antes del bloqueo.
- `duration`: cantidad de ticks que permanece Bloqueado.

Los eventos deben estar en orden estrictamente creciente; `after_cpu` debe ser
menor que `burst_time`. Ambos valores son enteros positivos. Para compatibilidad,
el constructor todavía acepta `io_after`/`io_duration` como evento único.

`ProcessState` implementa las transiciones descritas en el
[diagrama de estados](./state-diagram.md). La espera individual se calcula como
`retorno - ráfaga de CPU - suma de duraciones de E/S`.

### Colas

- `ready`: lista ordenada según la política del planificador.
- `blocked_until`: tick en que cada proceso bloqueado vuelve a Listo.
- `current`: proceso que ocupa la CPU, o `None` si está ociosa.
- `next_io_event`: índice del siguiente evento de E/S pendiente por proceso.

## 4. Contrato de los planificadores

`Scheduler` define:

- `select_next(ready)`: retira y devuelve un proceso de la cola de Listos.
- `should_preempt(current, ready)`: indica si un proceso en Listos debe
  interrumpir al proceso actual. La implementación base devuelve `False`.
- `quantum`: límite de ticks por turno; solo Round Robin lo configura.

`create_scheduler(name, quantum)` centraliza la creación para CLI y GUI:

| Nombre | Política de selección | Expropiación |
| --- | --- | --- |
| `fcfs` | Primero en la cola Listo. | No |
| `sjf` | Menor ráfaga original. | No |
| `srtf` | Menor tiempo restante. | Sí, ante un tiempo restante estrictamente menor. |
| `rr` | Primero en la cola Listo. | Sí, al agotar el quantum. |
| `priority` | Menor número de prioridad. | No |
| `priority_preemptive` | Menor número de prioridad. | Sí, ante una prioridad estrictamente menor. |

Los empates en SRTF o prioridad no interrumpen al proceso actual. Cuando la CPU
está libre, los desempates se resuelven por llegada y orden estable de la cola.

## 5. Ciclo de simulación

En cada tick `t`, el motor:

1. Añade a Listos los procesos cuya llegada sea `t`.
2. Devuelve a Listos los procesos cuya E/S terminó en `t`.
3. Pregunta al planificador si debe expropiar el proceso actual.
4. Si la CPU está libre, selecciona un proceso de Listos y lo pasa a Ejecución.
5. Registra una `SimulationSnapshot` con CPU y colas en `t`.
6. Ejecuta un tick, actualiza tiempo restante y quantum.
7. Aplica la primera condición que corresponda: finalización, evento de E/S o
   agotamiento del quantum.

Si una llegada y una E/S completan al mismo tiempo, se encola primero la llegada
y después el proceso desbloqueado. Tras terminar la simulación se agrega una
instantánea final en `makespan`. La lista completa `SimulationResult.timeline`
permite reproducir y consultar las colas desde la GUI.

`GanttSegment` agrupa ticks contiguos con el mismo PID (incluida la CPU ociosa).
La GUI expande esos segmentos al representar los estados por tick.

## 6. Métricas

Para cada proceso:

- Retorno: `completion_time - arrival_time`.
- Espera: `turnaround_time - burst_time - blocked_time`.
- Respuesta: `first_start_time - arrival_time`.

Para el sistema:

- Tiempo ocupado: suma de duraciones Gantt con PID.
- Tiempo ocioso: `makespan - tiempo ocupado`.
- Utilización: `tiempo ocupado / makespan * 100`.
- Rendimiento: `cantidad de procesos / makespan`.
- Cambios de contexto: número de transiciones entre segmentos ocupados con
  PID distintos. Los periodos ociosos no cuentan; no se cobra tiempo extra por
  el cambio.
- Estadísticas de respuesta, retorno y espera: mínimo, media, máximo y
  desviación estándar poblacional.

## 7. Formato JSON

El archivo contiene una lista de procesos. Por ejemplo:

```json
[
  {
    "pid": "P1",
    "arrival_time": 0,
    "burst_time": 6,
    "priority": 2,
    "io_events": [
      {"after_cpu": 2, "duration": 3},
      {"after_cpu": 4, "duration": 1}
    ]
  }
]
```

`load_processes_file` valida estructura, tipos, PID únicos, eventos y reglas del
modelo. También acepta el esquema anterior con `io_after` y `io_duration`.
`save_processes_file` escribe UTF-8 indentado y serializa los eventos en
`io_events`.

## 8. Presentación

`src/main.py` selecciona la presentación. `--gui` inicia Tkinter; sin ese
indicador, la aplicación ejecuta la CLI. La GUI usa el motor existente, no
implementa una segunda versión del planificador. La reproducción anima una
simulación ya calculada y los controles por tick consultan `timeline`.

La CLI acepta:

```text
--algorithm fcfs|sjf|srtf|rr|priority|priority_preemptive
--quantum N        requerido para rr
--input ARCHIVO    escenario JSON opcional
--gui              iniciar la interfaz gráfica
```

## 9. Extender el proyecto

Para añadir un planificador:

1. Crear una subclase de `Scheduler` que implemente `select_next`.
2. Sobrescribir `should_preempt` si la política debe ser expropiativa.
3. Exportarla y agregar su nombre a `create_scheduler`.
4. Agregar la opción a la CLI y a `_ALGORITHMS` en `src/ui/app.py`.
5. Añadir pruebas deterministas del Gantt y de métricas para casos conocidos.
6. Actualizar [algorithms.md](./algorithms.md) y el manual de usuario.

## 10. Pruebas y ejecución local

No se requieren dependencias adicionales. Desde la raíz:

```powershell
python -m unittest discover -s tests -v
python src\main.py --algorithm srtf
python src\main.py --gui
```

