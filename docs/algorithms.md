# Algoritmos y metricas

## Estrategias implementadas

- **FCFS/FIFO:** ejecuta primero el proceso que lleva mas tiempo en Listo.
- **SJF:** elige la rafaga de CPU mas corta entre los procesos Listos. Es
  no expropiativo.
- **Round Robin:** asigna como maximo un quantum por turno y devuelve a Listo
  el proceso que no haya terminado.
- **Prioridades:** elige el menor valor numerico de prioridad; los empates se
  resuelven por llegada y orden de entrada. Es no expropiativo.

Las llegadas se agregan a Listo al inicio de cada tick. Si una llegada y el fin
de una E/S ocurren al mismo tiempo, se encolan primero las llegadas y despues
los procesos desbloqueados.

## Metricas

Para cada proceso:

- **Retorno (turnaround):** `tiempo de finalizacion - tiempo de llegada`.
- **Espera:** `retorno - rafaga de CPU - tiempo bloqueado`.
- **Respuesta:** `primer inicio de CPU - tiempo de llegada`.
- **Duracion de CPU:** la suma de sus ticks de ejecucion, `burst_time`.

Los promedios de espera y retorno son la media aritmetica de esas metricas para
todos los procesos. Las unidades corresponden a ticks logicos. El planificador
admite un evento opcional de E/S por proceso: `io_after` indica cuantos ticks
de CPU se ejecutan antes del bloqueo y `io_duration` cuantos ticks permanece
Bloqueado. Ambos valores deben proporcionarse juntos.
