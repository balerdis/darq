# Threat Matrix for Process and Repository Boundaries

A design needs this file only when it touches one of these boundaries: routing; shell commands or
subprocesses; automation of version control or of pull requests; the classification of files as executable;
integration with other processes.

## What an applicable row owes

For every row marked `Applicable`, the design spells out three things: the safe behavior expected, the
failure behavior expected, and the concrete boundary the test exercises. Those cases travel into `tasks.md`
exactly as written, and during implementation each mapped RED test gets written ahead of any production
change.

## The matrix

Each row's Applicability cell holds `Applicable`, or an explicit `N/A` together with its reason. An `N/A`
row produces no task and no test; never invent either for it.

| Boundary | Minimum adversarial cases | Applicability | Design response | Planned RED tests |
|---|---|---|---|---|
| Git repository selection | `git -C`, relative paths, absolute paths | Applicable / N/A: reason | Which repository and working directory hold authority | One for every selector that applies |
| Commit state | staged, `commit -a`, empty index | Applicable / N/A: reason | How the index and the worktree are treated | One for every state that applies |
| Push state | tracking branch, first push, explicit refspec | Applicable / N/A: reason | How the destination and the ref get resolved | One for every state that applies |
| PR commands | explicit `--head`, environment prefix, composed commands | Applicable / N/A: reason | How arguments are put together, and who owns each of them | One for every form that applies |
| Documentation-like paths | `requirements.txt`, `CMakeLists.txt`, executable Markdown/MDX, `README.sh` | Applicable / N/A: reason | How each path is classified, and where execution may happen | One for every class that applies |

## When none of it applies

A design that crosses none of these boundaries writes the matrix down as not applicable and leaves it at
that, without growing it.
