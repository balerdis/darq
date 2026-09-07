# ADR 0002 — DARQ es marca y contenido, no un segundo producto

Estado: aceptada

## Contexto

Una vez que DARQ tiene su propio binario, su propio nombre y su propia identidad visual, aparece una tentación natural: ya que estamos, agreguemos también un comando propio, una capacidad propia, algo que el Pegasus genérico no tiene. Ceder a esa tentación convierte a DARQ en un segundo producto que hay que diseñar, versionar y mantener por su cuenta — exactamente lo que la ADR 0001 evita del lado del motor, reaparecido del lado de las capacidades.

## Decisión

DARQ es una marca y un conjunto de contenido. No reimplementa, envuelve ni extiende capacidades del motor; no agrega comandos que el motor no tenga.

El paralelo es exacto y vale decirlo así: esto es arquitectura hexagonal aplicada un nivel más arriba. Pegasus conoce el *contrato* de una raíz de contenido válida — una forma que `identity.json` y el árbol de contenido deben cumplir — y no puede conocer, ni necesita conocer, quién la implementa. De la misma manera que `core/` no puede mencionar el nombre de un CLI, el motor de Pegasus no puede mencionar el nombre de una distribución.

La palabra DARQ no aparece en ningún lugar del código fuente, los tests, la documentación ni las specs de Pegasus. Eso no es una coincidencia que se sostiene sola: es una propiedad que hay que preservar activamente, de la misma forma en que la regla "ningún módulo fuera de `adapters/` puede mencionar el nombre de un CLI" se sostiene con un test, no con buena voluntad. Forma sí, identidad nunca.

## Consecuencias

La consecuencia práctica, y la que más disciplina exige: una funcionalidad que DARQ quiere para sí misma es una funcionalidad que Pegasus tiene que ganar para todos, o DARQ se queda sin ella. No hay una tercera vía donde DARQ la resuelve por su cuenta — eso reabriría exactamente el fork que la ADR 0001 cierra, esta vez a nivel de capacidades en lugar de a nivel de código.

Esto también fija un criterio de admisión útil para cualquier pedido futuro: si algo que DARQ necesita tiene sentido para cualquier distribución — no solo para la DGISIS — el pedido va a Pegasus como mejora de motor. Si algo tiene sentido solo para DARQ porque es identidad, contenido o configuración de marca, va en el repositorio de DARQ. Lo que no puede pasar es que DARQ resuelva localmente algo que en realidad es una capacidad de motor disfrazada de configuración.

## Referencias

Ver ADR 0001 para el mecanismo que mantiene el motor fijo y ADR 0003 para cómo esta misma disciplina de "forma sí, identidad nunca" se refleja en el nombre elegido para la distribución.
