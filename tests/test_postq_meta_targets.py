"""A Facebook-only Meta item is not stopped by the Instagram reel of the same video (same title, same slot)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

EXT = Path(__file__).parent.parent / "tools" / "postq" / "ext"

# background.js in a vm; the page stub lists one scheduled Instagram row whose caption starts with the
# shared title, and stops at the composer's 'ready' step (reaching it = the item goes on to post).
HARNESS = r"""
const fs = require('fs'), vm = require('vm'), path = require('path');
const [ext, targets, platform] = [process.argv[1], process.argv[2].split(','), process.argv[3]];
const any = () => new Proxy(function () {}, { get: (t, k) => (k === 'then' ? undefined : any()), apply: () => any() });
const store = () => ({ get: async () => ({}), set: async () => {} });
const chrome = new Proxy({ storage: { session: store(), local: store() } },
  { get: (t, k) => (k in t ? t[k] : any()) });
const ctx = { chrome, console, URL, Intl, Date, fetch: async () => ({ ok: true, json: async () => ({}) }),
  setTimeout: (f) => { f(); return 0; }, setInterval: () => 0, importScripts: () => {} };
ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(ext, 'background.js'), 'utf8') + ';globalThis.metaFlow = metaFlow;', ctx);
const when = Date.now() + 5 * 86400000;
const row = { title: 'Harvest with me: a Korean backyard garden Harvest day', date: 'x', platform,
  thumb: 'https://scontent.fbcdn.net/t.jpg', match: true, blank: false };
const pg = {
  go: async () => {}, main: async () => {},
  step: async (name) => {
    if (name === 'findScheduled') return [row];
    if (name === 'ready') throw new Error('COMPOSER');
    return {};
  },
};
const item = { id: 'i', platform: 'meta', targets, account: 'A', title: 'Harvest with me: a Korean backyard garden',
  caption: 'Harvest with me, sound on.', caption_ig: null, asset: { business_id: 'b', asset_id: 'a' },
  schedule_at: new Date(when).toISOString(), tz: 'UTC' };
ctx.metaFlow(item, pg).then((r) => console.log(JSON.stringify({ result: r })),
  (e) => console.log(JSON.stringify({ error: e.message })));
"""


def run(targets, platform):
    out = subprocess.run(["node", "-e", HARNESS, str(EXT), targets, platform],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_facebook_item_goes_on_past_the_instagram_row():
    assert run("facebook", "instagram") == {"error": "COMPOSER"}


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_own_row_still_counts_as_already_scheduled():
    res = run("facebook", "facebook")
    assert "facebook x ✓ thumbnail ✓" in res.get("result", {}).get("log", ""), res
