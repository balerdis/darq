# Manual de uso: Pegasus Harness + OpenCode

Este manual describe cómo usar Pegasus 5 una vez instalado: qué decide, qué preserva de tu cuenta y cómo se trabaja el día a día con OpenCode. Para instalarlo no hay procedimiento acá — está en [INSTALL.md](INSTALL.md) (manual) y en [INSTALL_BY_AGENT.md](INSTALL_BY_AGENT.md) (asistido por un agente).

## Qué es Pegasus en esta versión

Pegasus 5 es un solo archivo ejecutable: un `zipapp` de Python con shebang y bit ejecutable, que se instala en `~/.local/bin/pegasus` y no depende de nada instalado antes que él — el paquete no declara ninguna dependencia de terceros, así que no hay entorno privado que armar ni que mantener. `pegasus` sin argumentos abre una TUI cuando corre en una terminal; sin terminal, o con un subcomando explícito, se comporta como CLI. Ambas superficies llaman al mismo motor: nada que la TUI pueda hacer le está vedado a los flags. La versión mayor que nombra este párrafo no se retipea acá: la deriva del árbol `ManualNamesTheEntryPointThisReleaseShipsTest` (`tests/test_manual_figures.py`), que además comprueba contra el árbol el destino del binario y que no haya quedado ninguna dependencia que aislar.

Antes de usarlo necesitás OpenCode ya instalado en la cuenta: el binario `pegasus` no lo instala, actualiza ni desinstala — sólo se integra con una instalación existente, y si no la encuentra se niega antes de escribir nada. Quien sí lo instala es `install.sh`, el script que corre el comando de una sola línea con el que empieza [INSTALL.md](INSTALL.md): trae Node y OpenCode antes de llegar al binario, así que si instalaste por ahí eso ya está resuelto, y qué hace exactamente está en [su propia sección](INSTALL.md#1-qué-hace-installsh). También hace falta una cuenta Linux no-root, porque Pegasus escribe únicamente en tu propio `~/.config` y `~/.local`. Las dos mitades se corren en vez de afirmarse: `ManualSaysWhoInstallsOpenCodeTest` (`tests/test_manual_prerequisites.py`) le pide un `install` a una máquina sin OpenCode y le pide su plan al script contra un home descartable, y exige que esta línea nombre todo lo que ese plan trae.

## Instalar el payload en OpenCode

Con `pegasus` en el PATH, el comando que aplica el payload es:

```sh
pegasus install --cli opencode --dry-run --mcp <id>
```

`--dry-run` muestra el plan sin escribir nada; repetir el mismo comando sin ese flag lo aplica. Un servidor MCP no nombrado con `--mcp` no se instala — no hay `--confirm`/`--decline` como en v3, cada `install` nombra su selección entera. Podés repetir `--mcp` para pedir varios. Eso vale tal cual para la primera instalación; después no, y el cambio es deliberado: un `install` a secas sobre una instalación que ya tiene una selección registrada se rechaza antes de escribir nada, en vez de retirarla en silencio porque nadie repitió el flag. Para dejar esa selección como está, usá `pegasus update --cli opencode`; para revocarla a propósito, `--mcp none`. Las tres cosas —el rechazo, que no escriba nada al rechazar, y que la revocación deliberada vacíe de verdad la selección— las corre contra una instalación real `ManualSaysHowAnMcpSelectionIsRevokedOnPurposeTest` (`tests/test_manual_command_surface.py`).

Cada `--mcp` acepta dos grafías, y no piden lo mismo: `--mcp <id>` le pide a Pegasus que obtenga y administre ese servidor, y `--mcp <id>=<clave>` le pide sólo el contrato —la convención y los permisos— contra un servidor que tu instalación ya corre bajo esa clave, sin descargar ni configurar nada para ese id. Cómo se pasa de una a la otra, y qué pasa si esa clave choca con una que ya otorgaste, está en [Dar acceso a un MCP que vos mismo administrás](#dar-acceso-a-un-mcp-que-vos-mismo-administrás). Qué hace cada grafía con la instalación no se afirma acá: las corre contra una real `ManualSaysWhatTheTwoMcpSpellingsAskForTest` (`tests/test_manual_command_surface.py`), comparando qué queda configurado y qué permiso lleva cada agente.

Si el plan encuentra una clave o un archivo tuyo en el destino, lo informa y lo preserva: no lo adopta como si fuera de Pegasus. El payload de OpenCode queda bajo `~/.config/opencode/` (o el `XDG_CONFIG_HOME` que tengas seteado): las skills en `skills/`, los comandos en `commands/`, el system prompt de Pegasus como `pegasus-AGENTS.md` (el nombre lleva el prefijo del binario instalado, `pegasus` en esta distribución; otra distribución del mismo motor lo instala con su propio nombre), y los agentes declarados dentro de `opencode.json` — OpenCode no los materializa como archivos aparte. Después de un apply exitoso, cerrá y reiniciá OpenCode para que cargue la configuración nueva.

## Qué hacen los cinco MCPs opcionales

| MCP | Uso práctico | Decisión |
| --- | --- | --- |
| CBM (`codebase-memory-mcp`) | Buscar estructura, callers, flujos e impacto de código. | Es inteligencia de código; no prueba comportamiento. |
| Engram | Recuperar decisiones, progreso y resúmenes entre sesiones, con el protocolo de memoria persistente. | La memoria no puede sobreescribir la evidencia actual. |
| Playwright | Probar una frontera de navegador cuando el proyecto lo necesita. | Requiere un navegador compatible instalado por separado; Pegasus no lo descarga. |
| Context7 | Consultar documentación del proveedor de forma remota. | Es remoto, igual que Jira; confirmá el acceso a esa red por separado. |
| Jira | El tracker de tu organización, a través del servidor remoto propio de Atlassian. Qué herramientas expone lo decide Atlassian, no Pegasus. | Necesita una autorización única, `opencode mcp auth jira`, antes de que cualquier herramienta conteste, y nada más te lo va a avisar. No retiene ninguna herramienta: lo que ese servidor permita, un agente que lo reciba lo puede hacer — crear, transicionar y editar, no sólo leer. |

Instalá solo lo que el equipo vaya a usar: un servidor no pedido con `--mcp` no deja config ni dependencia huérfana.

Lo mismo se elige desde la TUI (`pegasus`, sin argumentos), en el menú principal → `Install` → elegí el CLI: antes del plan aparece la pantalla `Install · <CLI> · choose which mcp servers to install`, un casillero por cada servidor que esta release embarca y una fila `Continue` al final. Gobierna una sola cosa: cuáles de esos servidores son parte de la instalación. Abre mostrando el estado real de la máquina y no una lista vacía —todo lo que el journal registra como instalado abre tildado—, y eso incluye los servidores atados: uno que Pegasus no obtiene sino que usás contra una clave tuya (`--mcp id=<clave>`) está instalado igual, así que abre tildado, y su fila lo dice con el prefijo `bound to <clave>` delante de la descripción. Dos casilleros idénticos que significan cosas distintas serían una trampa: uno pide «instalá y administrá este servidor» y el otro «dame el contrato contra el que ya corro bajo esta clave».

Por eso continuar sin tocar nada reproduce el estado que ya tenías, en vez de retirar una parte: cada fila tildada se vuelve a emitir con la grafía con la que estaba registrada, `id=clave` para una atada y el nombre pelado para una que administra Pegasus. Destildar una fila es la única forma de pedir un retiro, y por eso siempre es un acto deliberado. Lo que esta pantalla no hace es cambiar quién administra un servidor: convertir uno atado en uno que Pegasus obtiene, o al revés, es trabajo de `Grant MCP servers` (más abajo), y acá una fila conserva su atadura la tildes o la destildes.

Si destildaste algo, lo que te salva es el plan que viene después: todavía no escribió nada, y lista bajo `Would retire, no longer asked for:` exactamente lo que ese `Continue` sacaría de la máquina. Leé esa sección antes de confirmar; si aparece algo que no querías sacar, `esc` vuelve atrás sin escribir y podés volver a tildarlo. Si la instalación tiene una ligadura sin resolver (`--mcp id=<clave>` con la clave nunca registrada), la pantalla muestra ese bloqueo en lugar de la lista, por el mismo motivo que `Grant MCP servers`: con ese estado sin resolver no hay fila que pueda reproducirse bien, y hay que resolverlo primero.

## Dar acceso a un MCP que vos mismo administrás

Pegasus renderiza cada agente con una base que niega todo (`{"*": false}`) más una lista de los servidores que él mismo instala. Un MCP que instalaste y administrás por tu cuenta (Sentry, Figma, o cualquier otro) queda fuera de esa lista aunque figure en tu `opencode.json`: OpenCode combina el bloque de permisos propio del agente al final, así que si Pegasus no le abre la puerta a esa clave, ningún agente puede usarla, sin importar qué diga tu configuración general.

Si ya administrás tu propia clave `jira` con `mcp grant` —que alcanza a **todos** los agentes que la release embarca, sin excepción y sin que el número cambie la regla: hoy son **16 agentes**— y más adelante un `install`/`update` selecciona el `jira` que Pegasus embarca —que sólo alcanza a los agentes que su propio descriptor nombra, hoy **8 agentes**, los mismos que llevan Context7—, la colisión no aborta nada: `grant_mcp` descarta en silencio el grant que venías arrastrando, por considerarlo redundante, y tu alcance se achica de todos los agentes a ese subconjunto sin más aviso que el `grant_warnings` del report. Las dos cifras no se retipean acá: las deriva del árbol `GrantMcpReachesEveryAgentTest` (`tests/test_manual_figures.py`), que además corre el grant de verdad para comprobar que «todos» sigue siendo todos, y falla el día que alguna deje de coincidir.

`pegasus mcp` es la palanca para eso. A diferencia de los MCPs que Pegasus instala, acá no hay elección por agente: la clave se otorga a todos los agentes por igual, porque hacerlo agente por agente volvería tediosa la tarea de sumar un MCP más.

```sh
pegasus mcp grant --cli opencode sentry-mcp
pegasus mcp list --cli opencode
pegasus mcp revoke --cli opencode sentry-mcp
```

`grant` rechaza una clave que tu propia configuración de OpenCode no declara bajo `mcp` — nombra ahí mismo cuáles sí declara, para que un error de tipeo no termine en un permiso que nadie nota que falta. `revoke` sobre una clave que nunca otorgaste no es un error: informa que ya estaba en ese estado y sale en `0`. `list` muestra lo que está otorgado ahora, y de las claves que tu configuración declara y todavía no otorgaste, cuáles `grant` aceptaría tal como está la instalación — nunca una que `grant` fuera a rechazar. Una clave declarada que Pegasus ya alcanza por agente (un servidor propio de esta instalación, o una clave ya ligada) se muestra aparte, marcada como ya cubierta, en vez de desaparecer del listado sin explicación. `list` no escribe nada: lee el journal y tu configuración, y deja `opencode.json` exactamente como estaba.

`pegasus mcp grant` y `pegasus mcp revoke` reaplican la configuración renderizada al terminar — igual que `pegasus install` — así que el cambio ya queda escrito en `opencode.json`. Cuál de los subcomandos escribe y cuál no, no se afirma acá de memoria: lo mide `ManualSaysWhichMcpSubcommandsRewriteTheConfigurationTest` (`tests/test_manual_command_surface.py`), corriendo cada uno contra una instalación real y comparando el archivo renderizado byte a byte de un lado y del otro de la llamada. Como con cualquier cambio a los agentes, hace falta reiniciar OpenCode para que lo lea: sigue leyendo la configuración de agentes una sola vez, al arrancar. `pegasus update --cli opencode` reaplica las claves otorgadas junto con el resto de la selección, sin flags.

Lo mismo está disponible desde la TUI (`pegasus`, sin argumentos), en el menú principal → `Grant MCP servers` → elegí el CLI. La pantalla lista las claves que `mcp list` reporta como `available` para esa instalación, cada una tildada o no según si ya está otorgada; espacio o enter la tilda o destilda, y `Continue` aplica de una sola vez todo lo otorgado y todo lo revocado — y sólo cuenta como aplicado lo que su propio llamado efectivamente logró, nunca lo pedido sin más si algo se rechazó mientras tanto. Si no hay ningún servidor propio para mostrar, la pantalla explica cuál de dos motivos es: no instalaste ninguno todavía (instalalo en OpenCode como siempre lo harías, y volvé acá a otorgarlo), o ya instalaste uno pero Pegasus ya lo alcanza por agente y nombra cuál — ahí no hay nada para hacer, no es que la detección haya fallado. Si la instalación tiene una ligadura sin resolver (`--mcp id=<clave>` sin la clave nunca registrada), la pantalla lo dice en vez de listar nada: mientras eso siga así, `grant`/`revoke` se niegan para cualquier clave, no sólo la ligada, y hace falta resolverlo primero (ver más arriba). El resultado avisa el mismo reinicio que ya se menciona arriba.

Si más adelante un `install` liga un servidor propio de Pegasus (`--mcp id=<clave>`) bajo la misma cadena que una clave que ya habías otorgado, esa clave otorgada queda redundante y el `install` la descarta en vez de fallar — el servidor sigue siendo alcanzable a través de los agentes que ahora lo declaran. El comando avisa qué clave descartó; si no era lo que querías, volvé a otorgarla con `pegasus mcp grant`.

## Dar acceso a un directorio de trabajo propio

OpenCode pregunta por un permiso separado, `external_directory`, apenas una herramienta de archivo o `bash` apunta a algo fuera del worktree del proyecto. Cada agente que Pegasus instala ya trae la excepción que necesita para leer sus propias skills, pero un directorio que vos necesitás — un worktree enlazado, un árbol de scratch fuera del repo — es un dato que Pegasus no puede conocer de antemano, y no hay forma de agregarlo a mano: Pegasus reclama la entrada completa de cada agente en `opencode.json`, así que una excepción escrita a mano la pisa el próximo `install`/`update`.

```sh
pegasus directory grant --cli opencode /home/vos/worktrees/otro-repo
pegasus directory revoke --cli opencode /home/vos/worktrees/otro-repo
```

`grant` acepta cualquier ruta absoluta que no sea la raíz del filesystem (`/`), no contenga un metacarácter de glob (`*`, `?`, `[`, `]`), y no sea el directorio de configuración de OpenCode, el directorio de datos propio de Pegasus (donde vive su journal), ni un ancestro de cualquiera de los dos. El de configuración guarda tus propios servidores; el de datos guarda el registro que `uninstall` usa para decidir qué borrar, así que darle escritura a un agente ahí equivaldría a dejarlo decidir qué se borra en la próxima desinstalación. Fuera de esas restricciones, una ruta relativa o con `..` también se rechaza; el resto se acepta, incluida una ruta fuera de tu home. La ruta se normaliza antes de guardarse (una barra final o `//` repetidas colapsan a la misma forma), así que `grant`/`revoke` con distinta grafía de la misma ruta se reconocen entre sí. `revoke` sobre una ruta que nunca otorgaste no es un error: informa que ya estaba en ese estado y sale en `0`.

A diferencia de un MCP propio, un directorio otorgado alcanza a **todo** agente, primario o sub-agente por igual — no hay recorte por agente que preservar, así que no hace falta. Los dos reaplican la configuración renderizada al terminar, igual que `pegasus mcp grant`, así que el cambio ya queda escrito en `opencode.json` y sobrevive a cada `install`/`update` posterior sin que haga falta repetirlo. Como con cualquier cambio a los agentes, hace falta reiniciar OpenCode para que lo lea.

Un directorio que otorgás no se renderiza como una pregunta: queda como una entrada propia dentro de `external_directory`, `"/home/vos/worktrees/otro-repo/*": "allow"`, escrita después de la línea de base `"*": "ask"` — y como el runtime resuelve por la última regla que coincide, esa entrada gana. Lo que sigue preguntando es todo lo demás fuera del worktree: un directorio que no otorgaste le va a pedir confirmación a la persona cada vez que un agente lo necesite. La excepción a eso es una corrida no interactiva con `--auto`, `--yolo`, o el flag del runtime que saltea permisos -- ahí el pedido se publica y se auto-aprueba solo, sub-agentes incluidos, así que bajo esos flags la línea de base tiene el mismo efecto práctico que un `allow`. La entrada que se cita acá sale del `opencode.json` que este mismo grant escribe en disco, con la ruta del ejemplo de arriba: la deriva `ManualSaysHowAGrantedDirectoryIsRenderedTest` (`tests/test_manual_command_surface.py`).

## Usarlo todos los días

1. Abrí OpenCode dentro del repositorio en el que vas a trabajar.
2. Para un cambio con alcance real, iniciá el flujo SDD (`sdd-init`, `sdd-new` o `sdd-ff`) y completá el pre-chequeo de sesión que pide el orquestador.
3. Dejá que explore, propuesta, spec, diseño y tareas aclaren el cambio antes de `sdd-apply`.
4. Implementá por unidades de trabajo y cerrá con `sdd-verify` cuando estén completas las tareas; `sdd-verify` es la única autoridad de readiness.

Los comandos distribuidos son `sdd-init`, `sdd-new`, `sdd-ff`, `sdd-continue`, `sdd-apply`, `sdd-status`, `sdd-verify`, `sdd-archive`, `sdd-onboard`, `sdd-explore`, además de `context-load`, `context-save`, `handoff-load`, `handoff-save`, `skill-creator` y `skill-registry`. Podés leer su contenido en `~/.config/opencode/commands/` antes de usarlos.

## Elegir proveedor, modelo y esfuerzo

Pegasus distribuye roles, no credenciales ni modelos: ningún agente trae uno asignado por defecto. En el primer arranque, ejecutá `/connect` dentro de OpenCode para configurar las credenciales del proveedor, y `/models` para elegir el modelo que querés usar de forma general. Esas dos decisiones son tuyas y OpenCode las guarda en su propia configuración; Pegasus no las lee ni las reproduce.

Para asignar un modelo puntual a un agente, Pegasus tiene su propio comando, separado del `/models` de OpenCode. Lo acepta **todo** agente que esta release embarca —el orquestador, `king-pegasus` y los especialistas sin fase incluidos—, sin excepción y sin que el número cambie la regla: hoy son **16 agentes**. Ni la regla ni la cifra se retipean acá: las deriva del árbol `EveryShippedAgentAcceptsAModelAssignmentTest` (`tests/test_manual_figures.py`), que además le pide una asignación a cada agente embarcado para comprobar que ninguno la rechaza. Se usa así:

```sh
pegasus models set --cli opencode --agent sdd-apply --model anthropic/claude-sonnet-5 --effort high
pegasus models list --cli opencode
pegasus models unset --cli opencode --agent sdd-apply
```

Una asignación se guarda de inmediato, pero no queda escrita en la configuración de OpenCode hasta que un comando la renderice. `models set` y `models unset` avisan esto siempre, sin fijarse en qué tiene la instalación, y nombran `pegasus install --cli opencode`, que es el que el propio aviso te dice que corras. No es el único que la escribe: `pegasus update --cli opencode`, `pegasus mcp grant` y `pegasus directory grant` reaplican la configuración entera y se llevan con ellos la asignación guardada. Que el aviso salga siempre, y que cada una de esas rutas la escriba de verdad, los corre contra una instalación real `ManualSaysWhenAModelAssignmentReachesTheConfigurationTest` (`tests/test_manual_command_surface.py`), leyendo el archivo renderizado de un lado y del otro de cada llamado. No pongas tokens ni credenciales en el repo, en prompts, ni en comandos versionados.

## Verificar el estado

```sh
pegasus doctor
```

Reporta qué CLIs anfitrionas detecta y qué drift hay entre lo instalado y lo que el contenido actual generaría. No reemplaza una prueba de comportamiento.

Para chequear además que cada servidor MCP instalado arranca y contesta el handshake de MCP:

```sh
pegasus doctor --start-mcp-servers
```

Tiene sentido correrlo después de instalar servidores MCP, o cuando un cliente reporta que uno no conecta. A diferencia de `doctor` a secas, este flag ejecuta los comandos que la configuración tiene guardados — por eso no es el comportamiento por defecto.

Por cada servidor que este flag arranca informa uno de estos estados: `ok` (contestó el handshake), `timeout` (arrancó pero nunca contestó), `exited` (terminó antes de contestar), `invalid` (contestó algo que no es una respuesta MCP válida), `not-found` (no se pudo arrancar), `unreadable` (no se pudo leer la configuración de donde sale el comando) o `missing` (esa configuración ya no tiene la entrada que el journal reclama). Un servidor configurado como remoto no se arranca y se informa `remote`. Y uno atado a una clave que administrás vos (`--mcp id=<clave>`) tampoco aparece en esa lista: se informa aparte, con estado `bound`, y eso lo dice también un `pegasus doctor` sin el flag, porque no hay proceso que arrancar — es el estado normal de una instalación así, no una falla. Ninguno de esos estados se retipea acá: los deriva del árbol `ManualSaysEveryStatusDoctorCanReportTest` (`tests/test_manual_command_surface.py`), que además instala un servidor atado y uno remoto de verdad para comprobar dónde cae cada uno.

`pegasus repair --cli opencode` saca dos cosas que `doctor` sólo nombra, con `--dry-run` disponible para ver antes qué se va a remover: las entradas de `directories_quarantined` -- un `granted_directories` editado a mano en el journal que no pasó la validación y por eso no le concede nada a ningún agente -- y los directorios vacíos que `doctor` reporta bajo `unprunable_empty_directories`, de una instalación anterior a 5.28.0 que la poda automática nunca puede alcanzar. Toma un snapshot del journal antes de escribir, así que `pegasus restore` deshace la parte del journal igual que deshace cualquier otro comando; un directorio vacío borrado no se restaura -- no hay nada que recuperar más allá de un `mkdir`. Si `doctor` reporta `directories_not_walked`, hay un subárbol detrás de un symlink que ni `doctor` ni `repair` pudieron recorrer, y `repair` lo dice en su propio reporte en vez de sugerir que ahí no queda nada.

## Mantener Pegasus al día

Son dos actualizaciones distintas y conviene no confundirlas: `pegasus update --cli opencode` reaplica en OpenCode la selección que esa instalación ya tiene registrada, y `pegasus upgrade` no toca ninguna instalación — reemplaza el binario `pegasus` en sí. Para saber desde qué versión partís, `pegasus -V` (o `pegasus --version`) la contesta sin abrir tu home, sin leer el journal y sin resolver ningún adapter: es la versión del binario y no la de ninguna instalación suya, así que sigue contestando en una máquina donde la instalación esté rota, que es justo cuando hace falta.

```sh
pegasus upgrade --dry-run
pegasus upgrade
```

No lleva `--cli` porque no se trata de ninguna instalación puntual. Se niega antes de bajar un solo byte si no está corriendo desde un ejecutable instalado, si el destino no es escribible, si el archivo que hay ahí es de otra persona, o si no llega a la red para averiguar cuál es la última versión publicada. Recién después baja el checksum y el binario, lo verifica contra ese checksum, y lo pone en su lugar con un único rename atómico: un checksum que no coincide o una escritura que falla dejan intacto el binario con el que arrancaste, así que nunca hay un momento sin un `pegasus` funcionando en disco. Estar ya en la última versión publicada no es un error — lo informa y sale en `0`. Después hace falta reiniciar Pegasus: el proceso que acaba de hacer el upgrade sigue siendo, en memoria, la versión vieja.

Lo mismo está en la TUI (`pegasus`, sin argumentos), en el menú principal → `Upgrade`. Al abrir el menú, si hay un release más nuevo publicado que el binario que estás corriendo, el aviso aparece arriba de todo; ese chequeo corre en segundo plano, no bloquea el menú, y falla en silencio ante cualquier problema de red.

## Deshacer

- `pegasus restore [generación]` vuelve al estado exacto anterior a un comando (o a una generación puntual del historial de snapshots).
- `pegasus uninstall --cli opencode` retira solo lo que el journal reclama como propio.

El journal vive en `$XDG_DATA_HOME/pegasus-harness/journal-v4.json` (o `~/.local/share/pegasus-harness/journal-v4.json`), en un directorio `0700` con el archivo en `0600`. Lo que decide qué se toca es **el journal y nada más**: un archivo que Pegasus nunca creó no se toca nunca, y uno que el journal reclama se retira aunque vos lo hayas editado después. Nunca uses `restore` ni `uninstall` para borrar configuración que ya era tuya.

Una edición tuya sobre un archivo que Pegasus instaló no sobrevive: `install` y `update` la reescriben con la versión del release, y `uninstall` la borra sin aviso equivalente al `overwritten` que sí te dan los otros dos. Lo que te recupera es `pegasus restore`, con cinco generaciones de historial y no más. El motivo de esa política, los dos huecos del aviso y qué hacer en cada caso están en [docs/arquitectura/arquitectura.md#limitaciones-aceptadas](docs/arquitectura/arquitectura.md#limitaciones-aceptadas).

## Próximo paso

- Para el recorrido completo de instalación: [INSTALL.md](INSTALL.md).
- Para instalación asistida por un agente: [INSTALL_BY_AGENT.md](INSTALL_BY_AGENT.md).
- Para la arquitectura y las decisiones de diseño: [docs/arquitectura/arquitectura.md](docs/arquitectura/arquitectura.md).
