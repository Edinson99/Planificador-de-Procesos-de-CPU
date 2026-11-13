# Simulador de Planificador de Procesos de CPU

Prototipo local en Python que simula la planificacion de procesos con un reloj
logico por ticks. La interfaz de consola esta separada del motor y de las
estrategias de planificacion.

## Requisitos

- Python 3.9 o posterior
- Sin dependencias externas

## Ejecucion

Desde la raiz del repositorio:

```powershell
python src\main.py
```

El ejemplo integrado ejecuta FCFS. Para elegir otro algoritmo:

```powershell
python src\main.py --algorithm sjf
python src\main.py --algorithm priority
python src\main.py --algorithm rr --quantum 2
```

Para cargar procesos desde un archivo JSON:

```powershell
python src\main.py --algorithm rr --quantum 2 --input procesos.json
```

Formato de entrada:

```json
[
  {"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 2},
  {
    "pid": "P2",
    "arrival_time": 1,
    "burst_time": 3,
    "priority": 1,
    "io_after": 1,
    "io_duration": 2
  }
]
```

`io_after` y `io_duration` son opcionales y deben aparecer juntos. `io_after`
indica despues de cuantos ticks de CPU el proceso pasa a Bloqueado; tras
`io_duration` ticks vuelve a Listo. Un numero de prioridad menor representa
mayor prioridad. FCFS, SJF y Prioridades son no expropiativos; Round Robin usa
el quantum indicado.

La salida muestra el diagrama de Gantt, los tiempos por proceso y los promedios.
Por ejemplo, una ejecucion FCFS puede producir:

```text
Gantt: 0 -- P1 -- 5 -- P2 -- 8
PID   Llegada  Rafaga  Inicio  Fin  Retorno  Espera  Respuesta
P1          0       5       0    5        5       0          0
P2          1       3       5    8        7       4          4
```

## Estructura

```text
src/
  engine/simulator.py       Motor y reloj logico
  models/process.py         Proceso, estados y metricas
  schedulers/               FCFS, SJF, Round Robin y Prioridades
  main.py                   Interfaz de consola
tests/                      Pruebas unitarias
docs/
  algorithms.md             Algoritmos y formulas
  state-diagram.md          Transiciones de estado
```

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

El motor no crea hilos ni espera tiempo real: cada tick representa una unidad
de tiempo simulada, por lo que los resultados son reproducibles.
