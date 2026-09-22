# ADR 0004 — Gobernanza de agregados

Estado: aceptada

## Contexto

DARQ existe para llevar contenido institucional que Pegasus Harness, como producto independiente y
genérico, no tiene motivo para embarcar por su cuenta — ver `docs/contrato-inclusion.md`. Eso
implica que, tarde o temprano, alguien va a proponer agregar algo: un skill, un estándar, una
política. Sin un dueño claro de esa decisión, DARQ termina acumulando contenido por inercia — cada
área agrega lo suyo, nadie lo revisa contra un criterio común, y el conjunto deja de tener una
identidad coherente.

## Decisión

Tanto Pegasus Harness como DARQ los mantiene el mismo usuario, que es quien tiene la última palabra
sobre qué entra en cada uno. El equipo institucional de la DGISIS propone cambios a DARQ por Pull
Request; el usuario los revisa contra `docs/contrato-inclusion.md` y decide si los acepta.

Esto es deliberadamente simple, y se mantiene así a propósito mientras un solo mantenedor alcanza a
revisar cada propuesta: no hay un equipo de revisión separado, no hay permisos de merge delegados, y
no se asume que quien propone tenga acceso directo de escritura al repositorio. Más adelante, si el
volumen de propuestas lo justifica, el usuario podría otorgar permisos directos de mantenimiento a
personas del equipo institucional — pero esa es una decisión pendiente y esta ADR no la toma ni la
diseña de antemano.

### Qué trae quien propone

- El contenido en la forma que el motor espera — un skill, no una regla hardcodeada (ver
  `docs/contrato-inclusion.md` para el porqué).
- Para qué GO o para qué situación institucional resuelve algo, en concreto.
- Quién es el owner del contenido de acá en adelante — la persona o el equipo que responde si el
  contenido queda desactualizado o genera un problema.

### Qué evalúa el usuario al revisar el Pull Request

- Que el contenido sea institucional en el sentido del contrato de inclusión, y no una preferencia
  de equipo disfrazada de estándar.
- Que llegue en la forma correcta: un skill que el orquestador selecciona por relevancia, nunca una
  regla que el producto aplica sin importar el contexto.
- Que tenga un owner real, no un owner nominal.

### Contenido llegado desde una GO es una contribución de primera clase

El caso fundacional de este modelo es el skill de OpenShift que puede aportar la GO de
implementaciones: esa GO no programa, opera OpenShift directamente vía `oc`, y el estándar de
versiones ASI no le aplica — es precisamente la razón por la que el contenido institucional tiene
que llegar como skill que el orquestador elige por relevancia, y no como regla cableada en el
producto para todo el mundo.

Ese aporte no es una excepción tolerada: es un Pull Request evaluado contra el mismo contrato que
cualquier otro, venga de donde venga.

## Consecuencias

Centralizar la decisión final en una sola persona tiene un costo real y hay que decirlo así: cada
agregado espera a que el usuario lo revise, y eso es más lento que dejar que cada GO lo incorpore
directamente. Ese costo compra coherencia de criterio a través del tiempo mientras el volumen de
propuestas sigue siendo chico. Si ese volumen crece al punto de que revisar cada Pull Request deja
de ser sostenible para una sola persona, esta ADR va a necesitar revisarse — pero diseñar esa
gobernanza más compleja de antemano, sin la necesidad concreta delante, es exactamente lo que este
documento evita hacer.

## Referencias

Ver `docs/contrato-inclusion.md` para el criterio material de qué cuenta como contenido
institucional.
