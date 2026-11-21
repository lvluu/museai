"""A posting tab that Chrome swaps for a new id (prerender activation) is followed, not lost."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

EXT = Path(__file__).parent.parent / "tools" / "postq" / "ext"

# background.js in a vm with a stub `chrome`: only tabs 1 (until swapped) and 2 exist.
HARNESS = r"""
const fs = require('fs'), vm = require('vm'), path = require('path');
const ext = process.argv[1];
const any = () => new Proxy(function () {}, { get: () => any(), apply: () => any() });
let onReplaced, live = new Set([1]);
const calls = [];
const need = (id) => { if (!live.has(id)) throw new Error(`No tab with id: ${id}.`); };
const chrome = new Proxy({
  tabs: {
    onReplaced: { addListener: (fn) => { onReplaced = fn; } },
    get: async (id) => { need(id); return { id, url: 'https://www.tiktok.com/x', status: 'complete' }; },
    update: async (id) => { need(id); calls.push(['update', id]); },
  },
  scripting: { executeScript: async ({ target }) => { need(target.tabId); calls.push(['exec', target.tabId]); return [{ result: { value: target.tabId } }]; } },
}, { get: (t, k) => (k in t ? t[k] : any()) });
const ctx = { chrome, console, URL, fetch: async () => ({ json: async () => [] }), setTimeout: () => 0,
  setInterval: () => 0, importScripts: (f) => vm.runInContext(fs.readFileSync(path.join(ext, f), 'utf8'), ctx) };
ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(ext, 'background.js'), 'utf8') + ';globalThis.page = page;', ctx);
(async () => {
  const pg = ctx.page(1, 'tiktok', { host: 'www.tiktok.com', files: [] });
  const before = await pg.step('ready');
  live = new Set([2]);
  onReplaced?.(2, 1);  // Chrome activated a prerendered page: tab 1 is now tab 2
  await pg.go('https://www.tiktok.com/x');
  const after = await pg.step('findScheduled');
  console.log(JSON.stringify({ before, after, calls }));
})().catch((e) => { console.log(JSON.stringify({ error: e.message })); });
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_page_driver_follows_a_swapped_tab():
    out = subprocess.run(["node", "-e", HARNESS, str(EXT)], capture_output=True, text=True, check=True).stdout
    res = json.loads(out.strip().splitlines()[-1])
    assert "error" not in res, res["error"]
    assert res["before"] == 1
    assert res["after"] == 2
    assert ["update", 2] in res["calls"]
