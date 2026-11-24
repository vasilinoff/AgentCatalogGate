#!/usr/bin/env python3
"""python3 test_gate.py — runs the hook on ten synthetic Agent calls against the example
catalog, with HOME pointed at a temporary folder so your own catalog and log are untouched."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
home = Path(tempfile.mkdtemp())
(home / ".claude/agents").mkdir(parents=True)
(home / ".claude/agents/tracker.md").write_text("---\nmodel: haiku\n---\n")
shutil.copy(ROOT / "agent-catalog.example.json", home / ".claude/agent-catalog.json")


def gate(inp):
    out = subprocess.run([sys.executable, ROOT / "hooks/agent-catalog-gate.py"],
                         input=json.dumps({"tool_name": "Agent", "cwd": str(home), "tool_input": inp}),
                         capture_output=True, text=True, env={**os.environ, "HOME": str(home)})
    assert out.returncode == 0, out.stderr
    return "deny" if out.stdout.strip() else "allow"


cases = [
    ({"description": "Localize Spanish"}, "deny"),                                         # no category
    ({"description": "[poetry] A poem", "model": "opus", "effort": "high"}, "deny"),       # unknown category
    ({"description": "[copy] Localize Spanish", "model": "opus"}, "deny"),                 # effort missing
    ({"description": "[copy] Localize Spanish", "model": "sonnet", "effort": "high"}, "deny"),  # wrong model
    ({"description": "[copy] Localize Spanish", "model": "opus", "effort": "high"}, "allow"),
    ({"description": "[copy] Fix typos (override: trivial)", "model": "haiku", "effort": "low"}, "allow"),
    ({"subagent_type": "fork", "description": "anything"}, "allow"),
    ({"subagent_type": "tracker", "description": "Close a card"}, "allow"),               # named agent
    ({"subagent_type": "someplugin:agent", "description": "x"}, "allow"),                 # plugin agent
    ({"subagent_type": "general-purpose", "description": "x", "model": "opus", "effort": "high"}, "deny"),
]
for inp, want in cases:
    got = gate({"prompt": "x", **inp})
    assert got == want, (inp, got)

# A broken catalog never blocks work.
(home / ".claude/agent-catalog.json").write_text("{not json")
assert gate({"prompt": "x", "description": "anything"}) == "allow"

log = (home / ".claude/agent-calls.log").read_text().splitlines()
assert len(log) == len(cases) + 1
shutil.rmtree(home)
print(f"ok: {len(cases) + 1} cases")
