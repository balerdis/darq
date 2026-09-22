# ADR 0005 — DARQ es un fork completo, no una distribución

Estado: aceptada. Supera a `docs/adr/0001-distribucion-no-fork.md`, que declaraba la decisión
inversa.

## Contexto

`docs/adr/0001-distribucion-no-fork.md` —vigente desde el 7 de septiembre hasta el 22 de septiembre
de 2026— declaró que DARQ sería una distribución: consumiría un release publicado y fijado de
Pegasus Harness,
tomado como artifact de binario y no como código fuente, aportando sólo `identity.json`, contenido
propio y las herramientas de build que lo empaquetaban contra ese binario fijado. El repositorio de
DARQ no contenía una sola línea de motor, y un guardián (`tools/check_no_engine_code.py`) lo
verificaba: nada bajo `core/`, `ports/`, `adapters/`, `infra/` ni `tui/` podía existir en el árbol de
DARQ.

Ese modelo funcionó mientras DARQ fue, sobre todo, contenido: skills, prompts y agentes montados
sobre un motor ajeno. Pero el costo que la ADR original ya anticipaba en su sección de consecuencias
—"DARQ no puede arreglar un bug de motor con su propio calendario"— dejó de ser aceptable a medida
que la DGISIS necesitó evolucionar el motor mismo, no sólo el contenido que corre sobre él: cambios
de comportamiento, no sólo de marca o de skills, con un calendario propio de la organización y sin
depender de la cola de trabajo, el criterio de release ni los tiempos de otro proyecto.

## Decisión

DARQ pasa a ser un fork completo de Pegasus Harness. El repositorio de DARQ tiene su propia copia
del motor bajo `src/darq/` — `core/`, `ports/`, `adapters/`, `infra/`, `tui/` incluidos — y la
evoluciona con su propio calendario. Esto revierte, punto por punto, lo que
`docs/adr/0001-distribucion-no-fork.md` establecía:

- **`engine.pin` se retira.** No hay un release ajeno fijado por tag y hash que consumir: el motor
  vive en este repositorio y se versiona junto con el resto del código.
- **El rebrand en tiempo de build se retira.** La identidad de producto (`src/darq/identity.json`)
  sigue siendo un dato de arranque, no una rama de código — eso no cambió, y sigue siendo un
  mecanismo genuino del motor, no un artefacto del modelo de distribución anterior — pero ya no hay
  una transformación de texto aplicada sobre un árbol ajeno en el momento de empaquetar: el árbol
  que se transforma es el propio.
- **Los scripts de distribución específicos del modelo de release-ajeno-fijado se retiran.** Lo que
  queda es lo que cualquier fork del motor necesita para construir su propio release — herramientas
  como `tools/build_zipapp.py` siguen existiendo porque siguen siendo necesarias para publicar el
  binario de DARQ, no porque sigan atadas a un pin externo.
- **`tools/check_no_engine_code.py` se retira.** Ese guardián existía para demostrar, en CI local,
  que el árbol de DARQ no tenía motor propio. Esa propiedad dejó de ser el objetivo: ahora sí lo
  tiene, deliberadamente.

Inicialmente, ambas bases —Pegasus Harness y DARQ— se mantienen muy parecidas. Los cambios genéricos
que se desarrollan en Pegasus se transportan a mano a DARQ, caso por caso (merge, cherry-pick o
port, según convenga), sin ninguna automatización. No hay una obligación de mantener paridad
perfecta: las dos bases pueden divergir progresivamente a medida que DARQ incorpora necesidades
institucionales que no tienen sentido en un producto genérico.

## Consecuencias

Lo que se gana: DARQ puede corregir, extender o adaptar el motor con su propio calendario, sin
esperar un release ajeno. Una necesidad institucional que antes hubiera requerido convencer a otro
proyecto de que le convenía a él también, ahora simplemente se implementa.

El costo, dicho sin vueltas: cada corrección genérica que se hace en Pegasus tiene que transportarse
a mano a DARQ para que DARQ se beneficie de ella, y viceversa no aplica — un cambio institucional de
DARQ no vuelve a Pegasus salvo que alguien decida explícitamente proponerlo ahí. Sin automatización
de por medio, ese transporte depende de que alguien lo note, lo evalúe y lo aplique; nada lo obliga.
Con el tiempo, y sin ese esfuerzo activo, las dos bases van a divergir cada vez más — eso es lo
esperado, no un fallo del modelo.

## Referencias

- `docs/contrato-inclusion.md` — qué contenido institucional entra en DARQ ahora que no depende de
  una decisión de alcance tomada en otro proyecto.
- `https://github.com/balerdis/pegasus-harness` — el repositorio de origen del que DARQ es fork.
