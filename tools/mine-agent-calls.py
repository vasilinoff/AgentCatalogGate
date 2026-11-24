#!/usr/bin/env python3
"""List every subagent call in your Claude Code history, to seed or re-check the catalog.

    python3 tools/mine-agent-calls.py            # summary + 60 random generic calls
    python3 tools/mine-agent-calls.py --all      # every generic call, one per line

Reads ~/.claude/projects/*/*.jsonl (local transcripts) and nothing else. Prints the
subagent types and models used, then the description and the start of the prompt of
calls on generic agents: the ones a category should cover. Group those by hand (or ask
Claude to) into categories for agent-catalog.json.
"""
import collections, glob, json, os, random, sys

GENERIC = {"-", "general-purpose", "claude", "Explore", "Plan"}


def calls():
    for path in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
        with open(path, errors="ignore") as f:
            for line in f:
                if '"tool_use"' not in line:
                    continue
                try:
                    content = json.loads(line).get("message", {}).get("content")
                except json.JSONDecodeError:
                    continue
                for c in content if isinstance(content, list) else []:
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") in ("Agent", "Task"):
                        i = c.get("input", {})
                        yield (i.get("subagent_type") or "-", i.get("model") or "-",
                               i.get("description", ""), (i.get("prompt") or "")[:100].replace("\n", " "))


def main():
    rows = list(calls())
    print(f"{len(rows)} calls")
    print("by agent type:", collections.Counter(r[0] for r in rows).most_common(15))
    print("by model:     ", collections.Counter(r[1] for r in rows).most_common())
    generic = [r for r in rows if r[0] in GENERIC]
    print(f"\n{len(generic)} on generic agents:")
    sample = generic if "--all" in sys.argv else random.Random(1).sample(generic, min(60, len(generic)))
    for kind, model, desc, prompt in sample:
        print(f"{model:7} | {desc[:55]:55} | {prompt}")


if __name__ == "__main__":
    main()
