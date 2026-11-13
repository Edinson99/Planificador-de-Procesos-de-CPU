# Algoritmos y metricas

## Estrategias implementadas

- **FCFS/FIFO:** ejecuta primero el proceso que lleva mas tiempo en Listo.
- **SJF:** selecciona la rafaga original mas corta y no expropia la CPU.
- **SRTF:** elige el menor tiempo restante y expropia cuando llega un proceso
  con menos tiempo restante. En empates, el proceso actual continua.
- **Round Robin:** asigna como maximo un quantum por turno y devuelve a Listo
  el proceso que no haya terminado.
- **Prioridades no expropiativas:** elige el menor valor numerico; los empates
  se resuelven por llegada y orden de entrada.
- **Prioridades expropiativas:** interrumpe el proceso actual cuando llega uno
  con un numero de prioridad menor. En empate, el actual continua.

Las llegadas se agregan a Listo al inicio de cada tick. Si una llegada y el fin
de una E/S ocurren al mismo tiempo, se encolan primero las llegadas y despues
los procesos desbloqueados.

## Solicitudes de E/S

Un proceso puede realizar cero o mas solicitudes de E/S. Cada evento se define
por la cantidad acumulada de ticks de CPU ejecutados y la duracion del bloqueo:

```json
{
  "pid": "P1",
  "arrival_time": 0,
  "burst_time": 6,
  "io_events": [
    {"after_cpu": 2, "duration": 3},
    {"after_cpu": 4, "duration": 1}
  ]
}
```

`after_cpu` debe ser positivo, menor que la rafaga total y estar en orden
estrictamente creciente. El formato anterior `io_after`/`io_duration` se sigue
aceptando para escenarios existentes.

## Metricas

Por proceso:

- **Retorno (turnaround):** `finalizacion - llegada`.
- **Espera:** `retorno - rafaga de CPU - suma de duraciones de E/S`.
- **Respuesta:** `primer inicio de CPU - llegada`.
- **Duracion de CPU:** suma de sus ticks de ejecucion.

Metricas del sistema:

- **Utilizacion de CPU:** `ticks ocupados / ticks totales * 100`.
- **Rendimiento (throughput):** `cantidad de procesos / ticks totales`.
- **Cambios de contexto:** cambios entre dos procesos distintos ejecutados
  consecutivamente; los periodos ociosos no cuentan como cambio entre procesos.
- **Desviacion estandar:** desviacion poblacional de las metricas por proceso.

Las unidades son ticks logicos. Las colas se guardan en una instantanea al
inicio de cada tick y otra al terminar la simulacion, para permitir inspeccion
y reproduccion paso a paso. Los cambios de contexto se contabilizan, pero no
se agrega un costo de tiempo por cambio al modelo de CPU.
