# ADR 0003 — Por qué DARQ no se llama "harness"

Estado: aceptada

## Contexto

La dirección ejecutiva — la dirección de la que depende la directora de quien impulsa DARQ — ya
presentó su propia iniciativa con ese nombre: "ASI Harness", 43 slash commands construidos sobre
Claude que aplican de forma intensiva el estándar de versiones ASI. Es una iniciativa con
visibilidad y con dueño.

Si DARQ se presenta también como un "harness", el nombre por sí solo lo enmarca como una
alternativa a esa iniciativa — o peor, como una competencia directa contra algo que ya presentó la
propia dirección ejecutiva. Dado quién presentó la otra, esa lectura no le gana a DARQ un argumento
técnico: le cuesta la adopción antes de que nadie llegue a evaluar el contenido.

## Decisión

DARQ no se nombra ni se presenta como un harness. Se presenta como **la distribución institucional
de la DGISIS**, construida sobre Pegasus Harness.

"DARQ" expande a **DGISIS-GO Arquitectura**. El alcance declarado es la DGISIS y las GO que la
componen — no la totalidad del organismo, y no un reemplazo de lo que ya construyó o construya
cualquier otra área.

La palabra "distribución" acá no describe el mecanismo técnico con el que DARQ consume el motor —
eso es harina de otro costal: al momento de escribir esta ADR, DARQ era una distribución en sentido
técnico (release ajeno fijado por pin); desde el fork completo (ver `docs/adr/0005-fork-no-distribucion.md`)
ya no lo es, y DARQ mantiene su propia copia del motor. Lo que la palabra "distribución" sigue
describiendo con exactitud, e independientemente de ese cambio de mecanismo, es el sentido
institucional: DARQ pone a disposición de la DGISIS y sus GO un producto con un origen declarado y
un alcance declarado. Un fork también tiene, por definición, un upstream obvio (Pegasus Harness) y
un alcance obvio (quien lo mantiene y para quién sirve el contenido). Un harness nuevo, en cambio,
se lee como un producto que compite por el mismo espacio que otro harness ya ocupa. Nombrarla
"distribución institucional de la DGISIS" sigue haciendo explícitos, en el nombre mismo, los dos
límites que la mantienen fuera de esa disputa: de dónde viene el motor y a quién sirve el contenido.

## Consecuencias

DARQ queda protegida de leerse como competencia de "ASI Harness" sin tener que argumentarlo cada vez
que se presenta — el nombre ya lo dice. El costo es que el nombre compromete el alcance: DARQ no
puede, más adelante, presentarse como solución para áreas fuera de la DGISIS sin romper la lectura
que este mismo ADR construyó. Ampliar el alcance es una decisión que hay que tomar y anunciar
explícitamente, no algo a lo que DARQ pueda derivar en silencio.

## Referencias

- `docs/adr/0002-marca-sin-expansion.md` para la razón de fondo, de la que esta decisión de nombre
  es una consecuencia directa: DARQ es marca y contenido, no un producto que compita por
  capacidades.
- `docs/adr/0005-fork-no-distribucion.md` para el cambio de mecanismo (de distribución técnica a fork) que
  esta ADR distingue del sentido institucional de la palabra "distribución".
