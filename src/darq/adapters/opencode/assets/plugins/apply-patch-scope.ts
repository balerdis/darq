/** Say what `apply_patch` can reach, so its opening imperative is not read as a ban on the shell. */
import type { Plugin } from "@opencode-ai/plugin"

// Why this plugin exists at all.
//
// The runtime folds `edit`, `write` and `apply_patch` onto a single `edit`
// permission when it decides which tools to send to the model. Granting `edit`
// therefore hands over `apply_patch` as well, and there is no way to withhold
// that one tool without withholding editing entirely -- which is not a trade
// anyone wants. So the tool arrives whatever the permissions say, and its
// description arrives with it.
//
// That description opens with an imperative telling the model to use
// `apply_patch` to edit files. A model read that as a developer-priority
// instruction outranking its system prompt and refused to edit a file on
// another host over SSH, even though the person had explicitly authorized the
// change, and kept refusing after the prompt said otherwise. Text that travels
// with the tool definitions carries more weight than text that travels as a
// prompt, so the correction has to travel on the same channel. `tool.definition`
// is the only hook that writes there: whatever it leaves in `output.description`
// is what actually reaches the model.
//
// Why this appends instead of rewriting.
//
// Cutting the imperative would mean matching a sentence the runtime owns and
// may reword at any time. The day it changes, the match stops applying in
// silence and the old refusal quietly comes back. An appended paragraph stays
// true no matter how the rest of the description is worded, so it degrades into
// harmless duplication rather than into an invisible regression.
//
// The limit, which matters as much as the reason: amend the runtime's text only
// when it contradicts what this product needs *and* no permission lever exists.
// A permission that can be denied gets denied; a tool that can be withheld gets
// withheld. Only when both are closed -- as here, where the tool rides along
// with a permission we do want -- is its wording amended.

// The idempotence marker: the hook can fire more than once for the same tool,
// and the paragraph must be added exactly once. Matching on a fragment of what
// this plugin itself wrote (never on the runtime's own text) keeps the check
// under this file's control.
const SCOPE_MARKER = "writes to the local filesystem of the machine this session runs on"

// Why there is a second check, and why it anchors on one sentence instead of
// the whole description.
//
// Appending protects this plugin from a reword it does not need to react to.
// It does nothing for the two reworks that matter: the imperative this note
// corrects could be removed upstream (the note then ships to every model call
// for nothing) or reworded into something the note now contradicts. Nobody
// today has a way to learn either happened.
//
// Hashing the whole description would "solve" this by crying wolf on every
// unrelated wording change -- the description changes for a hundred reasons
// that have nothing to do with this plugin. Anchoring on the one sentence this
// plugin exists to correct means the check only fires when *that* text moves.
//
// The sentence, quoted from where it lives upstream at the OpenCode version
// this plugin was written against (v1.18.31,
// packages/opencode/src/tool/apply_patch.txt, line 1):
//
//   "Use the `apply_patch` tool to edit files."
//
// That file opens with it, `packages/opencode/src/tool/apply_patch.ts` reads
// the whole file in as the tool's `description`, and `ToolRegistry.tools` in
// `packages/opencode/src/tool/registry.ts` hands that description to this
// plugin's `tool.definition` hook verbatim, before this plugin appends
// anything. That is the only place the sentence can be checked against: the
// live `output.description` this hook already receives on every call.
const IMPERATIVE_ANCHOR = "Use the `apply_patch` tool to edit files."

// The blank line is load-bearing. This note is concatenated onto a description
// the runtime owns, and that description ends in a sentence of its own -- so
// with nothing between them the model reads `...to edit files.Scope of this
// tool:` and the correction starts inside somebody else's sentence. Everything
// after the separator is one paragraph on purpose: the remaining entries are
// line continuations, not lines, which is why the array is joined with "".
const SCOPE_NOTE = [
  "\n\n",
  `Scope of this tool: it ${SCOPE_MARKER}, as the user that session runs as, and nowhere else. It `,
  "cannot reach a file that lives on another host, and it cannot write a file owned by another user ",
  "on this one. When a request is about editing files, this tool means local files that user can ",
  "write. It is not an instruction to avoid the shell, and it does not forbid editing a remote file ",
  "over SSH with `bash`, or a privileged local file with `sudo`, when the person has authorized that ",
  "change. For a destination on another machine the shell is not a way around this tool -- it is the ",
  "only way there, and for a file this user cannot write it is the way there for the same reason. A ",
  "permission error this tool returns is a limit on this tool, not a prohibition on the change.",
].join("")

const {{program_pascal_name}}ApplyPatchScope: Plugin = async (pluginInput) => {
  // The alarm has to fire once per session, not once per `tool.definition`
  // call -- the hook can run once per model per turn, and re-announcing "the
  // imperative moved" on every one of those calls would be exactly the kind
  // of noise this project has learned to avoid ("con la escasez, lo más
  // posible"). There is no separate once-at-startup hook that sees a tool's
  // live description: the plugin factory body (this function, run once when
  // OpenCode loads the plugin) never receives one, only `tool.definition`
  // does. A closure flag scoped to this one plugin instance is what "once"
  // has to mean here.
  let premiseChecked = false

  async function checkPremise(description: string) {
    if (premiseChecked) return
    premiseChecked = true
    if (description.includes(IMPERATIVE_ANCHOR)) return
    try {
      // Best-effort, same pattern as the skill registry plugin: `opencode
      // run` and other non-TUI clients have nothing to show a toast on, and a
      // failed call here is an ordinary outcome, not a second failure to
      // report. Throwing instead was ruled out on purpose: `tool.definition`
      // runs inside `ToolRegistry.tools`, and nothing on that path catches a
      // rejection from a plugin hook -- an uncaught throw here would fail the
      // whole turn's tool list instead of raising a quiet flag on one tool.
      await pluginInput.client.tui.showToast({
        body: {
          title: "{{display_name}}: apply_patch scope note",
          message:
            'The sentence this note corrects ("' +
            IMPERATIVE_ANCHOR +
            "\") is no longer in apply_patch's description upstream. It may " +
            "have been fixed or reworded -- review whether this plugin's " +
            "scope note is still needed and still accurate.",
          variant: "warning",
        },
      })
    } catch {
      // ignore, see above
    }
  }

  return {
    "tool.definition": async (
      input: { toolID: string },
      output: { description: string; parameters: any },
    ) => {
      if (input.toolID !== "apply_patch") return
      if (typeof output.description !== "string") return
      void checkPremise(output.description)
      if (output.description.includes(SCOPE_MARKER)) return
      output.description = output.description + SCOPE_NOTE
    },
  }
}

export default {{program_pascal_name}}ApplyPatchScope
