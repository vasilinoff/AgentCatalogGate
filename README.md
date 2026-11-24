# Agent Catalog Gate

A Claude Code hook that makes every subagent call say what kind of task it is, and run
on the model and effort that kind of task deserves.

## The problem

When Claude Code delegates to a subagent, the subagent inherits the parent's model unless
the call says otherwise. In practice the call rarely says otherwise. In one person's
history of 1,189 subagent calls across 366 sessions, 80% set no model at all: reading a
ticket to classify it ran on the same top model, at the same effort, as an architecture
review. A rule in `CLAUDE.md` ("pick a cheaper model for mechanical work") helps for a
while, then fades in a long session, because the model is the one that has to remember it.

## The idea

Move the rule out of the model's memory and into a program that runs on every call.

1. **A catalog of task categories** (`agent-catalog.json`): each has a slug, a sentence
   saying when it applies, a model, an effort, and examples. The starting set was mined from
   real history (see below):

   | Category | Model / effort | For |
   |---|---|---|
   | `triage`, `lookup` | haiku / low | classify a ticket, find a file, read a page |
   | `chore` | sonnet / low | strip comments, rename, reformat |
   | `test-qa`, `implement`, `research`, `data`, `media-build`, `persona` | sonnet / medium | the bulk of the work |
   | `review`, `copy`, `critique`, `design` | opus / high | finding bugs, text people read, judging design, deciding |

2. **A PreToolUse hook on `Agent`** (`hooks/agent-catalog-gate.py`) that refuses a call
   unless its description starts with `[slug]` from the catalog and its `model` and `effort`
   are that category's. The refusal message carries the whole catalog, so the model
   corrects the call on the next try without having to remember anything.

3. **The catalog grows itself.** When no category fits, the refusal says so: add one to the
   catalog first, then call again. Claude decides what the new category is and what it
   should run on; the next call of that kind finds it there.

4. **Escape hatches, all explicit.** `(override: reason)` in the description allows a
   different model or effort for one call. Forks, named agents that set their own model in
   `.claude/agents/*.md`, and plugin agents pass untouched. A missing or broken catalog
   never blocks work: the gate lets the call through.

5. **A log** (`~/.claude/agent-calls.log`) of every decision, tab-separated, to re-read
   now and then and merge or split categories.

Why a hook and not a reminder: a model can't notice that it has stopped following an
instruction, because the check would live in the same context that drifted. A hook runs
outside the model, every time, and its refusal puts the rule back in front of it exactly
when it matters.

## Install

```bash
git clone https://github.com/vasilinoff/AgentCatalogGate ~/AgentCatalogGate
cp ~/AgentCatalogGate/hooks/agent-catalog-gate.py ~/.claude/hooks/
cp ~/AgentCatalogGate/agent-catalog.example.json ~/.claude/agent-catalog.json
```

Then add the hook to `~/.claude/settings.json`, next to any `PreToolUse` hooks you have:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Agent",
        "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/agent-catalog-gate.py", "timeout": 5 }]
      }
    ]
  }
}
```

A new session picks it up. One line in `CLAUDE.md` helps the model get it right the first
time instead of after a refusal:

> Every generic Agent call starts its description with a `[slug]` from
> `~/.claude/agent-catalog.json` and sets that category's model and effort. No category
> fits: add one to the catalog first.

That line also matters for effort: Claude Code's own guidance is to set a subagent's effort
only when the user or `CLAUDE.md` asks for it, and this is that ask.

## Seed the catalog from your own history

```bash
python3 tools/mine-agent-calls.py          # counts + 60 random calls on generic agents
python3 tools/mine-agent-calls.py --all    # every one
```

It reads your local transcripts in `~/.claude/projects/` and prints what you actually
delegated. Hand the output to Claude and ask it to group the calls into categories for the
catalog; the example catalog came out of exactly that.

## Check

```bash
python3 test_gate.py
```

Eleven cases against the example catalog in a throwaway `HOME`: no category, unknown
category, missing effort, wrong model, a good call, an override, a fork, a named agent, a
plugin agent, a generic agent without a category, and a broken catalog.

## Requirements

Claude Code with hooks, `python3` (standard library only).

## License

MIT
