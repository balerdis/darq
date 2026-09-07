# ADR 0001 — DARQ es una distribución, no un fork

Estado: aceptada

## Contexto

DARQ necesita el motor de Pegasus para funcionar: el CLI, el instalador, el journal de ownership, los adapters por cliente. Ninguna de esas piezas es específica de la DGISIS y ninguna vale la pena mantener por segunda vez. Pegasus 5.18.0 agregó soporte de distribución: un tercero puede construir su propio binario a partir de un release publicado y fijado, aportando su propio `identity.json` y su propio contenido, sin tocar código de motor.

La alternativa obvia era la de siempre: clonar el repositorio, cambiarle el nombre y empezar a divergir. Eso resuelve el problema de hoy y crea uno más caro mañana — dos copias de `core/`, `ports/`, `adapters/`, `infra/` y `tui/` que hay que mantener sincronizadas a mano, y que dejan de estarlo apenas nadie mira.

## Decisión

DARQ consume un release de Pegasus publicado, en una versión fija, tomado como artifact de binario y no como código fuente. El repositorio de DARQ no contiene una sola línea de motor: no hay `core/`, no hay `ports/`, no hay `adapters/`, no hay `infra/`, no hay `tui/`. Lo que DARQ aporta es `identity.json`, contenido propio y las herramientas de build que lo empaquetan contra el binario fijado.

Regla en forma verificable, no de intención:

> Ningún archivo bajo `core/`, `ports/`, `adapters/`, `infra/` o `tui/` existe en el árbol de DARQ. `tools/check_no_engine_code.py` lo confirma: no hay CI en este ecosistema — una decisión deliberada, igual que en el motor, que tampoco la tiene — así que el guardia corre localmente, a mano o desde `tools/check.sh`, con el alcance de archivos que reporta `git`, no una lista fija. Aplica tres chequeos independientes — nombres de directorio de capa de motor, nombres de archivo de contenido conocidos del motor, y cualquier archivo Python que importe el paquete del motor — y falla la build si alguno encuentra algo.

Si DARQ necesita un cambio de motor — una capacidad nueva, un bug corregido, un adapter distinto — el único camino es: corregirlo en Pegasus, cortar un release de Pegasus, y actualizar el pin en DARQ. No hay atajo local.

### El pin

El pin identifica el release consumido con dos datos, no uno: el tag de Pegasus y el SHA-256 de cada asset consumido de ese release. El tag dice *qué versión*; el hash dice *que el artifact que se está usando es, byte a byte, el que ese tag publicó* — protege contra un tag remplazado o un artifact corrompido en tránsito, no solo contra un número de versión equivocado.

Actualizar el pin es deliberadamente un diff de un solo archivo: el tag y los hashes cambian, nada más se toca en el mismo commit. Eso lo vuelve trivial de revisar — un reviewer no tiene que leer un diff de motor para aprobar una actualización de pin, solo tiene que confirmar que el hash corresponde al release que dice ser.

## Consecuencias

Lo que se gana: DARQ no puede volverse una copia divergente de Pegasus, porque no tiene código de motor que divergir. Cada bug de motor se corrige una sola vez, en un solo lugar, y todas las distribuciones lo reciben al bumpear el pin. La superficie que un contribuidor de DARQ necesita entender para aportar contenido institucional es pequeña: no incluye el motor.

El costo, dicho sin vueltas: DARQ no puede arreglar un bug de motor con su propio calendario. Si algo en el instalador o en un adapter afecta a DARQ, la corrección pasa por Pegasus primero — su cola de trabajo, su criterio de release, sus tiempos. Esa lentitud no es un defecto del diseño: es el mecanismo mismo que impide la divergencia. Un camino rápido para saltarse el pin sería, exactamente, la puerta por la que DARQ empezaría a convertirse en un fork.

## Referencias

Ver `docs/contrato-inclusion.md` para el criterio de qué contenido entra en DARQ una vez que el motor está fijado por este ADR.
