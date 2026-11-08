// Drives engram.ts through its start-up for each scenario read from stdin and
// prints what it did. Run under `node --experimental-strip-types`; argv:
// <plugin.ts>. stdin: a JSON array of `{env: {...}}` (ENGRAM_PORT and the
// ENGRAM_PORT_* test seams). `fetch` and `Bun.spawn` are recorded, never real.
// Prints one `{ fetched: [<port>...], spawned: [{cmd, port}] }` per scenario.
// The plugin keeps no state between scenarios: it resolves the port per request.
import { readFileSync } from "node:fs"
import { pathToFileURL } from "node:url"

let fetched = []
let spawned = []
globalThis.Bun = {
  which: () => process.env.FAKE_WHICH_ENGRAM ?? null, // test seam: the `engram` found on PATH
  spawnSync: () => ({ exitCode: 1, stdout: Buffer.from("") }),
  spawn: (cmd, opts) => {
    spawned.push({ cmd, port: opts?.env?.ENGRAM_PORT ?? null })
    return {}
  },
  file: () => ({ exists: async () => false }),
}
globalThis.fetch = async (url) => {
  fetched.push(Number(new URL(url).port))
  // Health fails until a server was "started", so the plugin has to start one.
  if (url.endsWith("/health")) return { ok: spawned.length > 0 }
  return { ok: true, json: async () => ({ context: "" }) }
}

const mod = await import(pathToFileURL(process.argv[2]).href)
const results = []
for (const scenario of JSON.parse(readFileSync(0, "utf8"))) {
  for (const key of ["ENGRAM_PORT", "ENGRAM_PORT_PROC_TCP4", "ENGRAM_PORT_PROC_TCP6", "ENGRAM_PORT_FALLBACK_BASE"]) {
    delete process.env[key]
  }
  Object.assign(process.env, scenario.env)
  fetched = []
  spawned = []
  const plugin = await mod.Engram({ directory: process.cwd() })
  await plugin.event({
    event: { type: "session.created", properties: { info: { id: "root1", parentID: undefined, title: "root" } } },
  })
  await plugin["chat.message"]?.(
    { sessionID: "root1" },
    { message: { role: "user" }, parts: [{ type: "text", text: "a prompt that is long enough to be recorded" }] },
  )
  results.push({ fetched: [...new Set(fetched)], spawned: spawned.filter((s) => s.cmd[1] === "serve") })
}
console.log(JSON.stringify(results))
