"""A dry run never presses anything on a video an earlier run already uploaded (resume path)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

EXT = Path(__file__).parent.parent / "tools" / "postq" / "ext"

# background.js in a vm with a stub `chrome`; checkOnEditPage gets a fake page that records each step.
HARNESS = r"""
const fs = require('fs'), vm = require('vm'), path = require('path');
const ext = process.argv[1], dry = process.argv[2] === 'dry';
const any = () => new Proxy(function () {}, { get: () => any(), apply: () => any() });
const chrome = new Proxy({}, { get: () => any() });
const ctx = { chrome, console, URL, fetch: async () => ({ ok: true, json: async () => ({}) }), setTimeout: () => 0,
  setInterval: () => 0, importScripts: (f) => vm.runInContext(fs.readFileSync(path.join(ext, f), 'utf8'), ctx) };
ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(ext, 'background.js'), 'utf8') + ';progress = async () => {};globalThis.check = checkOnEditPage;', ctx);
ctx.setTimeout = (fn) => (setImmediate(fn), 0);  // waits pass at once; load-time timers stay stubbed
const steps = [];
const pg = {
  go: async (url) => { steps.push(['go', url]); },
  send: async (name) => { steps.push(['send', name]); },
  step: async (name) => {
    steps.push([name]);
    if (name === 'openDraft') return steps.filter((s) => s[0] === 'openDraft').length === 1;  // a draft, once
    if (name === 'submit') return { button: 'Schedule', confirm: 'Video scheduled', url: null };
    if (name === 'verify') return [];
    return {};
  },
};
const item = { id: 'x1', platform: 'youtube', dry_run: dry, cover: null };
ctx.check(item, pg, 'zJuy23bjJ1U', 'https://youtube.com/shorts/zJuy23bjJ1U', Date.now() + 86400000, 'note')
  .then((r) => console.log(JSON.stringify({ r, steps: steps.map((s) => s[0]) })))
  .catch((e) => console.log(JSON.stringify({ error: e.message })));
"""


def run(mode):
    out = subprocess.run(["node", "-e", HARNESS, str(EXT), mode], capture_output=True, text=True, check=True).stdout
    res = json.loads(out.strip().splitlines()[-1])
    assert "error" not in res, res["error"]
    return res


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_dry_run_resume_presses_nothing():
    res = run("dry")
    assert res["r"]["status"] == "dry-run"
    assert not {"submit", "visibility", "verify", "send"} & set(res["steps"])


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_real_resume_still_schedules_a_draft():
    res = run("real")
    assert "submit" in res["steps"]
    assert res["r"]["status"] == "scheduled"
