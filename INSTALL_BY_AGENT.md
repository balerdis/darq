# Instalar Pegasus con un agente

Este instructivo es para un agente que instala Pegasus 5 en nombre de una persona, en la cuenta Linux
actual. Pegasus soporta hoy dos CLIs anfitrionas -- OpenCode y Claude Code -- y este documento nunca
elige una por vos: la parte 1 dice cómo averiguar cuál (o cuáles) hay en esta cuenta, y a partir de ahí
cada comando lleva `--cli <id>` explícito, nunca adivinado. El agente descarga, verifica y ejecuta
cada comando exactamente como está escrito acá; la persona decide qué MCPs se instalan, cuál es el
CLI de destino cuando hay más de una opción razonable, y mantiene el control de credenciales y
modelos.

Pegasus 5 es un solo archivo: `pegasus`. No hay wheel, no hay venv, no hay `pip install` — se
descarga, se verifica y se deja ejecutable en el PATH. Cada paso de esta guía dice si necesita red o
no, y qué hacer si falla.

**Nunca invoques `pegasus` sin subcomando, bajo ninguna circunstancia.** Corrido en una terminal abre
un menú interactivo (una TUI) que espera teclas de una persona; un agente no tiene con qué manejarlo,
y no hay forma de automatizarlo desde acá -- este instructivo no describe esa interfaz en ningún
momento, a propósito. Sin terminal (stdin y stdout no conectados a una), tampoco hay menú: imprime la
misma línea de uso que `--help` y termina con código de salida distinto de cero, que tampoco es un
resultado útil para vos. Usá siempre un subcomando explícito (`doctor`, `install`, `update`,
`upgrade`, `uninstall`, `restore`, `models`), y agregá `--json` cuando necesites un resultado que
puedas parsear en vez de prosa.

## 0. Usar `install.sh`, cuando alcanza

Si lo único que hace falta es dejar `python3` (ya presente), Node, el CLI elegido y el binario
`pegasus` instalados -- sin elegir MCPs todavía --, `install.sh` hace eso solo, y es más corto que
repetir los pasos manuales de este documento.

**`install.sh` nunca elige el CLI por su cuenta, y menos todavía corrido sin una persona detrás.**
Sin `--cli`, resuelve así: si la cuenta tiene exactamente un CLI soportado ya instalado, ese es el
destino; si hay ambigüedad (ninguno instalado, o los dos) y hay una terminal, pregunta; sin terminal
-- el caso de un agente corriendo esto por su cuenta -- se niega de entrada, nombrando `--cli` y los
ids válidos, en vez de instalar en un CLI que nadie eligió. Esto es real incluso bajo `--verify`, que
también resuelve el CLI antes de reportar nada:

```
$ install.sh --verify   (sin --cli, sin terminal, ningún CLI presente)
ERROR: no se indicó qué CLI instalar y no hay una terminal para preguntarlo (por ejemplo, corriendo
sin tty o con stdin cerrado). Usá --cli ID para elegir uno sin preguntar. Válidos: claudecode,
opencode.
```

**Por eso un agente siempre pasa `--cli` a `install.sh`, en cualquier modo, y nunca confía en que
"había exactamente uno instalado" vaya a seguir siendo cierto.** Si la persona ya te dijo qué CLI
usar, o el paso 1 más abajo ya lo determinó, usá ese id. Si no lo sabés todavía y necesitás
averiguarlo sin cambiar nada, `command -v claude` y `command -v opencode` (ninguno de los dos toca
disco) alcanzan para ver qué hay antes de llamar a `install.sh` con el `--cli` correcto -- no le pidas
a `install.sh` que adivine.

La forma no interactiva, la que un agente debe usar para instalar (sustituí `<cli>` por `claudecode` u
`opencode`):

```sh
curl -fsSL https://github.com/balerdis/pegasus-harness/releases/latest/download/install.sh \
  | bash -s -- --cli <cli> --yes --no-run
```

`--yes` salta la confirmación (necesaria: nadie va a escribir "y" en un pipe) y `--no-run` evita que
el script lance nada al final -- la TUI de Pegasus, que no es algo que un agente deba abrir. Repetido
sin `--no-run` sí la lanzaría (siempre a la TUI, nunca directo al CLI elegido -- ver INSTALL.md,
sección 1), así que un agente nunca lo corre sin ese flag. Para inspeccionar qué falta sin cambiar
nada -- por ejemplo, para decidir si hace falta seguir con este instructivo o no --, usá `--verify`,
con el mismo `--cli` explícito:

```sh
curl -fsSL https://github.com/balerdis/pegasus-harness/releases/latest/download/install.sh \
  | bash -s -- --cli <cli> --verify
```

`--verify` no descarga nada, no crea directorios, y termina con código de salida distinto de cero si
`python3` está ausente o es más viejo que 3.12 (o si falta `curl`) -- el resto de esta guía asume que
ese chequeo ya pasó. Que el CLI pedido con `--cli` no esté instalado todavía no es uno de esos
bloqueos: `--verify` sale en `0` igual, y el reporte simplemente dice que ese CLI "se va a instalar".
Si `install.sh` se niega por el motivo de Python, no lo resuelvas vos: instalar o actualizar el Python
del sistema es una decisión específica de cada distribución, y una elección equivocada puede romper
otra cosa. Decíselo a la persona con la versión que pide y la que se encontró, tal como el propio
script las imprime, y esperá su decisión.

Lo que `install.sh` no hace es elegir MCPs ni escribirlos en la configuración del CLI -- eso sigue
siendo tarea de los pasos de abajo (sección "Instalar en el CLI elegido y elegir MCPs"), porque es ahí
donde la persona tiene que tomar una decisión explícita por cada servidor.

## 1. Ubicar el checkout y confirmar la cuenta

```sh
test -f pyproject.toml -a -d src/pegasus
id -u
```

Si el segundo comando imprime `0`, detenete: no instales como root. Si el primero falla, no estás en
el checkout de `pegasus-harness` — y no importa: instalar Pegasus no exige ninguno. No le pidas nada a
la persona por esto; seguí directamente con el paso 2 desde el directorio que sea.

## 2. Descargar el asset del release y verificarlo

No hace falta resolver ningún tag ni preguntarle a la persona cuál quiere: `releases/latest/download/`
es un redirect de GitHub que siempre apunta al último release publicado, así que se descarga directo
de ahí.

```sh
DOWNLOAD_DIR="$HOME/Downloads/pegasus"
mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

BASE_URL="https://github.com/balerdis/pegasus-harness/releases/latest/download"

curl -fL -O "$BASE_URL/pegasus"
curl -fL -O "$BASE_URL/pegasus.sha256"
curl -fL -O "$BASE_URL/release-manifest.json"

sha256sum -c pegasus.sha256
python3 -c "
import json
manifest = json.load(open('release-manifest.json'))
assert manifest['schema'] == 'pegasus-harness-release/v5', manifest['schema']
names = {a['name'] for a in manifest['assets']}
assert names == {'pegasus', 'install.sh'}, names
print('release-manifest.json: coincide con', manifest['tag'], manifest['commit'])
"
```

**Detenete y no sigas si:** `sha256sum -c` reporta `FAILED`, o el script de Python levanta
`AssertionError`. Ninguno de los dos casos es recuperable descargando de nuevo en el momento: si el
release ya publicó bytes que no calzan con su propio manifest, avisale a la persona y esperá
instrucciones — no lo instales. (Un `FAILED` también puede pasar si se publicó un release nuevo justo
entre las dos descargas de arriba; en ese caso, volver a descargar los tres archivos sí resuelve.)

Esta es la única sección de toda la instalación que necesita red: descargar el archivo que se va a
instalar. Pegasus no tiene dependencias de terceros, así que ningún paso posterior vuelve a salir a
internet.

*No ejecutado en esta verificación: `curl` contra GitHub necesita red, prohibida en este entorno de
trabajo. Lo que sí se probó, contra un artefacto construido localmente con `tools/build_zipapp.py` y
su propio `release-manifest.json` generado por `tools/build_release_evidence.py --tag v5.9.0` (un tag
de ejemplo cualquiera, sólo para tener uno en la corrida; no hace falta que coincida con nada de la
sección anterior, que ya no resuelve ningún tag), es que `sha256sum -c` y la comparación de
`schema`/`assets` distinguen exactamente un archivo correcto de uno alterado — corrida real:*

```
$ sha256sum -c pegasus.sha256
pegasus: OK
$ python3 -c "... (script de arriba) ..."
release-manifest.json: coincide con v5.9.0 57d58ccd2d942043a32a20f7696c48fc075e6e5d
```

*y, contra la misma copia con un byte agregado a mano:*

```
$ sha256sum -c pegasus.sha256
pegasus: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

## 3. Dejar el ejecutable en el PATH

```sh
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"
install -m 755 pegasus "$BIN_DIR/pegasus"

case ":$PATH:" in
  *":$BIN_DIR:"*) echo "PATH: ya incluye $BIN_DIR" ;;
  *) echo "PATH: falta $BIN_DIR -- invocá el ejecutable por su ruta absoluta y avisale a la persona" ;;
esac
```

**Si falta en el PATH, no lo agregues vos al perfil de shell de nadie**, ni siquiera "temporalmente":
decíselo y seguí. Y no lo necesitás para terminar — tenés la ruta absoluta, así que invocá
`"$BIN_DIR/pegasus"` y andá.

Lo que sí tenés que decirle, con estas palabras, porque es el error fácil de cometer: **un
`source ~/.bashrc` no alcanza.** Quien agrega `~/.local/bin` al PATH suele ser `~/.profile`, que corre
al *iniciar sesión* y no al abrir una terminal, y sólo si el directorio ya existía — y lo acaba de
crear esta instalación. Cerrar sesión y volver a entrar es lo que resuelve. Editar el shell es el
último recurso, no el primero, porque hacerlo cuando no hacía falta deja la entrada duplicada.

*Ejecutado tal cual: `install -m 755` dejó el archivo con permiso `0755`, y el `case` se probó con las
dos ramas (ausente y presente) sobre un `PATH` de prueba.*

## 4. Verificar y reportar

```sh
pegasus doctor
```

Como el paso 2 no depende de red y el paso 3 no toca nada más, si `sha256sum -c` terminó en `0` este
comando ya puede correr. **Éste es el paso que te dice qué CLIs anfitrionas hay en esta cuenta -- no
lo asumas de ningún otro lado.** Reporta cada adapter que Pegasus trae registrado, uno por línea, con
su estado real: presente (con la ruta de su configuración) o ausente.

*Ejecutado tal cual, contra el ejecutable puesto en un `bin_dir` de prueba y llamado por PATH, en una
cuenta con las dos CLIs presentes:*

```
$ pegasus doctor
Claude Code: present at /home/.claude, Pegasus not installed.
OpenCode: present at /home/.config/opencode, Pegasus not installed.
```

Si sólo una de las dos líneas dice `present`, ese es tu único destino razonable -- no le ofrezcas a la
persona instalar en la que falta. Si las dos dicen `present`, pedile a la persona cuál de las dos
querés que Pegasus integre (o si las dos), en vez de elegir vos. Si las dos dicen `not found on this
machine`, no hay nada para integrar todavía: decíselo a la persona antes de seguir, no instales un CLI
por su cuenta -- eso es tarea de la sección anterior (paso 0), no de Pegasus.

## Instalar en el CLI elegido y elegir MCPs

Con `pegasus` en el PATH y ya sabiendo, por el paso 4, cuál CLI vas a integrar (llamalo `<cli>` de
acá en adelante: `claudecode` u `opencode`), identificá primero su binario en la shell real de la
cuenta -- no asumas que una shell de login comparte el mismo PATH que la sesión del agente:

```sh
command -v claude       # si <cli> es claudecode
command -v opencode     # si <cli> es opencode
```

Pedile a la persona una decisión explícita por cada MCP que quiera instalar. El contenido embarca
cinco, y no son intercambiables entre sí: nombrale los cinco, con lo que cada uno necesita antes de
servir para algo.

| id | Qué es | Cómo se distribuye | Qué hay que saber antes de elegirlo |
| --- | --- | --- | --- |
| `cbm` | Grafo de la estructura del código: símbolos, callers, impacto. | `download` (binario de release, `sha256` fijo) | Si la persona ya lo corre por su cuenta, atalo en vez de instalarlo (ver abajo). |
| `engram` | Memoria persistente entre sesiones. | `download` (binario de release, `sha256` fijo) | -- |
| `playwright` | Maneja un navegador real contra una página real. | `npm` (tarball con `integrity` y lockfile propio) | Necesita Node para instalarse (ver "Preflight de Node") y un navegador compatible ya instalado; Pegasus no descarga navegadores. |
| `context7` | Documentación al día de librerías y CLIs de terceros. | `remote` (endpoint HTTPS) | Sale de la máquina: confirmá que esa red esté permitida. |
| `jira` | El tracker de la organización, a través del servidor remoto propio de Atlassian. | `remote` (endpoint HTTPS) | Dos cosas, las dos hay que decirlas antes de instalarlo. **(1)** Necesita una autorización única que Pegasus no puede hacer por nadie: bajo OpenCode, `opencode mcp auth jira`, corrida por la persona. Hasta que eso pase, toda herramienta de ese servidor falla igual y reinstalarlo no cambia nada. **(2)** No retiene ninguna herramienta: lo que Atlassian permita bajo esa cuenta, un agente que reciba el servidor lo puede hacer — crear, transicionar y editar tickets, no sólo leerlos. |

Traducí cada decisión a `--mcp <id>` (instalar) o a la ausencia del flag (no instalar) -- no hay
`--confirm`/`--decline` en v5, un servidor no nombrado simplemente no se instala:

```sh
pegasus install --cli <cli> --dry-run --mcp context7 --mcp jira
```

Si la persona ya corre uno de estos servidores por su cuenta bajo una clave propia, no lo instales de
nuevo: usá `--mcp <id>=<clave>` (por ejemplo `--mcp cbm=codebase-memory-mcp`). Esa forma pide a Pegasus
la convención y los permisos del servidor, sin descargar nada ni tocar la configuración de mcp para
ese id -- es lo que corresponde cuando la persona dice "eso ya lo tengo corriendo yo".

**Preflight de Node:** si alguno de los servidores elegidos se distribuye por npm -- de los cinco,
sólo `playwright` -- e `install` no encuentra `node` en el PATH, se niega antes de escribir nada,
*incluso en `--dry-run`*, con:

```
playwright needs Node to install, and node is not on PATH; installing Node is the user's own
responsibility, so change the selection or make node available before retrying
```

Esto no es un bug ni algo que el agente deba resolver instalando Node por su cuenta: contale a la
persona que ese servidor necesita Node y dale las dos salidas reales -- instalar Node ella misma, o
sacar ese servidor de la selección -- y esperá su decisión. (Reinstalar un servidor npm que ya está
materializado no dispara esto: no hay nada que buscar, así que no hace falta Node.)

Mostrale el plan a la persona antes de aplicar. Recién con su confirmación, repetí el mismo comando sin
`--dry-run`.

Si la selección incluyó `jira` y el CLI elegido fue OpenCode, decile que falta un paso que sólo puede
dar ella, y que el reporte de `install` no lo cubre: correr `opencode mcp auth jira` una vez. Un
`install` exitoso deja el servidor configurado y alcanzable por los agentes, pero sin esa autorización
ninguna de sus herramientas contesta. No lo hagas vos y no lo des por hecho: si más adelante ese
servidor falla, nombrá ese comando como la causa probable en vez de reinstalar.

## Dar acceso a un MCP que la persona administra por su cuenta

Esto es distinto de todo lo anterior: `--mcp <id>` y `--mcp <id>=<clave>` son para servidores que
Pegasus conoce, con descriptor propio. Si la persona instaló y administra un MCP que Pegasus nunca
vio -- Sentry, Figma, o cualquier otro -- ese servidor puede figurar en la configuración propia del
CLI elegido y seguir siendo invisible para todos los agentes: Pegasus renderiza cada agente con una
base que niega todo, y un servidor no nombrado en esa base no se abre aunque exista en la
configuración general del CLI.

`pegasus mcp grant` es el único mecanismo para eso, y es deliberadamente parejo: la clave se otorga a
todos los agentes por igual, nunca a uno solo. Antes de correrlo, confirmá con la persona la clave
exacta bajo la que su servidor está declarado en la configuración propia de ese CLI -- no la adivines,
y no aceptes un nombre "parecido". Si te equivocás, `grant` se niega y el JSON trae en `error` cuáles
claves sí están declaradas ahí, para ese CLI puntual -- mostrale esa lista a la persona en vez de
insistir con una variación.

```sh
pegasus mcp grant --cli <cli> <clave> --json
```

Si la clave no está declarada en la configuración de esa CLI, el comando se niega y el JSON trae en
`error` cuáles claves sí están declaradas -- mostrale esa lista a la persona en vez de reintentar con
una variación. Con éxito, el JSON trae `"action": "grant"`, la clave otorgada, y la lista completa de
lo ya otorgado bajo `"granted"`, más `activation`: bajo OpenCode trae el paso de reiniciarlo; bajo
Claude Code viene vacío, porque esa CLI no necesita ningún paso de activación -- no asumas el mismo
texto para las dos, leé lo que el JSON realmente trae.

```sh
pegasus mcp list --cli <cli> --json
pegasus mcp revoke --cli <cli> <clave> --json
```

`list` muestra lo otorgado ahora (`"granted"`) y qué otras claves declaradas `grant` aceptaría tal
como está esta instalación (`"available"`) -- nunca una clave que `grant` fuera a rechazar. Una clave
declarada que Pegasus ya alcanza por agente -- un servidor propio que esta instalación eligió, o una
clave ya ligada -- aparece en cambio en `"already_covered"`, no en `"available"`: otorgarla de nuevo
sería redundante, no un error, así que no desaparece del reporte sin explicación. Si la instalación
tiene una ligadura sin resolver (`--mcp id=<clave>` cuya clave nunca se registró), `grant`/`revoke` se
niegan de entrada para cualquier clave -- no sólo la ligada -- así que en ese estado `"available"` y
`"already_covered"` vienen vacíos, `"unresolved_mcp_bindings"` nombra el o los ids que bloquean, y
`"blocked"` trae el mismo texto exacto que `grant`/`revoke`/`update` ya usan para rechazar, nunca una
segunda redacción del mismo hecho -- resolvé eso primero (`pegasus install --cli <cli> --mcp
id=<clave>`) antes de esperar algo de `"available"`. `revoke` sobre una clave nunca otorgada no es un
error: el JSON trae `"status": "already-revoked"` y sale en `0`. `pegasus update --cli <cli>`
reaplica las claves ya otorgadas junto con el resto de la selección,
sin que haga falta repetir `mcp grant`.

Si un `install` posterior liga un servidor propio de Pegasus (`--mcp id=<clave>`) bajo la misma
cadena que una clave ya otorgada por su cuenta, esa clave otorgada queda redundante -- el servidor
sigue siendo alcanzable a través de los agentes que ahora lo declaran -- así que `install` la
descarta del grupo llevado de una instalación anterior en vez de abortar la instalación por eso; el
JSON trae la advertencia en `"grant_warnings"`, nombrando la clave descartada. Esto sólo aplica a una
clave que la persona no nombró en este mismo llamado: si en cambio corre `pegasus mcp grant` con una
clave que choca con la selección `--mcp` de ese mismo llamado, sigue siendo un error -- ahí la
colisión es una contradicción real entre lo que acaba de pedir, no algo que quedó de antes.

## Actualizar una instalación existente

Hay dos comandos que actualizan cosas distintas. No los confundas ni los uses uno por el otro.

### `pegasus update --cli <id>`: reaplica la selección ya instalada

Usalo cuando la persona pide "actualizar" una instalación que ya existe (por ejemplo, después de que
vos mismo la actualizaste con `pegasus upgrade`, o simplemente porque pasó tiempo). **No corras
`pegasus install --cli <id>` a secas para esto:** sobre una instalación que ya tiene una selección
registrada, un `install` sin `--mcp` se rechaza antes de escribir nada -- el JSON trae
`"status": "failed"` y no se toca un solo archivo -- así que no te va a comer ninguna atadura de MCP,
pero tampoco te va a actualizar nada. Si la persona quiere retirar esa selección, la grafía deliberada
es `--mcp none`, y sólo correla si lo pidió. `update` existe exactamente para lo otro: reaplica la
selección propia registrada, MCPs atados incluidos, sin que vos tengas que reconstruirla. El rechazo,
que `update` no toque la selección y que `--mcp none` la vacíe están corridos contra una instalación
real en `InstallGuidesSayABareInstallIsRefusedTest`
(`tests/test_install_guides_command_surface.py`).

```sh
pegasus update --cli <cli> --dry-run --json
```

Mostrale el plan a la persona (o resumíselo) antes de aplicar. Con su confirmación, repetí sin
`--dry-run`:

```sh
pegasus update --cli <cli> --json
```

**Si el JSON trae `"status": "failed"`, no reintentes con otros flags -- `update` no tiene ninguno más
que ayude.** Mirá `error` y actuá según cuál de estos dos mensajes es:

- `"<cli> has nothing installed to update; run install instead"` -- no hay nada instalado ahí
  todavía. No es un fallo tuyo: contale a la persona que no hay instalación previa para esa CLI y, si
  quiere una, seguí la sección "Instalar en el CLI elegido y elegir MCPs" de arriba (`install`, no
  `update`).

- Un mensaje que empieza con `"... has bound mcp server(s) ... whose server key was never recorded"`
  -- `update` se niega a adivinar la clave de un servidor atado que quedó registrado antes de que
  Pegasus la guardara, porque adivinar retiraría justo esa atadura. El mensaje mismo trae, listo para
  copiar, el comando `pegasus install --cli <id> --mcp <id>=<key>` que hace falta correr una vez por
  cada id afectado -- con un `<key>` de relleno en cada uno. **Vos no sabés esa clave.** Conseguila de
  la configuración propia de esa CLI (no es algo que Pegasus guarde) o preguntale a la persona; nunca
  inventes un valor para `<key>`. Corré ese `install` una sola vez con la clave real, y a partir de ahí
  `update` vuelve a funcionar sin flags. `pegasus doctor --json` también imprime este mismo comando,
  bajo `mcp_bound_unknown_keys`, si preferís detectar el caso antes de intentar `update`.

### `pegasus upgrade`: reemplaza el binario de `pegasus`

Esto descarga un ejecutable nuevo y lo instala en lugar del actual. **Nunca lo corras por tu cuenta:**
necesitás el visto bueno explícito de la persona antes de ejecutarlo sin `--dry-run`, igual que con
cualquier escritura sobre su cuenta. Empezá siempre por el `--dry-run`:

```sh
pegasus upgrade --dry-run --json
```

Si el plan muestra una versión nueva y la persona confirma, corré el upgrade real y **reportá el
resultado de la verificación, no solo "listo"**:

```sh
pegasus upgrade --json
```

Con éxito, el JSON trae `"status": "upgraded"`, `"old_version"`, `"new_version"` y
`"restart_required": true`. Ese último campo no es adorno: **el proceso de `pegasus` que hizo el
upgrade sigue siendo la versión vieja** -- conserva el inode del archivo con el que arrancó. No le
digas a la persona que la versión nueva ya está activa, ni la asumas vos mismo en el siguiente comando
que corras: decile explícitamente que tiene que reiniciar Pegasus (cerrar y volver a invocarlo) para
que la versión nueva quede en efecto.

Si el JSON trae `"status": "already-current"`, tampoco es un error -- el código de salida es `0`
igual que con `"upgraded"`. Significa que ya estaba en la versión más nueva publicada (viene en
`"version"`); decíselo a la persona tal cual, sin reintentar nada ni tratarlo como una falla.

Si el JSON trae `"status": "failed"` (código de salida distinto de cero), mirá `error` -- no hay flag
que arregle ninguno de estos:

- `"could not reach GitHub to check the newest published release -- ..."` -- no hay red. No reintentes
  en loop; avisá y esperá a que haya conexión.
- `"... is not writable by this process; upgrade refuses to download anything it could not then
  install. Instead, ..."` -- el mensaje mismo trae el comando manual (descargar, verificar contra
  `pegasus.sha256`, y copiar el archivo a mano, con `root`/`sudo` si hace falta). No intentes escalar
  privilegios vos mismo; pasale ese comando a la persona.
- `"pegasus is not running from an installed executable -- ..."` -- estás corriendo desde un checkout
  de código fuente, no desde el zipapp del release. No hay binario que reemplazar acá; si la persona
  quiere el ejecutable, seguí la sección de instalación de este mismo instructivo en la cuenta
  correspondiente.

## Respetar el estado existente

No fuerces colisiones: Pegasus las informa y preserva los archivos o claves existentes. Después de
instalar, revisá `pegasus doctor` y el journal en
`$XDG_DATA_HOME/pegasus-harness/journal-v4.json` (o `~/.local/share/pegasus-harness/journal-v4.json`
si esa variable no está definida) -- el mismo journal para cualquier CLI, todas sus instalaciones
registradas ahí adentro. La persona puede usar las herramientas del CLI elegido que prefiera para su
propia configuración, pero el agente no debe pedir, leer ni reproducir su contenido.

Si hace falta deshacer algo, usá únicamente `pegasus restore` (vuelve a la generación anterior) o
`pegasus uninstall --cli <cli>` (retira sólo lo que el journal reclama como propio). No borres
configuración ajena a mano.

No le prometas a la persona que una edición suya sobre un archivo instalado se preserva: no se
preserva. Antes de afirmar qué sobrevive a un `install`, `update` o `uninstall`, leé
[Limitaciones aceptadas](docs/arquitectura/arquitectura.md#limitaciones-aceptadas), que trae el
alcance exacto del aviso `overwritten`, sus dos huecos y la ventana de `pegasus restore`.

La instalación manual canónica está en [INSTALL.md](INSTALL.md); [README.md](README.md) presenta
ambas rutas y [MANUAL.md](MANUAL.md) explica el control de modelo y proveedor de la persona.
