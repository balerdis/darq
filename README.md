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

```bash
curl -fsSL https://github.com/balerdis/darq/releases/latest/download/install.sh | bash
```

Esto descarga, verifica e instala DARQ y sus dependencias (nvm, Node LTS y
OpenCode) en una cuenta limpia. `install.sh` acepta además `--verify` (informa
el estado sin cambiar nada), `--yes` (salta la confirmación), `--no-run`
(instala lo que falte pero no lanza nada al final) y `--bin-dir` (para instalar
el binario en un directorio distinto de `~/.local/bin`); correlo con `--help`
para ver la lista completa.

Si preferís no ejecutar un script bajado por `curl` directamente, el camino
manual, hoy:

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
`v1.1.0`). Si el checksum no coincide, no lo ejecutes — pedí el release de
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
   `pegasus`, `build_zipapp.py`, `build_installer.py` y la plantilla
   `install.sh` publicados en el tag fijado por `engine.pin`, verifica los
   cuatro contra el sha256 pinneado ahí (un mismatch es siempre un error
   fatal, nunca un warning), extrae el paquete, le aplica el rebranding
   declarativo de `rebrand.json` vía `rebrand/transform.py`, superpone
   `content/` encima del árbol ya rebrandeado, arma `dist/darq` con el
   `build_zipapp.py` recién descargado — nunca con una copia local — y genera
   `dist/install.sh` con el `build_installer.py` del motor, a partir del
   `identity.json` propio de DARQ.
3. **`tools/verify_darq.py`** — corre el binario ya construido de verdad,
   dentro de un `$HOME` descartable que el propio script crea y borra: chequea
   `darq --version`, `darq doctor --json`, un `darq install --cli opencode`
   real, la ubicación del data dir, escanea todo lo instalado en busca de
   fugas de marca fuera de los tokens de wire protegidos, y además verifica
   `dist/install.sh`: que no mencione al motor en ningún lado, que su
   encabezado de identidad sea el de DARQ, y que `install.sh --help` ande.

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
- **Quedan trazas de marca del motor en dos puntos de los artefactos
  instalados** — medidas y clasificadas explícitamente en `rebrand.json` y
  verificadas en cada corrida de `tools/verify_darq.py`, que además falla si
  alguna de las dos entradas de abajo deja de ocurrir (una entrada que no
  clasifica ningún hit real es una entrada obsoleta que hay que sacar del
  registro, no dejar ahí afirmando un residuo que ya no existe). Son residuo
  cosmético, ambas en el registro `accepted_residue`: el registro
  `known_defects`, para trazas que además rompen algo, está hoy vacío. Desde
  el motor v5.28.0 los nombres de artefacto en disco se derivan de
  `identity.json` en vez de ser literales, así que esta lista es mucho más
  corta que antes de esa versión:
  - `pegasus-zellij-state`, el nombre del directorio de estado bajo
    `~/.config/` y `~/.cache/` que usa el plugin de Zellij. Es una decisión
    deliberada del motor, no una limitación de alcance: esos directorios
    viven fuera del directorio de configuración del CLI, ningún journal los
    reclama, y derivarlos huerfanaría en silencio el estado que la persona ya
    tiene en disco.
  - `"Pegasus skill index"`, una línea de docstring autorreferencial dentro
    del módulo del skill-registry — el único lugar donde ese archivo, ya
    llamado con el nombre del producto, todavía menciona el nombre del motor.
    Arreglo upstream de una sola línea, diferido a la próxima release del
    motor.
  - Distinto es el caso de las variables de entorno `PEGASUS_*` y los ids de
    esquema versionados (`pegasus/cli-report/v1` y similares): esos son
    identificadores de wire estables, compartidos por cualquier distribución
    construida sobre el mismo motor, y están bien como están.

## Más contexto

Las decisiones de diseño están documentadas como ADR en `docs/adr/`:
por qué DARQ es una distribución y no un fork (0001), por qué es marca y
contenido y no un segundo producto (0002), por qué no se llama "harness"
(0003), y cómo se gobierna la aceptación de contenido nuevo (0004).
