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
   real, la ubicación del data dir, escanea el contenido de los archivos
   instalados bajo `~/.config/opencode` en busca de fugas de marca fuera de
   los tokens de wire protegidos — el alcance exacto de ese escaneo, y lo que
   queda afuera, está en «Deudas» — y además verifica `dist/install.sh`: que
   no mencione al motor en ningún lado, que su
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

## Deudas

Trabajo conocido que todavía está por decidirse o por hacerse. Cada fila declara
qué la destraba, para que acarrearla sea una decisión y no un olvido, y qué
puede hacer una persona mientras siga abierta. Acá no va lo que funciona así a
propósito: eso vive en «Limitaciones aceptadas», abajo. Las dos tablas viven en
este mismo archivo, y no en un registro aparte, por una razón concreta: este
README no tiene un solo link de Markdown y este repositorio no tiene validador
de links, así que un puntero a otro documento no lo verificaría nadie.

| Deuda | Qué la destraba | Qué hacer mientras tanto |
|-------|-----------------|--------------------------|
| La bandera `--offline` no rehúsa cuando la caché está vacía: se va a la red igual. `fetch_pinned_assets` decide con `if offline and destination.is_file()`, así que un asset que no esté en `build/cache/` cae en la rama que descarga, sin decir una palabra. Su propia ayuda promete «reuse whatever is already cached», y la promesa vale sólo cuando ya está todo cacheado — que es justo el caso en el que no hace falta prometerla. Lo encontró un test escrito para cubrir otra cosa, y ese test hoy fija el comportamiento real, no el prometido | Decidir qué significa la bandera: rehusar con un error que nombre el asset faltante, o seguir cayendo a la red y reescribir la ayuda para que diga eso. Lo primero es lo que casi todo el mundo espera de un modo offline y es un cambio chico; lo segundo es más barato todavía y no arregla nada. No se tocó acá porque el encargo era cubrir, no cambiar el comportamiento | Si querés garantía de que no sale a la red, verificá que `build/cache/` tenga los cuatro assets antes de correr con `--offline`. Los tests de `check.sh` ya lo hacen: se saltean nombrando el asset que falta en vez de dejar que la llamada salga a internet |
| Dos de los tres tests de `tools/check.sh` no son herméticos: dependen de un `dist/darq` ya construido y de un `build/cache/` poblado, y las dos rutas están en `.gitignore`, así que en un clon limpio no existen. Hoy se saltean con un mensaje que nombra qué falta y con qué comando se produce, que es honesto, pero un skip no es cobertura: en la máquina donde más importaría —una recién clonada— esos dos no prueban nada. El tercero, el de argumento desconocido, sí es hermético y corre siempre | Poder correr `check.sh` contra un repositorio de prueba en vez del real. `ROOT_DIR` se deriva hoy de la ubicación del propio script y no se puede sustituir, así que haría falta un override de raíz. Fabricar un `dist/` sintético adentro del árbol real no es salida: sería repetir el defecto que este mismo repositorio ya tiene anotado más abajo, tests que ensucian el árbol de trabajo y dejan residuo si se los interrumpe | Correr `tools/build_darq.py --offline` una vez antes de la suite si querés que esos dos corran. Y no leer un «OK (skipped=1)» como si fuera cobertura completa |
| `overlay_content` (`tools/build_darq.py`) superpone `content/` reemplazando por ruta, sin detectar colisiones y sin pasar nunca las rutas del overlay por el mirror de marca. Un archivo de DARQ que aterrice sobre una ruta que el motor ya ocupa gana sin que nada lo diga —imprime la misma línea `OVERLAY:` que un archivo nuevo— y deja congelada la versión del motor en esa ruta: un cambio upstream ahí no vuelve a aparecer nunca. Y una ruta de DARQ que llevara la marca del motor entraría al paquete sin que el mirror la vea | Decidir qué hace el build ante una colisión: fallar, o reportarla como tal. Hoy no hay forma de distinguir «agregué contenido» de «pisé contenido heredado» leyendo la salida del build | Antes de agregar un archivo a `content/`, mirar si esa ruta existe en `build/work/extracted/pegasus/content` después de un build. Hoy no hay ninguna colisión |
| El escáner de fugas de marca prueba que no hay fugas sin clasificar *dentro del corpus que recorre*, y ese corpus es más angosto que «todo lo que la instalación escribió». Son cuatro huecos, los cuatro latentes hoy, escritos también en el docstring de `tools/verify_darq.py` bajo «Known limitations of check 5»: recorre sólo `~/.config/opencode` (nunca el data dir, donde el journal sí lleva la marca del motor, hoy sólo en tokens protegidos); compara contenido y nunca nombres de archivo; se come en silencio cualquier archivo que no decodifique como UTF-8; y toda la corrida se maneja con un único `install --cli opencode` | Una decisión de alcance del guardián, no un arreglo del rebranding. Es deuda y no limitación aceptada porque nadie decidió que el corpus se quede angosto: se documentó primero, a propósito, y ensancharlo quedó como decisión aparte | Nada urgente: ninguno de los cuatro esconde algo hoy. Si se agrega un asset binario, o un segundo adaptador de CLI, el hueco correspondiente deja de ser latente y hay que ensanchar el escaneo antes |
| `PEGASUS_INSTALL_BASE_URL` está en `protected_tokens`, pero DARQ no lo produce nunca: `dist/install.sh` deriva el nombre de la variable de `PRODUCT_PROGRAM_NAME` y termina buscando `DARQ_INSTALL_BASE_URL`. La cadena no aparece ni una vez en el instalador generado; en todo el repositorio vive sólo en `rebrand.json` y en el test que la nombra. Es un permiso de enmascarado que no puede coincidir con nada, y sobrevive porque `protected_tokens` está exento a propósito del chequeo que borra entradas que no clasifican ningún hit | Decidir si se saca de la lista o se deja como blindaje ante un cambio upstream. Sacarla es un diff de una línea; dejarla exige asumir que una entrada inerte no enseña a ignorar la lista | Nada. No enmascara nada real, así que no puede tapar una fuga |
| Las dos entradas de `renames` en `rebrand.json` se reproducen exactas por derivación mecánica: correr `rebrand.transform.rename_relative_path` sobre `agents/king-pegasus.md` y `agents/mcp/cbm@king-pegasus.md` devuelve los mismos destinos que la lista declara. La lista es inerte. Y `renames_notes` la justifica diciendo que el destino «no es una sustitución textual del origen», premisa que la propia tabla de sustituciones contradice: `["king-pegasus", "arquitecto-darq"]` es la primera regla, y es exactamente la que produce esos destinos | Decidir entre vaciar la lista —con la derivación mecánica ya cubierta por el mirror que falla nombrando la ruta— o corregir la nota para que diga por qué se dejan entradas explícitas que no hacen falta | No confiar en `renames_notes` como explicación de por qué esas dos filas están ahí. El comportamiento lo fija la tabla de sustituciones, no la lista |
| La razón de la entrada `accepted_residue` del docstring del skill-registry dice que el arreglo está «diferido a la próxima release del motor». El motor pasó cinco releases desde entonces (v5.28.0 a v5.33.0, que es el tag que fija `engine.pin`) y la línea sigue igual upstream, en `src/pegasus/adapters/opencode/assets/skill-registry/skill_registry.py`. El residuo se acepta; lo que venció es la razón escrita al lado. Es deuda y no limitación porque la fila declara un arreglo que se espera, y una limitación aceptada no espera nada | Cualquiera de las dos: que el arreglo de una línea entre upstream, o que la razón se reescriba sin prometer una release que ya pasó cinco veces | Leer esa nota como lo que es hoy: un residuo cosmético aceptado de hecho, con una fecha de vencimiento que nadie renovó |
| `laravel-security` no cumple el criterio de admisión que este mismo repositorio declara. `docs/contrato-inclusion.md` dice que DARQ rechaza «contenido genérico sin especificidad institucional», y el skill es guía de seguridad Laravel aplicable a cualquier equipo que use el framework: lo único propio de la organización en él es `author: DGISIS` en el frontmatter. El mismo documento lo nombra, dos secciones antes, como caso fundacional de lo que DARQ acepta. La tensión es entre dos párrafos del contrato, no entre el contrato y el contenido | Una decisión del equipo de I+D: o el skill gana la especificidad institucional que el criterio pide, o el criterio se redacta para admitir explícitamente contenido que el motor retiró por alcance aunque sea genérico | Nada bloquea usarlo. Lo que conviene no hacer es citarlo como ejemplo del criterio: hoy es el contraejemplo |
| `balerdis/darq` es un repositorio público —verificado con `gh repo view`— y `content/skills/estandar-versiones-asi/` se describe a sí mismo como política de tecnología interna de la organización, con una matriz de versiones homologadas citando documento y página de fuentes controladas. Su propio `references/provenance.md` sostiene que el asunto es de alcance y no de confidencialidad: los documentos fuente no se redistribuyen, sólo la matriz derivada y sus citas, y ese alcance es exactamente por qué el skill vive en DARQ y no en el motor | Una decisión de gobernanza de quien es dueño del repositorio, no un defecto técnico: si el argumento de alcance alcanza para publicar la matriz derivada, no hay nada que hacer; si no alcanza, lo que cambia es la visibilidad del repositorio o la forma en que se distribuye ese skill | Nada en el árbol. El motor ya tomó la decisión inversa para su propio release público, y la registra en su propio contrato de inclusión |
| La suite escribe archivos dentro del árbol de trabajo real: `tests/test_check_no_engine_code.py` crea a propósito un `core/`, un `content/king-pegasus.md`, un `helper.py` que importa el motor y un `guard-scope-probe.py` en la raíz del repositorio, para probar que el guardia anti-fork los atrapa, y los saca con `addCleanup`. Una interrupción a mitad de corrida deja exactamente el tipo de archivo que la invariante de cabecera de este repositorio prohíbe | Decidir si esos tests pueden ejercitar el guardia sobre un árbol temporal. Hoy no pueden: el guardia toma su alcance de `git ls-files` sobre el repositorio real, que es justamente lo que se quiere probar | Si una corrida se interrumpe, correr `git status --short` antes que nada. Lo que aparezca con esos nombres es residuo de test, no una violación — y borrarlo es lo primero, porque la corrida siguiente del guardia va a fallar por él |

## Limitaciones aceptadas

Acá no hay nada pendiente, y esa es la razón de separarla de la tabla de arriba.
Una deuda declara qué la destraba porque se espera que alguna vez se destrabe;
una limitación describe cómo funciona el producto a propósito, con el motivo por
el que se eligió así. Mezclarlas promete en silencio un arreglo para lo que no
va a arreglarse. Una fila se muda de acá para arriba sólo si la decisión se
reabre.

| Limitación | Por qué es así | Qué hacer al respecto |
|------------|----------------|-----------------------|
| Un solo producto por usuario del sistema operativo: DARQ y Pegasus no conviven en la misma cuenta de SO | El motor no hizo seguro compartir `~/.config/opencode` entre dos productos en la misma cuenta: la segunda instalación sobrescribe lo que la primera dejó en esa configuración compartida. El motor lo documenta como comportamiento conocido, no como algo a resolver | Un usuario del sistema operativo por producto. Si hacen falta los dos, hacen falta dos cuentas |
| El plugin de Zellij escribe en `~/.config/pegasus-zellij-state/` y `~/.cache/pegasus-zellij-state/`, con el nombre de marca del motor, aunque el archivo del plugin sí se derive: la instalación deja un `darq-zellij-state.ts` apuntando a un directorio `pegasus-zellij-state` | Es una decisión deliberada del motor, y su propio asset la explica en un comentario: esos directorios viven fuera del directorio de configuración del CLI, ningún journal los reclama y ningún retiro ni migración los alcanzaría con otro nombre, así que derivarlos huerfanaría en silencio el estado que la persona ya tiene en disco — su script de reporte, su log de debug | Nada. Está registrado en `accepted_residue` y `tools/verify_darq.py` lo reporta como NOTE en cada corrida; si dejara de ocurrir, la corrida falla pidiendo que se saque la entrada |
| Las variables de entorno `PEGASUS_*` y los ids de esquema versionados (`pegasus-harness/journal/v4`, `pegasus/cli-report/v1`, `pegasus/artifact-catalog/v4` y similares) se quedan tal cual dentro de los artefactos instalados | Son identificadores de wire estables, compartidos por definición por cualquier distribución construida sobre el mismo motor. Reescribirlos rompería la compatibilidad con el motor que DARQ consume sin ganar nada: quien los lee es código, no una persona formándose una impresión de marca | Nada. Están en `protected_tokens`, que el escáner de fugas enmascara antes de cualquier sustitución y trata como silenciosos por diseño |
| El paquete Python que viaja adentro de `dist/darq` se sigue llamando `pegasus`: el zipapp contiene `pegasus/core/…`, `pegasus/adapters/…`, y ningún `.py` se rebrandea | La sustitución se aplica sólo a `.md` y `.txt`, a propósito: reescribir código fuente sería empezar a mantener un fork, que es exactamente lo que cierra la ADR 0001. Nada de ese namespace es superficie de usuario — los nombres de artefacto en disco, el ejecutable y el data dir se derivan de `identity.json` desde el motor v5.28.0 | Nada. `tools/verify_darq.py` verifica la superficie instalada y la salida de los comandos, que es donde la marca importa |
| Durante `darq doctor`, el motor se presenta ante cada servidor MCP de terceros como `pegasus-doctor`: es el `clientInfo.name` fijo del handshake `initialize` (`CLIENT_NAME` en `core/mcp_handshake.py`, una constante de módulo que no deriva de `identity.json`) | Es un identificador de cliente del ecosistema, de la misma familia que los ids de esquema, y está registrado como tal en `protected_tokens`. Conviene saberlo igual, porque es la única cadena de marca del motor que sale de la máquina de la persona: todo el resto del residuo conocido se queda en disco | Nada en DARQ; derivarlo sería un cambio upstream. Si un servidor MCP de terceros registra qué cliente lo consultó, va a ver `pegasus-doctor`, no `darq` |
| No hay CI en este ecosistema: `.github/` no existe, ni acá ni en el motor | Es una decisión deliberada, registrada en `docs/adr/0001-distribucion-no-fork.md`. El guardia anti-fork corre localmente, a mano o desde `tools/check.sh`, y toma su alcance de lo que reporta `git` en vez de una lista fija, así que atrapa también lo agregado y todavía no commiteado | Correr `tools/check.sh` antes de proponer un cambio o publicar un release. Nada lo va a correr por vos |

## Más contexto

Las decisiones de diseño están documentadas como ADR en `docs/adr/`:
por qué DARQ es una distribución y no un fork (0001), por qué es marca y
contenido y no un segundo producto (0002), por qué no se llama "harness"
(0003), y cómo se gobierna la aceptación de contenido nuevo (0004).
