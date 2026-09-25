# Transportar un cambio desde Pegasus

DARQ es un fork completo de Pegasus Harness (ver [ADR 0005](adr/0005-fork-no-distribucion.md)).
Los cambios genéricos que se hacen en Pegasus se traen a mano, caso por caso. No hay
automatización y no se busca paridad perfecta.

Este documento es el procedimiento, y cada regla de acá salió de un transporte real que salió mal
de esa manera. No es una lista de buenas intenciones: es el registro de lo que ya costó.

## 1. Traer los objetos SIN los tags

```sh
git fetch --no-tags /home/serg/ia/pegasus-harness main:refs/remotes/pegasus-local/main
```

**`--no-tags` no es opcional.** `git fetch` sigue los tags por default, y los tags de Pegasus
apuntan a commits que DARQ tiene en su historia — porque la comparte. Sin esa bandera, los tags de
release de Pegasus aparecen en DARQ como si fueran propios.

Ya pasó: un transporte trajo los tags de Pegasus y se empujó al remoto de DARQ un `v6.1.2` que
apuntaba a un commit de Pegasus. Lo atrapó `tools/build_release_evidence.py`, que se negó a generar
la evidencia porque el `install.sh` del árbol no coincidía con el del commit que el tag señalaba.
No llegó a haber release, pero la próxima vez puede no haber un guardián en el camino.

**Un tag alcanzable desde HEAD no es un tag propio.** DARQ comparte la historia de Pegasus, así que
los tags viejos de Pegasus apuntan a ancestros legítimos del HEAD de DARQ. Para distinguirlos hay
que mirar qué commit *creó* el tag, no si es alcanzable.

## 2. Mirar qué falta, no qué hay en Pegasus

Armar la lista con `git log v<ultima>..HEAD` del lado de Pegasus **no alcanza**: puede incluir
commits que ya se transportaron en una ronda anterior. Comparar contra lo que DARQ ya tiene.

Si un `git cherry-pick` termina con *"the previous cherry-pick is now empty"*, ese commit ya
estaba. Seguir con `git cherry-pick --skip`.

## 3. Los conflictos esperables, y por qué son correctos

Dos archivos conflictúan casi siempre, y en los dos el conflicto es la respuesta correcta:

- **`docs/arquitectura/arquitectura.md`** — la tabla de deudas, cuando una fila se mueve de "sin
  unidad asignada" a "resueltas". Las dos copias tienen la misma tabla con la marca sustituida.
- **`docs/contrato-inclusion-artifacts.md`** — es donde los dos productos difieren **a propósito**:
  Pegasus enumera sus skills y dice que no embarca ninguna de dominio; DARQ enumera las suyas,
  incluidas las dos institucionales. La cifra la deriva un test del árbol, así que esa diferencia
  no puede quedarse vieja en silencio.

La resolución es tomar el lado entrante y **localizarlo**, nunca quedarse con el lado de DARQ: el
entrante trae el cambio que se está transportando.

## 4. Lo peligroso no son los conflictos: son los hunks que aplican limpio

Un conflicto avisa. Un hunk que aplica limpio trae la prosa y los literales del upstream **sin que
nadie mire**. En un transporte de diez commits entraron así diecinueve literales de Pegasus, entre
ellos:

- `from pegasus.tui import app` — **código ejecutable**, habría roto el arranque;
- `name == "pegasus.tui.app"` dentro de un hook — no habría fallado: **habría dejado de probar en
  silencio**, que es el modo de falla caro.

## 5. Las cinco formas del literal, y cuál se ve

`tests/test_upstream_module_paths.py` es el guardián de esto. **Corrélo siempre después de cada
cherry-pick**, antes de cerrar el commit.

| Forma | ¿La ve el guardián? |
|---|---|
| Ruta de módulo con punto: `pegasus.core.identity` | **sí** |
| Segmentos separados: `_ROOT / "src" / "pegasus" / "content"`, `os.path.join(..., "pegasus", ...)`, `.joinpath("pegasus")`, o la misma tupla partida en varias líneas | **sí** |
| Ruta literal en una cadena o regex, con o sin el prefijo `src/`: `"src/pegasus/content/skills/"`, `"pegasus/content/skills/"` | **sí** |
| Nombre de agente de upstream: `pegasus-orchestrator`, `king-pegasus` — en la prosa de un archivo, o como el nombre del archivo mismo | **sí** |
| Prosa que nombra el producto: "Pegasus hace X" | no, y a veces corresponde |

La ruta con punto la agarra `UPSTREAM_MODULE_PATH`, desde el fork original. Las otras dos rutas se
agregaron después, en el mismo archivo: `SPLIT_UPSTREAM_PATH_SEGMENT` para los segmentos separados
y `UPSTREAM_PATH_STRING` para la cadena o regex de una sola pieza. El nombre de agente lo agarra
`UPSTREAM_AGENT_NAME` —el nombre de un agente que Pegasus renombró en este fork
(`pegasus-orchestrator` → `darq-orchestrator` y sus tres hermanos, más `king-pegasus` →
`arquitecto-darq`, que no sigue ninguna regla)— más un chequeo aparte sobre el nombre de archivo
mismo, para el caso en que un agente se llama `pegasus-explorer.md` pero su cuerpo nunca repite ese
nombre. Cinco de los seis nombres de upstream se derivan solos de `identity.json` y de qué agentes
`<program_name>-<rol>` ya tiene el árbol; `king-pegasus` está a mano porque no hay ninguna regla
mecánica que lo saque de `arquitecto-darq`.

**Alcance de directorios: `src/darq`, `tests`, `tools` y `docs`, para las cuatro formas por
igual.** Una revisión adversarial encontró que `docs/` no estaba en el escaneo, y lo probó con un
Markdown de prueba que nombraba `pegasus-orchestrator` y `src/pegasus/content/skills/foo.md` sin
que nada lo viera: la suposición de que una ruta partida o una cadena de una pieza son sintaxis de
Python y no pueden aparecer en prosa era falsa, porque este mismo documento las cita como ejemplo
en la tabla de arriba. El escaneo ahora lee `.py` y `.md` en los cuatro directorios por igual, y
sólo dos archivos quedan exentos, cada uno con su razón escrita en el propio código
(`EXEMPT` en `tests/test_upstream_module_paths.py`): `tests/test_architecture.py` (construye
paquetes de prueba llamados `pegasus` a propósito) y este mismo documento (cita los cuatro ejemplos
de la tabla de arriba tal cual). Ningún otro archivo de `docs/` necesitó exención —
`test_scanning_docs_needs_only_the_runbooks_own_exemption` lo mide, no lo asume, y se pone en rojo
el día en que un segundo archivo la necesite.

Un release grande y con mucha prosa de Pegasus, el tipo que agrega archivos nuevos de agentes o
skills en vez de tocar código, es exactamente el caso que más le pega a la forma del nombre de
agente: un archivo nuevo de upstream que nombra `pegasus-orchestrator` en su propia prosa, o que se
llama directamente `pegasus-orchestrator.md`, aplica limpio —git no tiene nada que resolver, es un
archivo que no existía— y antes de este guardián no había nada que lo mirara.

**Lo que el guardián todavía no ve, declarado y no asumido:**

- Un `"pegasus"` como argumento de `join`/`joinpath` detrás de una llamada anidada —
  `os.path.join(str(ROOT), "pegasus")`— porque el escaneo no balancea paréntesis; nada en el estilo
  actual de este fork anida una llamada adentro de un join, así que el hueco se acepta en vez de
  perseguirlo con una herramienta más pesada que una regex. Medido en
  `NoSplitUpstreamPathSegmentTest.test_a_nested_call_is_not_caught`.
- Un rol de agente que Pegasus estrena y este fork todavía no espejó como `darq-<rol>`: la
  derivación sólo produce `pegasus-<rol>` para un rol que el árbol *ya* tiene como `darq-<rol>`, así
  que un sexto agente genérico de upstream (`pegasus-scribe`, digamos) entra sin que nada lo vea
  hasta el día en que este fork cree `darq-scribe` — a partir de ahí la derivación lo agarra solo.
  Medido en `NoUpstreamAgentNameTest.test_a_wholly_new_upstream_agent_role_is_not_caught`.

Lo único que sigue sin verse por decisión, no por hueco, es la prosa que nombra el producto
("Pegasus hace X"): es una decisión editorial, no un defecto de transporte, así que este guardián
no la juzga.

## 6. Los tokens que NUNCA se localizan

Son contratos compartidos entre los dos productos. Localizarlos huerfanaría el estado en disco de
cualquier instalación existente:

```
pegasus-harness/journal/v4      pegasus/capability-manifest/v1
pegasus/model-assignment/v1     pegasus/artifact-catalog/v4
pegasus/cli-report/v1           pegasus-registry-assets/v3
pegasus_version                 pegasus_installed
pegasus-doctor                  pegasus-zellij-state
PEGASUS_SKILL_REGISTRY_BIN      PEGASUS_SKILL_ROOTS
PEGASUS_NO_UPDATE_CHECK         PEGASUS_ZELLIJ_STATE_DEBUG
.pegasus-                       .pegasus-data
/pegasus/catalog-build          pegasus-AGENTS.md
pegasus.md
```

Y `tests/test_architecture.py` construye a propósito paquetes ficticios llamados `pegasus`
(`_write_scratch_pegasus`): es deliberado y está documentado en el propio helper.

## 7. La regla que manda sobre todas

**Nunca hacer pasar un test debilitando lo que vigila.** La mayoría de lo que se transporta son
guardianes, y varios existen porque un defecto real se escapó. Si uno falla después del transporte,
la respuesta es **localizar el dato que mira**, jamás ampliar una exención, relajar una aserción ni
borrar un caso.

Si un test no se puede localizar sin cambiar lo que prueba, eso es un hallazgo: hay que pararse y
decirlo, no resolverlo.

## 8. Antes de cerrar

1. `PYTHONPATH=src:tests .venv/bin/python3 -m unittest tests.test_upstream_module_paths -q`
2. La suite completa, con el total esperado. Si el total **baja**, se borró un test.
3. Por cada guardián que hubo que tocar, una prueba de mutación: romper lo que vigila y comprobar
   que sigue fallando.
4. Construir el zipapp e instalar de verdad en un `$HOME` descartable, con los dos CLIs.

## 9. Dos archivos que git nunca va a seguir, y está bien

`src/darq/content/session-start.txt` (una línea, 0% de similitud con la de Pegasus) e
`identity.json` (reescrito entero) nunca se detectan como renombrados. Son exactamente los dos que
llevan la identidad, o sea los que nunca se querría transportar. La propiedad salió por casualidad,
pero conviene conocerla.
