#!/usr/bin/env python3
"""PreToolUse gate on Agent: every generic subagent call names a task category from
~/.claude/agent-catalog.json and runs on that category's model and effort.

- description starts with "[slug]" and slug is in the catalog;
- model and effort are set and equal the category's, unless the description says
  "(override: <reason>)";
- forks and named agents with their own .claude/agents/*.md (or plugin "x:y") pass:
  their model is set where they are defined.
Every decision is appended to ~/.claude/agent-calls.log, the input for re-seeding the
catalog later. A broken catalog never blocks work: the gate lets the call through.
"""
import json, os, re, sys, time
from pathlib import Path

HOME = Path.home()
CATALOG = HOME / ".claude/agent-catalog.json"
LOG = HOME / ".claude/agent-calls.log"
GENERIC = {"", "general-purpose", "claude", "Explore", "Plan"}


def named_agent(kind, cwd):
    if ":" in kind:                       # plugin agent, defined by its plugin
        return True
    dirs = [HOME / ".claude/agents"] + [p / ".claude/agents" for p in [Path(cwd), *Path(cwd).parents]]
    return any((d / f"{kind}.md").exists() for d in dirs)


def check(inp, cwd, catalog):
    kind = inp.get("subagent_type") or ""
    if kind == "fork" or (kind not in GENERIC and named_agent(kind, cwd)):
        return None, kind or "-"
    cats = catalog["categories"]
    desc = inp.get("description", "")
    m = re.match(r"\s*\[([a-z0-9-]+)\]", desc)
    table = "\n".join(f"  [{s}] {c['model']}/{c['effort']}: {c['when']}" for s, c in cats.items())
    if not m:
        return (f"Agent call needs a task category: start description with [slug] from "
                f"{CATALOG}:\n{table}\nNone fits: add a category to that file first, then call again."), "?"
    slug = m.group(1)
    if slug not in cats:
        return (f"Unknown category [{slug}]. Add it to {CATALOG} (when, model, effort, examples) "
                f"or use one of:\n{table}"), slug
    want = cats[slug]
    model, effort = inp.get("model"), inp.get("effort")
    if not model or not effort:
        return (f"[{slug}] runs on model={want['model']} effort={want['effort']}: set both "
                f"on the Agent call."), slug
    if (model, effort) != (want["model"], want["effort"]) and "(override:" not in desc:
        return (f"[{slug}] is model={want['model']} effort={want['effort']}, call has "
                f"{model}/{effort}. Use the category's, or add '(override: reason)' to the "
                f"description."), slug
    return None, slug


def main():
    data = json.load(sys.stdin)
    inp = data.get("tool_input") or {}
    try:
        catalog = json.loads(CATALOG.read_text())
        reason, slug = check(inp, data.get("cwd") or os.getcwd(), catalog)
    except Exception as e:                # catalog missing or malformed: never block work
        reason, slug = None, f"gate-error:{e.__class__.__name__}"
    try:
        with LOG.open("a") as f:
            f.write("\t".join([time.strftime("%Y-%m-%d %H:%M"), "deny" if reason else "allow", slug,
                               inp.get("subagent_type") or "-", inp.get("model") or "-",
                               inp.get("effort") or "-", (inp.get("description") or "").replace("\t", " ")]) + "\n")
    except OSError:
        pass
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    main()
