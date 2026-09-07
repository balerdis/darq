# DARQ

DARQ es la distribución institucional de la DGISIS: el mismo motor Pegasus, con
los estándares y skills que los propios equipos de la DGISIS necesitan —
empezando por el estándar de versiones ASI y la skill de seguridad Laravel, y
sumando a futuro contenido aportado por las GO, como una skill para operar
OpenShift vía `oc`. El alcance es explícito: DARQ es para la DGISIS y sus GO,
no para el organismo entero ni un reemplazo de otras iniciativas.

DARQ no contiene una sola línea de código de motor. En tiempo de build descarga
un release publicado y fijado de `pegasus-harness`, verifica su integridad,
le aplica un rebranding declarativo, y le superpone el contenido propio en
`content/`. Ver `docs/adr/0001-distribucion-no-fork.md` para el porqué.

## Instalar

Todavía no hay un instalador propio — ver [Fuera de alcance](#fuera-de-alcance-por-ahora)
más abajo. El camino manual, hoy:

```bash
# 1. Descargar el binario y su checksum del release que quieras instalar
curl -LO https://github.com/balerdis/darq/releases/download/<tag>/darq
curl -LO https://github.com/balerdis/darq/releases/download/<tag>/darq.sha256

# 2. Verificar el checksum antes de ejecutar nada
sha256sum -c darq.sha256

# 3. Darle permiso de ejecución y ponerlo en el PATH
chmod +x darq
mkdir -p ~/.local/bin && mv darq ~/.local/bin/darq

# 4. Instalar el contenido de DARQ para tu CLI
darq install --cli opencode
```

Reemplazá `<tag>` por el tag del release que vayas a instalar (por ejemplo
`v1.0.0`). Si el checksum no coincide, no lo ejecutes — pedí el release de
nuevo o avisá al equipo de I+D.

## Build desde código fuente

Punto de entrada único:

```bash
tools/check.sh                # guardia anti-fork + build + verificación, en una sola corrida
tools/check.sh --offline      # reusa lo que ya esté en la caché; los checksums se verifican igual
tools/check.sh --no-build     # salta el build, verifica lo que ya esté en dist/darq
```

Lo que hace cada paso, en el orden en que corre:

1. **`tools/check_no_engine_code.py`** — el guardia anti-fork. Confirma que
   ningún archivo del árbol de DARQ es código o contenido del motor: ni un
   directorio con nombre de capa hexagonal (`core`, `ports`, `adapters`,
   `infra`, `tui`), ni un archivo con nombre de contenido conocido del motor,
   ni un `.py` que importe el paquete `pegasus`. Toma el alcance de archivos
   de `git` (`ls-files --cached --others --exclude-standard`), no de una
   lista fija, así que también atrapa algo agregado pero todavía no
   commiteado.
2. **`tools/build_darq.py`** — descarga (o reusa, en `--offline`) el binario
   `pegasus` y `build_zipapp.py` publicados en el tag fijado por `engine.pin`,
   verifica ambos contra el sha256 pinneado ahí (un mismatch es siempre un
   error fatal, nunca un warning), extrae el paquete, le aplica el rebranding
   declarativo de `rebrand.json` vía `rebrand/transform.py`, superpone
   `content/` encima del árbol ya rebrandeado, y arma `dist/darq` con el
   `build_zipapp.py` recién descargado — nunca con una copia local.
3. **`tools/verify_darq.py`** — corre el binario ya construido de verdad,
   dentro de un `$HOME` descartable que el propio script crea y borra: chequea
   `darq --version`, `darq doctor --json`, un `darq install --cli opencode`
   real, la ubicación del data dir, y escanea todo lo instalado en busca de
   fugas de marca fuera de los tokens de wire protegidos.

### El pin

`engine.pin` fija dos cosas, no una: el tag de `pegasus-harness` que este
build consume, y el sha256 publicado de cada asset de ese tag. El tag dice qué
versión; el hash prueba que lo que se descargó es, byte a byte, lo que ese tag
publicó. Actualizarlo es deliberadamente un diff de un solo archivo — tag y
hashes, nada más en el mismo commit — para que revisarlo no exija leer un
diff de motor, solo confirmar que el hash corresponde al release que dice ser.

## Cómo proponer contenido

La aceptación de agregados a DARQ está centralizada en el equipo de I+D
(Pablo, Walter, Aníbal), según `docs/adr/0004-gobernanza-de-agregados.md`.
El criterio material de qué entra y en qué forma — siempre un skill que el
orquestador elige por relevancia, nunca una regla cableada — está en
`docs/contrato-inclusion.md`. Si estás pensando en aportar algo, empezá por
ese documento.

## Limitaciones conocidas

- **Un solo producto por usuario del sistema operativo.** El motor no hizo
  seguro compartir `~/.config/opencode` entre dos productos en la misma
  cuenta de SO, así que DARQ y Pegasus no conviven en el mismo usuario.
- **Todavía no hay instalador propio.** El `install.sh` del motor tiene 1081
  líneas y cero parametrización; clonarlo recrearía exactamente el drift que
  este diseño existe para evitar. Parametrizarlo es trabajo upstream en
  Pegasus, pendiente.
- **Quedan trazas de marca del motor en algunos artefactos instalados** —
  medidas y clasificadas explícitamente en `rebrand.json` (registros
  `accepted_residue` y `known_defects`), verificadas en cada corrida de
  `tools/verify_darq.py`:
  - `pegasus-AGENTS.md` (el artefacto de system-prompt instalado), el
    subárbol `pegasus/skill-registry` con su ejecutable
    `pegasus-skill-registry` y su módulo `pegasus_skill_registry.py`, el
    archivo generado `pegasus-skill-registry.env`, el nombre de paquete npm
    `pegasus-opencode-notifier` (en `notifier/package.json` y su lockfile), y
    los tres archivos de plugin `plugins/pegasus-*.ts` junto con los símbolos
    que exportan (`PegasusOrchestratorNotifier`, `PegasusSkillRegistryPlugin`,
    `PegasusZellijStatePlugin`). Son ids de artefacto que el journal rastrea
    por ese nombre, o assets `.ts` que el transform de rebrand nunca reescribe
    (solo toca `.md` y `.txt`); renombrarlos es trabajo upstream pendiente en
    Pegasus, no algo que DARQ pueda resolver rebrandeando su propia copia. El
    título del toast de notificación del plugin de skill-registry
    (`"Pegasus skill registry"`) es, dentro de este grupo, el único caso
    genuinamente visible para quien usa DARQ, no solo plomería interna.
  - Distinto es el caso de las variables de entorno `PEGASUS_*` y los ids de
    esquema versionados (`pegasus/cli-report/v1` y similares): esos son
    identificadores de wire estables, compartidos por cualquier distribución
    construida sobre el mismo motor, y están bien como están.
- **Defecto funcional conocido: el notifier nunca dispara en DARQ.**
  `plugins/pegasus-orchestrator-notifier.ts` tiene hardcodeado
  `const ORCHESTRATOR_AGENT = "pegasus-orchestrator"` para decidir cuándo
  avisar. DARQ renombra su agente orquestador a `darq-orchestrator`, así que
  esa comparación nunca coincide y el plugin de notificaciones nunca dispara
  en una instalación de DARQ. Es el mismo tipo de bug que el motor v5.19.0
  acaba de arreglar del lado Python (`AGENT_FOR_ROLE` en
  `adapters/opencode/render.py`), pero sobrevive en este asset `.ts` porque el
  escaneo de identidad del motor (basado en AST) solo lee archivos `.py`. El
  arreglo es upstream: que el motor renderice este plugin con el nombre de
  orquestador declarado en el contenido, en vez de distribuirlo como asset
  estático. Mientras tanto, si notás que las notificaciones no llegan, es
  esto — no un bug nuevo de DARQ.

## Más contexto

Las decisiones de diseño están documentadas como ADR en `docs/adr/`:
por qué DARQ es una distribución y no un fork (0001), por qué es marca y
contenido y no un segundo producto (0002), por qué no se llama "harness"
(0003), y cómo se gobierna la aceptación de contenido nuevo (0004).
