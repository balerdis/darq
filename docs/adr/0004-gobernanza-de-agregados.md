# ADR 0004 — Gobernanza de agregados

Estado: aceptada

## Contexto

DARQ existe para llevar contenido institucional que un producto público como Pegasus no puede embarcar por su cuenta — ver `docs/contrato-inclusion.md`. Eso implica que, tarde o temprano, alguien va a proponer agregar algo: un skill, un estándar, una política. Sin un dueño claro de esa decisión, DARQ termina acumulando contenido por inercia — cada área agrega lo suyo, nadie lo revisa contra un criterio común, y el conjunto deja de tener una identidad coherente.

## Decisión

La aceptación de agregados a DARQ está centralizada en el equipo de I+D: Pablo, Walter y Aníbal. Ninguna otra vía de incorporación es válida. El instrumento de esa revisión es `docs/contrato-inclusion.md`: el equipo de I+D lo aplica, no lo reinterpreta caso por caso.

### Qué trae quien propone

- El contenido en la forma que el motor espera — un skill, no una regla hardcodeada (ver `docs/contrato-inclusion.md` para el porqué).
- Para qué GO o para qué situación institucional resuelve algo, en concreto.
- Quién es el owner del contenido de acá en adelante — la persona o el equipo que responde si el contenido queda desactualizado o genera un problema.
- Confirmación de que no requiere ningún cambio de motor (ver ADR 0001 y ADR 0002).

### Qué evalúan los revisores

- Que el contenido sea institucional en el sentido del contrato de inclusión, y no una preferencia de equipo disfrazada de estándar.
- Que llegue en la forma correcta: un skill que el orquestador selecciona por relevancia, nunca una regla que el producto aplica sin importar el contexto.
- Que tenga un owner real, no un owner nominal.
- Que no abra una necesidad de cambio de motor — si la abre, la propuesta va primero a Pegasus, no a DARQ.

### Contenido llegado desde una GO es una contribución de primera clase

El caso fundacional de este modelo es el skill de OpenShift que va a aportar la GO de implementaciones (Ramiro): esa GO no programa, opera OpenShift directamente vía `oc`, y el estándar de versiones ASI no le aplica — es precisamente la razón por la que el contenido institucional tiene que llegar como skill que el orquestador elige por relevancia, y no como regla cableada en el producto para todo el mundo.

Ese aporte no es una excepción tolerada ni un favor que I+D le hace a otra GO: es una contribución igual en estatus a cualquiera que I+D proponga por su cuenta, evaluada contra el mismo contrato. La gobernanza descrita en este ADR no es real hasta que un agregado que vino de afuera de I+D — no propuesto ni escrito por I+D — atravesó el proceso completo y fue aceptado o rechazado con el mismo criterio que cualquier otro.

## Consecuencias

Centralizar la aceptación tiene un costo real y hay que decirlo así: cada agregado espera a que I+D lo revise, y eso es más lento que dejar que cada GO agregue lo suyo directamente. Ese costo compra dos cosas — coherencia de criterio a través del tiempo, y una única lista de responsables cuando algo del contenido institucional queda obsoleto o genera un problema. Sin ese gate, DARQ se vuelve tan heterogénea como los equipos que le agregan cosas, y la ADR 0002 — que DARQ no es un producto que crece por acumulación — deja de tener quién la haga cumplir.

## Referencias

Ver `docs/contrato-inclusion.md` para el criterio material de qué cuenta como contenido institucional, y ADR 0001 para la regla de que ningún agregado puede requerir un cambio de motor.
