# Manual de usuario

## 1. Propósito

El simulador permite crear procesos, elegir una política de planificación y
observar su ejecución en una CPU lógica. Presenta el diagrama temporal, los
estados de cada proceso, las colas en cada tick y estadísticas del resultado.

## 2. Requisitos e inicio

- **Desde la web:** abre el [simulador publicado en GitHub Pages](https://edinson99.github.io/Planificador-de-Procesos-de-CPU/). No requiere instalación; el cálculo ocurre en tu navegador.
- Windows 10/11.
- Python 3.9 o posterior, con Tkinter instalado.
- No requiere instalar paquetes de terceros.

En la versión web, agrega procesos o carga el ejemplo, selecciona un algoritmo,
y pulsa **Simular**. Puedes importar o exportar escenarios JSON, seleccionar
ticks desde el control de tiempo y usar los botones de reproducción. En los
eventos E/S, escribe `CPU:duración` y separa varios eventos con comas, por
ejemplo `2:3, 5:1`.

Desde el Explorador de archivos, haz doble clic en `iniciar_gui.bat`. También
puedes abrir PowerShell en la carpeta del proyecto y ejecutar:

```powershell
python src\main.py --gui
```

Para abrir la ventana sin mantener una consola visible:

```powershell
pythonw src\main.py --gui
```

## 3. Crear y administrar procesos

En **Archivo > Agregar proceso**, completa:

| Campo | Descripción |
| --- | --- |
| Nombre | Identificador único del proceso, por ejemplo `P1`. |
| Tiempo de llegada | Tick en que el proceso entra al sistema; debe ser cero o mayor. |
| Tiempo de CPU | Ráfaga total requerida; debe ser mayor que cero. |
| Prioridad | Número entero; los valores menores representan prioridad mayor. |
| Eventos E/S | Opcional. Usa `CPU:duracion`, separados por comas. |

Ejemplo: `2:3, 5:1` significa que el proceso se bloquea por 3 ticks después de
acumular 2 ticks de CPU y vuelve a bloquearse por 1 tick después de acumular
5 ticks de CPU. Los tiempos `CPU` deben estar en orden creciente y ser menores
que la ráfaga total.

La tabla de procesos se puede mostrar u ocultar desde **Opciones >
Mostrar/Ocultar procesos**. Para quitar procesos, selecciónalos en la tabla y
usa **Archivo > Quitar proceso seleccionado**. **Limpiar procesos** elimina
toda la lista.

## 4. Elegir algoritmo y quantum

Abre **Opciones > Algoritmos** y selecciona:

- **FIFO (No expropiable):** ejecuta en orden de llegada a Listo.
- **Menos tiempo primero (No expropiable):** elige la ráfaga original más corta.
- **SRTF (Expropiable):** elige el menor tiempo restante; puede interrumpir al
  proceso actual.
- **Round Robin (Expropiable):** reparte la CPU por turnos.
- **Prioridades (No expropiable):** elige la prioridad numérica más baja sin
  interrumpir el proceso actual.
- **Prioridades expropiativas:** interrumpe cuando llega un proceso con una
  prioridad numérica menor.

Para Round Robin, configura el quantum en **Opciones > Quantum de Round
Robin...**. Debe ser un entero positivo. Las velocidades en **Opciones >
Velocidad de simulación** cambian la rapidez de la animación, no el resultado.

## 5. Ejecutar y explorar

Pulsa **▶** para calcular y reproducir la simulación. También puedes:

- Usar **◀ Tick** y **Tick ▶** para retroceder o avanzar una unidad.
- Pulsar **Reiniciar** para volver al tick cero.
- Hacer clic sobre el gráfico para ir directamente a un tick.
- Pasar el cursor sobre un segmento para ver su proceso, estado e intervalo.

En cada tick, el texto bajo el gráfico muestra el proceso en ejecución y las
colas de Listos, Bloqueados, Nuevos y Terminados. El gráfico usa verde para
Bloqueado, cian para Listo y rojo para Ejecución; las líneas verticales señalan
las llegadas.

## 6. Leer las estadísticas

La tarjeta **CPU** informa duración total, ticks ociosos, ticks ocupados,
utilización, rendimiento y cambios de contexto. Las otras tarjetas muestran
mínimo, media, máximo y desviación estándar de los tiempos de respuesta,
retorno y espera.

Las fórmulas y convenciones están en [Algoritmos y métricas](./algorithms.md).
En particular, no se añade tiempo de sobrecarga por cambio de contexto.

## 7. Abrir y guardar escenarios

Usa **Archivo > Abrir escenario...** para cargar una lista JSON y
**Archivo > Guardar escenario como...** para exportarla. El archivo debe estar
codificado en UTF-8. Ejemplo:

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
    "priority": 1,
    "io_events": []
  }
]
```

`io_events` puede ser una lista vacía. Cada evento requiere `after_cpu` y
`duration`, ambos enteros positivos. El formato anterior de un único bloqueo
(`io_after` y `io_duration`) también se puede abrir.

## 8. Usar la consola

Desde la raíz del proyecto:

```powershell
python src\main.py
python src\main.py --algorithm srtf
python src\main.py --algorithm priority_preemptive
python src\main.py --algorithm rr --quantum 2
python src\main.py --algorithm rr --quantum 2 --input procesos.json
```

Los algoritmos aceptados son `fcfs`, `sjf`, `srtf`, `rr`, `priority` y
`priority_preemptive`. Round Robin requiere `--quantum`.

## 9. Solución de problemas

- **No aparece la ventana:** verifica que Python esté instalado y que Tkinter
  esté incluido en esa instalación. Prueba `python src\main.py --gui` para ver
  posibles mensajes en la consola.
- **No se inicia la simulación:** agrega al menos un proceso y revisa que PID,
  llegada, ráfaga, prioridad y E/S sean válidos.
- **No se puede abrir un JSON:** comprueba que contenga una lista no vacía, que
  los PID sean únicos y que cada evento de E/S tenga los campos requeridos.
- **El quantum no se acepta:** debe ser un entero mayor que cero.

