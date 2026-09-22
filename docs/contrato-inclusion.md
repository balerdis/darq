# Contrato de inclusión de DARQ

Este documento fija qué contenido institucional entra en DARQ y con qué forma.

## Qué cambió con el fork, y por qué este contrato ya no argumenta lo mismo

Hasta el 2026-09-22, DARQ era una distribución: consumía un release fijado de Pegasus Harness y le
aplicaba un rebrand de texto en tiempo de build. En ese modelo, el argumento central de este
documento era de **alcance ajeno**: Pegasus, como producto público de uso general, retiraba de su
release ciertas piezas de contenido —el estándar de versiones ASI, la guía de seguridad Laravel—
porque no tenía por qué embarcar de fábrica la política interna de una organización particular, y
DARQ existía, en parte, para ser el lugar donde ese contenido retirado sí encontraba casa.

Ese argumento ya no aplica tal como estaba escrito. DARQ es hoy un fork completo, con su propia
copia del motor bajo `src/darq/`. No hay un release ajeno cuyo alcance haya que respetar ni
esquivar: el contenido de este repositorio vive acá porque quien lo mantiene decide que vive acá,
sin necesidad de invocar una decisión de alcance tomada en otro proyecto. Pegasus Harness
(`https://github.com/balerdis/pegasus-harness`) sigue existiendo como producto independiente y
genérico, y su propio contrato de inclusión sigue resolviendo qué entra en *su* release público —
pero ya no es el otro lado de una ecuación que DARQ tenga que completar. Son, simplemente, dos
proyectos separados, cada uno con su propio criterio.

Lo que sí se conserva, porque seguía siendo válido independientemente del modelo de distribución,
es lo siguiente: qué cuenta como contenido institucional, la forma no negociable en la que ese
contenido tiene que entrar (skill elegido por relevancia, nunca regla incondicional), y la exigencia
de procedencia y owner nombrado. Eso no dependía de que DARQ fuera una distribución — depende de
cómo se gobierna un cuerpo de contenido institucional, y sigue aplicando igual en un fork.

## Qué califica como contenido institucional para la DGISIS

Específico de la organización: fuera de ella no tiene sentido genérico.

- Estándares de tecnología propios (el caso fundacional: el estándar de versiones ASI).
- Skills de operación de infraestructura propia de una GO (el caso en curso: operar OpenShift vía
  `oc`, aportado por la GO de implementaciones).
- Guía técnica genérica que la organización decide sostener para sus propios equipos aunque no sea
  exclusiva de la DGISIS — el caso presente es seguridad Laravel: es guía aplicable a cualquier
  equipo que use el framework, y lo único propio de la organización que tiene es su `author`. Entra
  porque acá hay equipos que trabajan con Laravel y alguien tiene que mantenerla para ellos, no
  porque sea contenido exclusivo de la DGISIS.
- Cualquier contenido futuro con ese perfil: útil puertas adentro, con o sin equivalente genérico
  afuera.

La pregunta que separa esto de una preferencia de equipo disfrazada de estándar es: ¿tiene un owner
nombrado que responde por él en el tiempo, y una situación institucional concreta que resuelve? Si
no, no entra, sin importar su calidad.

## La forma es no negociable: skill elegido por relevancia, nunca regla hardcodeada

Un estándar institucional entra a DARQ como un skill que el orquestador elige según el contexto de
la tarea — nunca como una regla que el producto aplica de forma incondicional a todo el mundo.

La razón no es de preferencia de diseño, es organizacional: la GO de implementaciones opera
OpenShift directamente y no programa. El estándar de versiones ASI no le aplica, y no tiene sentido
que le aplique — no hay versión de framework que homologar cuando el trabajo es administrar
clústers vía `oc`. Si el estándar ASI estuviera cableado en el producto en lugar de vivir como skill
seleccionado por relevancia, cada GO que no encaja en su premisa quedaría forzada a convivir con una
regla que no le corresponde, o el producto tendría que empezar a distinguir GOs por código. Un
skill que el orquestador selecciona por relevancia resuelve esto sin que el motor necesite saber qué
GO es cuál: aplica donde el contexto lo amerita y queda inerte donde no.

## Provenance y owner

Todo contenido que entra a DARQ trae su procedencia — de qué GO o equipo viene, para qué situación
institucional se escribió — y un owner nombrado que responde por él en el tiempo: quien lo actualiza
si el estándar cambia, quien lo retira si deja de aplicar. Contenido sin owner no se acepta, sin
importar su calidad.

## Qué DARQ no embarca

- Nada que sea competencia o superposición con lo que ya presenta la dirección ejecutiva
  ("ASI Harness") — DARQ es la distribución institucional de la DGISIS, no una alternativa a esa
  iniciativa (ver `docs/adr/0003-no-se-llama-harness.md`).
- Nada específico de otras áreas fuera de la DGISIS y sus GO.
- Contenido sin owner nombrado.

## Cómo se gobierna esto hoy

`docs/adr/0004-gobernanza-de-agregados.md` describe quién revisa un agregado y cómo, incluida la
salvedad explícita de que la gobernanza descrita ahí es deliberadamente simple mientras ambos
proyectos los mantiene una sola persona.

## Referencias

- `docs/adr/0005-fork-no-distribucion.md` — por qué DARQ dejó de ser una distribución y pasó a ser un fork.
- `docs/adr/0003-no-se-llama-harness.md` — por qué el nombre no compite con otra iniciativa de la
  organización.
- `docs/adr/0004-gobernanza-de-agregados.md` — quién aplica este contrato y cómo.
