const QUEUE = 'http://127.0.0.1:8766';
const CHUNK = 4 * 1024 * 1024; // bytes per executeScript call while moving a video into the tab
const UPLOAD_TIMEOUT_MS = 60 * 60 * 1000;
const log = (...args) => console.debug('[post-approve]', ...args);

// Background side of each platform: where the composer lives and which page scripts drive it.
const ADAPTERS = {
  youtube: { url: 'https://www.youtube.com/upload', host: 'studio.youtube.com', files: ['adapters/lib.js', 'adapters/youtube.js'], flow: youtubeFlow },
};

const api = (path, body) => fetch(`${QUEUE}/api/items${path}`, {
  method: 'POST', headers: { 'X-Postq': '1', 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}),
});

// Progress lines the popup shows while a post runs (the popup may be closed and reopened meanwhile).
async function progress(id, line) {
  log(id, line);
  const { progress: all = {} } = await chrome.storage.session.get('progress');
  await chrome.storage.session.set({ progress: { ...all, [id]: line } });
}

async function refreshBadge() {
  try {
    // The header tells the queue server the extension is alive (`postq approve` warns when it is not).
    const items = await (await fetch(`${QUEUE}/api/items`, { headers: { 'X-Postq-Poller': chrome.runtime.getManifest().version } })).json();
    chrome.action.setBadgeText({ text: items.length ? String(items.length) : '' });
    chrome.action.setBadgeBackgroundColor({ color: '#cc0000' });
    autoPost(items);
  } catch {
    chrome.action.setBadgeText({ text: '' });
  }
}

// `postq approve` sets item.auto. The claim stops a second start while one runs, and a failed post
// comes back from the server with auto cleared, so it is not retried until approved again.
// One at a time: Studio only renders in the visible tab, so two posts at once would starve each other.
let autoBusy = false;
async function autoPost(items) {
  if (autoBusy) return;
  autoBusy = true;
  try {
    for (const item of items.filter((i) => i.auto && ADAPTERS[i.platform] && !running.has(i.id))) {
      await approve(item, {}).catch((e) => log('auto failed', item.id, e.message));
    }
  } finally {
    autoBusy = false;
  }
}

const running = new Set();
async function approve(item, edits) {
  if (running.has(item.id)) throw new Error('Already posting.');
  const adapter = ADAPTERS[item.platform];
  if (!adapter) throw new Error(`No ${item.platform} adapter yet.`);
  const claim = await api(`/${item.id}/claim`);
  if (!claim.ok) throw new Error('Already being posted (or posted) elsewhere: skipped.');
  running.add(item.id);
  const post = { ...item, ...edits };
  let tabId;
  try {
    // Visible tab: Studio renders its upload form with requestAnimationFrame, which Chrome pauses
    // in background tabs, so a hidden tab never shows the details form (checked 2026-11).
    tabId = (await chrome.tabs.create({ url: adapter.url, active: true })).id;
    const result = await adapter.flow(post, page(tabId, item.platform, adapter));
    await api(`/${item.id}`, { ...edits, ...result });
    await progress(item.id, `${result.status}${result.url ? ` · ${result.url}` : ''}`);
    if (result.status !== 'dry-run') chrome.tabs.remove(tabId).catch(() => {});
    return result;
  } catch (e) {
    // An upload that got as far as a video id is kept, so the retry finishes that video, no second copy.
    await api(`/${item.id}/release`, { error: e.message, video_id: post.video_id });
    await progress(item.id, `failed: ${e.message}`);
    if (tabId) chrome.tabs.update(tabId, { active: true }).catch(() => {}); // leave it open to look at
    throw e;
  } finally {
    running.delete(item.id);
    refreshBadge();
  }
}

// Page driver for one tab: waits for the platform host, injects lib + adapter, runs steps.
function page(tabId, platform, adapter) {
  async function inject() {
    const end = Date.now() + 60000;
    for (;;) {
      const tab = await chrome.tabs.get(tabId);
      if (tab.status === 'complete' && new URL(tab.url || 'about:blank').host === adapter.host) break;
      if (Date.now() > end) throw new Error(`${adapter.host} did not load (logged in? tab url: ${tab.url})`);
      await new Promise((r) => setTimeout(r, 500));
    }
    await chrome.scripting.executeScript({ target: { tabId }, files: adapter.files });
  }
  async function step(name, ...args) {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId }, func: (p, s, a) => globalThis.postqRun(p, s, a), args: [platform, name, args],
    });
    if (!result) throw new Error(`step ${name}: no answer from the page (navigated away?)`);
    if (result.error) throw new Error(`step ${name}: ${result.error}`);
    return result.value;
  }
  // Pull the file from the queue server in ranges and hand it to the page chunk by chunk.
  async function send(slot, media, onPct) {
    for (let start = 0; start < media.size; start += CHUNK) {
      const end = Math.min(start + CHUNK, media.size) - 1;
      const res = await fetch(`${QUEUE}/media/${media.file}`, { headers: { Range: `bytes=${start}-${end}` } });
      if (res.status !== 206) throw new Error(`queue server answered ${res.status} for ${media.file}`);
      const bytes = new Uint8Array(await res.arrayBuffer());
      let bin = '';
      for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      const got = await chrome.scripting.executeScript({
        target: { tabId }, func: (s, b) => globalThis.postqLib.chunk(s, b), args: [slot, btoa(bin)],
      });
      if (got[0].result !== end + 1) throw new Error(`${slot} transfer broke at byte ${start}`);
      onPct?.(Math.round(((end + 1) / media.size) * 100));
    }
  }
  // Load another page in the same tab and re-inject (status reads 'complete' until the new load starts).
  async function go(url) {
    await chrome.tabs.update(tabId, { url, active: true });
    const end = Date.now() + 60000;
    while (!(await chrome.tabs.get(tabId)).url?.startsWith(url)) {
      if (Date.now() > end) throw new Error(`tab did not go to ${url} (a "leave page?" prompt?)`);
      await new Promise((r) => setTimeout(r, 500));
    }
    await inject();
  }
  // After a channel switch: let Studio's own reload settle, then load the upload page again.
  async function reopen() {
    const end = Date.now() + 30000;
    const before = (await chrome.tabs.get(tabId)).url;
    while ((await chrome.tabs.get(tabId)).url === before && Date.now() < end) await new Promise((r) => setTimeout(r, 500));
    while ((await chrome.tabs.get(tabId)).status !== 'complete' && Date.now() < end) await new Promise((r) => setTimeout(r, 500));
    await chrome.tabs.update(tabId, { url: adapter.url, active: true });
    while ((await chrome.tabs.get(tabId)).status === 'complete' && Date.now() < end) await new Promise((r) => setTimeout(r, 200));
    await inject();
  }
  return { inject, step, send, go, reopen };
}

const mimeOf = (file) => ({ mp4: 'video/mp4', mov: 'video/quicktime', webm: 'video/webm', jpg: 'image/jpeg',
  jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp' })[file.split('.').pop()];

const accountMatches = (want, who) => {
  const norm = (s) => (s || '').trim().replace(/^@/, '').toLowerCase();
  return [who.name, who.id].some((v) => v && norm(v) === norm(want));
};

async function youtubeFlow(item, pg) {
  const say = (line) => progress(item.id, line);
  await say('Opening YouTube Studio…');
  await pg.inject();
  await pg.step('ready');
  let who = await pg.step('whoami');
  if (!accountMatches(item.account, who)) {
    await say(`Studio is on "${who.name}", switching to "${item.account}"…`);
    await pg.step('switchChannel', item.account);
    await pg.reopen(); // the switch reloads Studio on the channel's dashboard
    await pg.step('ready');
    who = await pg.step('whoami');
    if (!accountMatches(item.account, who)) {
      throw new Error(`switched channel, but Studio is on "${who.name}" (${who.id}), item wants "${item.account}"`);
    }
  }
  const when = item.schedule_at ? Date.parse(item.schedule_at) : null;
  // Already uploaded (`postq approve --video <id>`): no second copy, only finish and check that video.
  if (item.video_id) {
    await say(`Channel ${who.name} ✓ · resuming video ${item.video_id}`);
    return checkOnEditPage(item, pg, item.video_id, `https://youtube.com/shorts/${item.video_id}`, when, 'resumed');
  }
  await say(`Channel ${who.name} ✓ · moving video into the tab…`);
  await pg.send('video', item.video, (p) => say(`Moving video into the tab ${p}%`));
  await pg.step('setVideo', item.video.name, mimeOf(item.video.file));
  item.video_id = (await pg.step('progress')).url?.match(/(?:shorts\/|youtu\.be\/|[?&]v=)([\w-]{11})/)?.[1];
  await say('Filling details…');
  const warnings = await pg.step('fill', item);
  await pg.step('toVisibility');
  const vis = await pg.step('visibility', item, when);
  const note = [vis.mode === 'scheduled' ? `scheduled ${vis.date} ${vis.time} (${vis.zone})` : vis.mode, ...warnings].join(' · ');
  await say(note);

  const end = Date.now() + UPLOAD_TIMEOUT_MS;
  for (let p = await pg.step('progress'); p.uploading; p = await pg.step('progress')) {
    if (Date.now() > end) throw new Error(`upload did not finish within 60 min (${p.label})`);
    await say(`${p.label}`);
    await new Promise((r) => setTimeout(r, 3000));
  }
  const { url } = await pg.step('progress');
  if (item.dry_run) return { status: 'dry-run', url, log: `${note} · form filled, not submitted (tab left open)` };
  const sent = await pg.step('submit');
  const link = sent.url || url;
  await say(`${sent.confirm} · checking the edit page`);
  const id = link?.match(/(?:shorts\/|youtu\.be\/|[?&]v=)([\w-]{11})/)?.[1];
  if (!id) throw new Error(`pressed "${sent.button}" but got no video id to check (link: ${link})`);
  return checkOnEditPage(item, pg, id, link, when, note);
}

// Only the saved video counts: reopen it in Studio, schedule it if it is still a draft, fix what
// drifted, read the schedule back.
async function checkOnEditPage(item, pg, id, link, when, note) {
  const say = (line) => progress(item.id, line);
  const edit = `https://studio.youtube.com/video/${id}/edit`;
  await pg.go(edit);
  if (await pg.step('openDraft')) {
    await say('Still a draft: setting its schedule…');
    await pg.step('toVisibility');
    await pg.step('visibility', item, when);
    const sent = await pg.step('submit');
    await say(`${sent.confirm} · checking the edit page`);
    await pg.go(edit);
    if (await pg.step('openDraft')) throw new Error(`video ${id} is still a draft after "${sent.button}"`);
  }
  // Cover goes up on the edit page: the upload dialog has no thumbnail picker for Shorts.
  if (item.cover) await pg.send('cover', item.cover, (p) => say(`Moving thumbnail into the tab ${p}%`));
  const checks = await pg.step('verify', { ...item, cover: item.cover && { name: item.cover.name, type: mimeOf(item.cover.file) } }, when);
  return { status: when ? 'scheduled' : 'posted', url: link, log: [note, ...checks].join(' · ') };
}

// Posting runs here, not in the popup: the popup closes on blur, an upload must not.
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  const run = {
    approve: () => approve(msg.item, msg.edits || {}),
    discard: () => api(`/${msg.item.id}`, { status: 'discarded' }).then(refreshBadge),
  }[msg.type];
  if (!run || sender.tab) return false;
  run().then((data) => reply({ data }), (e) => reply({ error: e.message }));
  return true;
});

chrome.alarms.create('badge', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(refreshBadge);
chrome.runtime.onStartup.addListener(refreshBadge);
chrome.runtime.onInstalled.addListener(refreshBadge);
