# Simulador de Planificación de Procesos de CPU

Simulador educativo de planificación de CPU. Puedes usarlo desde el navegador
con [la versión web](https://edinson99.github.io/Planificador-de-Procesos-de-CPU/)
o ejecutar la aplicación Python de escritorio, ambas con un reloj lógico
determinista. Permite configurar procesos, ráfagas, prioridades y múltiples
eventos de entrada/salida (E/S), y observar el Gantt, los estados y las colas
en cada tick.

## Usar desde la web

Abre el [simulador web](https://edinson99.github.io/Planificador-de-Procesos-de-CPU/).
Agrega o importa procesos JSON, selecciona un algoritmo y pulsa **Simular**.
Puedes avanzar por ticks o reproducir la línea de tiempo; los cálculos se
realizan localmente en el navegador.

El sitio se publica automáticamente en GitHub Pages cuando hay cambios en
`web/` en la rama `main`. En la configuración del repositorio, selecciona
**Settings > Pages > Build and deployment > Source: GitHub Actions** si Pages
aún no está habilitado. El workflow valida las pruebas Python y web antes de
desplegar.

## Inicio rápido en Windows

1. Instala Python 3.9 o posterior con Tkinter.
2. Abre la carpeta del proyecto.
3. Haz doble clic en [`iniciar_gui.bat`](./iniciar_gui.bat).

También puedes iniciar la ventana desde PowerShell:

```powershell
python src\main.py --gui
```

La aplicación no requiere paquetes de terceros. Consulta el
[Manual de usuario](./docs/manual-usuario.md) para agregar procesos, configurar
algoritmos, explorar la línea de tiempo y trabajar con escenarios JSON.

## Funcionalidades

- FCFS/FIFO, SJF, SRTF, Round Robin y prioridades expropiativas o no
  expropiativas.
- Múltiples bloqueos por E/S para cada proceso.
- Gantt con estados por proceso, llegadas, reproducción, avance por tick y
  consulta de colas.
- Métricas de respuesta, espera y retorno; utilización, rendimiento y cambios
  de contexto.
- Importación y exportación de escenarios JSON desde la GUI.
- Simulador web estático con importación/exportación JSON y reproducción por tick.
- Interfaz de consola para ejecuciones rápidas y pruebas.

## Consola

Ejecuta el ejemplo FCFS:

```powershell
python src\main.py
```

Otros algoritmos:

```powershell
python src\main.py --algorithm sjf
python src\main.py --algorithm srtf
python src\main.py --algorithm priority
python src\main.py --algorithm priority_preemptive
python src\main.py --algorithm rr --quantum 2
```

Para ejecutar un escenario:

```powershell
python src\main.py --algorithm rr --quantum 2 --input procesos.json
```

## Formato de escenario JSON

El archivo contiene una lista de procesos. `io_events` es opcional; cada
elemento bloquea el proceso después de acumular `after_cpu` ticks de CPU y lo
mantiene bloqueado por `duration` ticks.

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
  },
  {
    "pid": "P2",
    "arrival_time": 1,
    "burst_time": 3,
    "priority": 1
  }
]
```

Los valores de `after_cpu` deben ser enteros positivos, estar en orden
creciente y ser menores que la ráfaga de CPU. Los escenarios existentes con
`io_after` y `io_duration` siguen siendo compatibles.

## Métricas y convenciones

- Retorno = finalización − llegada.
- Espera = retorno − ráfaga de CPU − tiempo total bloqueado.
- Respuesta = primer inicio de CPU − llegada.
- Utilización = ticks ocupados ÷ ticks totales × 100.
- Rendimiento = procesos terminados ÷ ticks totales.

Los cambios de contexto entre procesos se cuentan, pero no agregan tiempo de
sobrecarga al reloj lógico. Para las reglas completas consulta
[Algoritmos y métricas](./docs/algorithms.md) y el
[diagrama de estados](./docs/state-diagram.md).

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas cubren políticas preemptivas y no preemptivas, colas, E/S múltiple,
métricas, compatibilidad JSON y lógica de la interfaz.

## Documentación

- [Manual de usuario](./docs/manual-usuario.md): instalación, uso de la GUI y
  la CLI, algoritmos, escenarios y solución de problemas.
- [Manual técnico](./docs/manual-tecnico.md): arquitectura, modelo, motor,
  estrategias, métricas, JSON y guía de extensión.
- [Algoritmos y métricas](./docs/algorithms.md)
- [Estados de un proceso](./docs/state-diagram.md)

## Estructura del proyecto

```text
src/
  main.py                       Entrada de GUI y CLI
  process_io.py                 Carga y guardado de escenarios JSON
  engine/simulator.py           Reloj lógico, colas, Gantt e instantáneas
  models/process.py             Proceso, estados y eventos de E/S
  schedulers/                   Estrategias de planificación
  ui/app.py                     Interfaz gráfica Tkinter
tests/                          Pruebas automatizadas
docs/                           Manuales y documentación técnica
web/                            Simulador para GitHub Pages
```
