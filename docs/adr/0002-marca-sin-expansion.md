# ADR 0002 — DARQ es marca y contenido, no un segundo producto

Estado: aceptada

## Contexto

Una vez que DARQ tiene su propio binario, su propio nombre y su propia identidad visual, aparece una tentación natural: ya que estamos, agreguemos también un comando propio, una capacidad propia, algo que el Pegasus genérico no tiene. Ceder a esa tentación convierte a DARQ en un segundo producto que hay que diseñar, versionar y mantener por su cuenta — exactamente lo que la ADR 0001 evita del lado del motor, reaparecido del lado de las capacidades.

## Decisión

DARQ es una marca y un conjunto de contenido. No reimplementa, envuelve ni extiende capacidades del motor; no agrega comandos que el motor no tenga.

El paralelo es exacto y vale decirlo así: esto es arquitectura hexagonal aplicada un nivel más arriba. Pegasus conoce el *contrato* de una raíz de contenido válida — una forma que `identity.json` y el árbol de contenido deben cumplir — y no puede conocer, ni necesita conocer, quién la implementa. De la misma manera que `core/` no puede mencionar el nombre de un CLI, el *código* del motor de Pegasus no puede mencionar el nombre de una distribución — ni ramificar según él.

Hay que ser preciso sobre qué es lo que se preserva, porque la versión anterior de esta ADR afirmaba algo más fuerte y directamente falso: decía que «la palabra DARQ no aparece en ningún lugar del código fuente, los tests, la documentación ni las specs de Pegasus», y agregaba que eso se sostenía con un test. Ni una cosa ni la otra. DARQ aparece hoy en siete archivos de test del motor — `tests/test_catalog.py`, `tests/test_cli.py`, `tests/test_cli_upgrade.py`, `tests/test_upgrade.py`, `tests/test_identity.py`, `tests/test_tui_wordmark.py` y, bajo la forma `acme-darq`, `tests/test_filesystem.py` — y se la discute por nombre, largamente, en `docs/arquitectura/arquitectura.md`. Y no existe ningún test que prohíba esas apariciones; nunca existió.

Lo que sí es cierto, y es lo único a lo que esta ADR se compromete, es esto: **ningún módulo de `src/` del motor menciona a DARQ, y ningún comportamiento del motor se bifurca según el nombre de una distribución.** El motor lee una identidad y una raíz de contenido, y trata a las dos como datos: `identity.json` le dice cómo llamarse, el árbol de contenido le dice qué embarcar, y nada en el camino pregunta *cuál* distribución es la que está corriendo. Esa es la propiedad que hay que preservar activamente, del mismo modo en que la regla «ningún módulo bajo `core/` o `ports/` puede mencionar el nombre de un CLI» se sostiene con un test (`tests/test_core_is_cli_agnostic.py`) y no con buena voluntad.

Las apariciones de DARQ en los tests y en la documentación del motor son lo contrario de una filtración: son la evidencia de que el mecanismo de identidad es real y no teórico. Un motor que sólo se prueba contra su propia identidad no prueba nada — el fixture y el bug dirían la misma palabra por casualidad, que es exactamente el argumento que `tests/test_cli_identity_sweep.py` escribe en su propio docstring. Usar a DARQ como la segunda identidad de trabajo en los tests es lo que hace falsable la afirmación «el motor no sabe quién lo embarca». Forma sí, identidad nunca — pero «identidad nunca» es una regla sobre el *comportamiento* del motor, no sobre el vocabulario de sus tests.

## Consecuencias

La consecuencia práctica, y la que más disciplina exige: una funcionalidad que DARQ quiere para sí misma es una funcionalidad que Pegasus tiene que ganar para todos, o DARQ se queda sin ella. No hay una tercera vía donde DARQ la resuelve por su cuenta — eso reabriría exactamente el fork que la ADR 0001 cierra, esta vez a nivel de capacidades en lugar de a nivel de código.

Esto también fija un criterio de admisión útil para cualquier pedido futuro: si algo que DARQ necesita tiene sentido para cualquier distribución — no solo para la DGISIS — el pedido va a Pegasus como mejora de motor. Si algo tiene sentido solo para DARQ porque es identidad, contenido o configuración de marca, va en el repositorio de DARQ. Lo que no puede pasar es que DARQ resuelva localmente algo que en realidad es una capacidad de motor disfrazada de configuración.

## Limitación conocida

La afirmación que queda en pie no tiene hoy un guardián propio. `tests/test_core_is_cli_agnostic.py` prohíbe la cadena `opencode` bajo `core/` y `ports/` —es decir, cuida el eje del CLI, no el de la distribución— y `tests/test_cli_identity_sweep.py` prueba que la prosa del CLI, corrida bajo una identidad ajena y ficticia, nunca dice el nombre del motor. Ninguno de los dos prohíbe que el nombre de una distribución concreta aparezca en `src/`, ni que una rama del motor pregunte por él. La forma derivada del guardián sería barata —la misma técnica de subcadena que ya usa `test_core_is_cli_agnostic`, aplicada sobre todo `src/` y sobre los nombres de distribución conocidos—, pero escribirlo es una decisión del motor, no de esta distribución, y esta ADR no la toma: la deja nombrada acá para que la próxima persona que la lea sepa que la propiedad se sostiene hoy por inspección y no por un test.

## Referencias

Ver ADR 0001 para el mecanismo que mantiene el motor fijo y ADR 0003 para cómo esta misma disciplina de "forma sí, identidad nunca" se refleja en el nombre elegido para la distribución.
