const QUEUE = 'http://127.0.0.1:8766';
const READY = new Set(['youtube']); // platforms with an adapter (mirror of ADAPTERS in background.js)
const LIMITS = { youtube: { title: 100, caption: 5000 }, meta: { caption: 2200 }, tiktok: { caption: 2200 }, x: { caption: 280 } };
const list = document.getElementById('list');
const cards = new Map();

// <input type=datetime-local> works in this browser's zone: so does YouTube Studio's scheduler.
const toLocalInput = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;

function counter(input, max) {
  const el = document.createElement('span');
  el.className = 'count';
  const update = () => {
    el.textContent = `${input.value.length}/${max}`;
    el.classList.toggle('over', input.value.length > max);
  };
  input.addEventListener('input', update);
  update();
  return el;
}

function render(item) {
  const lim = LIMITS[item.platform] || {};
  const el = document.createElement('section');
  el.className = 'card';
  el.innerHTML = `
    <div class="meta"><span class="pill"></span><span class="who"></span><span class="pill dry" hidden>dry run</span><span class="when"></span></div>
    <div class="top">
      <video muted controls preload="metadata"></video>
      <div class="fields">
        ${lim.title ? '<label>Title <input name="title"></label>' : ''}
        <label>${item.platform === 'youtube' ? 'Description' : 'Caption'} <textarea name="caption"></textarea></label>
        <div class="row">
          <label>Publish at (${zone}, empty = now) <input type="datetime-local" name="at"></label>
          ${item.platform === 'youtube' ? `<label>Related video <input name="related" placeholder="Tập 36 / latest:Tập"></label>` : ''}
          ${item.platform === 'youtube' ? `<label>Visibility <select name="visibility">
            <option>public</option><option>unlisted</option><option>private</option></select></label>` : ''}
        </div>
      </div>
    </div>
    <div class="row">
      <button class="primary" data-act="approve">Approve</button>
      <button data-act="discard">Discard</button>
      <label class="check"><input type="checkbox" name="dry"> dry run</label>
      <span class="status"></span>
    </div>`;
  const q = (s) => el.querySelector(s);
  const [platformPill, who, dryPill, whenEl] = el.querySelectorAll('.meta > *');
  platformPill.textContent = item.platform + (item.targets?.length ? ` → ${item.targets.join(' + ')}` : '');
  who.textContent = item.account + (item.playlist ? ` · playlist: ${item.playlist}` : '');
  dryPill.hidden = !item.dry_run;
  whenEl.textContent = item.created;
  q('video').src = `${QUEUE}/media/${item.video.file}`;
  const title = q('[name=title]');
  if (title) {
    title.value = item.title;
    title.parentElement.prepend(counter(title, lim.title));
  }
  const caption = q('[name=caption]');
  caption.value = item.caption;
  caption.parentElement.prepend(counter(caption, lim.caption));
  q('[name=at]').value = toLocalInput(item.schedule_at);
  if (q('[name=visibility]')) q('[name=visibility]').value = item.visibility;
  if (q('[name=related]')) q('[name=related]').value = item.related || '';
  q('[name=dry]').checked = item.dry_run;
  const c = { item, el, status: q('.status'), buttons: [...el.querySelectorAll('button')] };
  c.edits = () => {
    const at = q('[name=at]').value;
    return {
      ...(title && { title: title.value }),
      caption: caption.value,
      schedule_at: at ? new Date(at).toISOString() : null,
      ...(q('[name=visibility]') && { visibility: q('[name=visibility]').value }),
      ...(q('[name=related]') && { related: q('[name=related]').value.trim() || null }),
      dry_run: q('[name=dry]').checked,
    };
  };
  q('[data-act=approve]').onclick = () => approve(c);
  q('[data-act=discard]').onclick = () => discard(c);
  if (!READY.has(item.platform)) {
    c.buttons[0].disabled = true;
    setStatus(c, '', `no ${item.platform} adapter yet`);
  }
  cards.set(item.id, c);
  list.append(el);
}

function setStatus(c, cls, line) {
  c.status.className = `status ${cls}`;
  const url = line.match(/https?:\/\/\S+/)?.[0];
  c.status.textContent = url ? line.replace(url, '') : line;
  if (url) c.status.append(Object.assign(document.createElement('a'), { href: url, target: '_blank', textContent: url }));
}

async function approve(c) {
  if (c.busy || c.done || !READY.has(c.item.platform)) return;
  c.busy = true;
  c.buttons.forEach((b) => (b.disabled = true));
  setStatus(c, '', 'Starting…');
  const res = await chrome.runtime.sendMessage({ type: 'approve', item: c.item, edits: c.edits() });
  c.busy = false;
  if (res?.error) {
    setStatus(c, 'bad', res.error);
    c.buttons.forEach((b) => (b.disabled = false));
  } else {
    c.done = true;
    setStatus(c, 'ok', `${res.data.status}${res.data.url ? ` · ${res.data.url}` : ''}`);
  }
}

async function discard(c) {
  await chrome.runtime.sendMessage({ type: 'discard', item: c.item });
  c.el.remove();
  cards.delete(c.item.id);
  renderEmpty();
}

function renderEmpty(msg = 'Nothing pending. Queue with: postq add --platform youtube --account … --file v.mp4 --title …') {
  const empty = list.querySelector('.empty');
  if (cards.size) return empty?.remove();
  if (!empty) list.insertAdjacentHTML('beforeend', '<div class="empty"></div>');
  list.querySelector('.empty').textContent = msg;
}

// Live progress written by the background worker (also for posts started before this popup opened).
async function showProgress() {
  const { progress = {} } = await chrome.storage.session.get('progress');
  for (const [id, line] of Object.entries(progress)) {
    const c = cards.get(id);
    if (c && !c.done) setStatus(c, line.startsWith('failed') ? 'bad' : '', line);
  }
}
chrome.storage.onChanged.addListener((ch, area) => area === 'session' && ch.progress && showProgress());

async function poll() {
  try {
    const items = await (await fetch(`${QUEUE}/api/items`)).json();
    for (const item of items) if (!cards.has(item.id)) render(item);
    renderEmpty();
    showProgress();
  } catch {
    if (!cards.size) renderEmpty('Queue server not reachable. Run: postq serve');
  }
}

async function approveAll() {
  for (const c of cards.values()) await approve(c);
}
document.getElementById('all').onclick = approveAll;
document.addEventListener('keydown', (e) => {
  const inField = ['TEXTAREA', 'INPUT', 'SELECT', 'BUTTON', 'A'].includes(document.activeElement?.tagName);
  if (e.key === 'Enter' && !inField) { e.preventDefault(); approveAll(); }
});

poll();
setInterval(poll, 5000);
