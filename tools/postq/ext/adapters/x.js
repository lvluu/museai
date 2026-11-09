// X composer (x.com/compose/post) and its scheduled-posts list (x.com/compose/post/unsent/scheduled).
// Every selector lives in SEL: when X changes, fix it here. Run a --dry-run item after a fix.
// X has no custom thumbnail for a video uploaded on the web (checked 2026-11): the post shows the
// video's own first frame, so item.cover is not used here.
globalThis.postqAdapters.x ??= (() => {
  const { sleep, $, waitFor, takeFile, attach } = globalThis.postqLib;

  const SEL = {
    composer: ['[role=dialog] [data-testid=tweetTextarea_0]', '[data-testid=tweetTextarea_0]'],
    blocks: '[data-block=true]', // one per line of the Draft.js editor
    fileInput: ['[role=dialog] input[data-testid=fileInput]', 'input[data-testid=fileInput]'],
    attachments: ['[role=dialog] [data-testid=attachments]', '[data-testid=attachments]'],
    uploadStatus: '[role=status]', // inside attachments: "t.mp4: Uploading (0%)"
    scheduleIcon: ['[role=dialog] [data-testid=scheduleOption]', '[data-testid=scheduleOption]'],
    scheduleConfirm: ['[data-testid=scheduledConfirmationPrimaryAction]'],
    postButton: ['[role=dialog] [data-testid=tweetButton]', '[data-testid=tweetButton]'],
    profileLink: ['[data-testid=AppTabBar_Profile_Link]'],
    switcher: ['[data-testid=SideNav_AccountSwitcher_Button]'],
    toast: ['[data-testid=toast]', '[role=alert]'],
    scheduledTab: '[role=tab]', // the one reading "Scheduled"
    unsent: '[data-testid=unsentTweet]', // one scheduled post: "Will send on …" + tweetText
    unsentText: '[data-testid=tweetText]',
  };

  const text = (el) => (el?.innerText || el?.textContent || '').trim();
  // Text compares without case, accents, emoji, punctuation or line breaks (X collapses blank lines).
  const fold = (s) => (s || '').replace(/đ/g, 'd').replace(/Đ/g, 'D').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^\p{L}\p{N}#@]+/gu, ' ').trim();
  const editorText = (box) => [...box.querySelectorAll(SEL.blocks)].map((b) => text(b)).join('\n');

  // "Will send on Wed, Nov 25, 2026 at 7:00 AM" (browser's own zone) -> epoch ms, NaN when unreadable.
  const sendTime = (s) => Date.parse((s.match(/send on \w+, (.+? \d{4}) at (\d{1,2}:\d{2}\s*[AP]M)/i) || []).slice(1).join(' '));
  const shown = (ms) => new Date(ms).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });

  // The schedule dialog: native <select>s labelled Month, Day, Year, Hour, Minute, AM/PM.
  function selects() {
    const dlg = $(SEL.scheduleConfirm)?.closest('[role=dialog]');
    if (!dlg) return null;
    const label = (s) => text(document.getElementById(s.getAttribute('aria-labelledby')));
    return { dlg, ...Object.fromEntries([...dlg.querySelectorAll('select')].map((s) => [label(s), s])) };
  }
  function pick(sel, value) {
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(sel, String(value));
    sel.dispatchEvent(new Event('change', { bubbles: true }));
    if (sel.value !== String(value)) throw new Error(`schedule ${sel.id}: no option ${value}`);
  }

  // Rows of the Scheduled tab, scrolled to the end (the list renders lazily).
  async function scheduledRows() {
    const tab = await (async () => {
      for (const end = Date.now() + 30000; Date.now() < end; await sleep(300)) {
        const t = [...document.querySelectorAll(SEL.scheduledTab)].find((e) => /^scheduled$/i.test(text(e)));
        if (t) return t;
      }
      throw new Error('no Scheduled tab in Unsent posts (logged out?)');
    })();
    if (tab.getAttribute('aria-selected') !== 'true') tab.click();
    // An empty list has no rows at all: give it a moment, then take what is there.
    for (const end = Date.now() + 8000; !document.querySelector(SEL.unsent) && Date.now() < end;) await sleep(300);
    const rows = new Map();
    const scroller = tab.closest('[role=dialog]')?.querySelector('[data-viewportview=true]') || document.scrollingElement;
    for (let i = 0, last = -1; i < 40 && rows.size !== last; i++) {
      last = rows.size;
      for (const r of document.querySelectorAll(SEL.unsent)) {
        const body = text(r.querySelector(SEL.unsentText));
        rows.set(`${text(r).split('\n')[0]}|${body}`, { at: sendTime(text(r)), line: text(r).split('\n')[0], body });
      }
      scroller.scrollTop += 2000;
      await sleep(600);
    }
    return [...rows.values()];
  }

  return {
    async ready() {
      await waitFor(SEL.composer, { timeout: 45000, what: 'X composer (are you logged in to x.com?)' });
      await waitFor(SEL.fileInput, { hidden: true, what: 'composer media input' });
      return location.href;
    },

    // The account the composer posts as: the side nav's @handle.
    async whoami() {
      const link = await waitFor(SEL.profileLink, { hidden: true, what: 'profile link (logged in?)' });
      const handle = link.getAttribute('href').replace(/^\//, '');
      const name = text($(SEL.switcher, { hidden: true })).split('\n')[0];
      return { name: name || handle, id: handle };
    },

    async setVideo(name, type) {
      attach($(SEL.fileInput, { hidden: true }), takeFile('video', name, type));
      await waitFor(SEL.attachments, { timeout: 60000, what: 'video attachment in the composer' });
      return true;
    },

    // Draft.js takes a paste as one edit (insertText with line breaks scrambles its blocks).
    async fill(item) {
      const box = await waitFor(SEL.composer);
      box.focus();
      box.click();
      await sleep(200);
      if (editorText(box).trim()) document.execCommand('selectAll', false); // a restored draft: paste over it
      const dt = new DataTransfer();
      dt.setData('text/plain', item.caption);
      box.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
      await sleep(800);
      const got = editorText(box);
      if (fold(got) !== fold(item.caption)) throw new Error(`text reads back as ${JSON.stringify(got.slice(0, 120))}`);
      return [];
    },

    // whenMs in the browser's zone (X's dialog names it): set every select, check the dialog's own
    // "Will send on …" line, Confirm, then check the composer's banner.
    async schedule(whenMs) {
      (await waitFor(SEL.scheduleIcon, { what: 'schedule icon' })).click();
      for (const end = Date.now() + 15000; !selects() && Date.now() < end;) await sleep(250);
      const s = selects();
      if (!s) throw new Error('schedule dialog did not open');
      const when = new Date(whenMs);
      const h = when.getHours();
      pick(s.Year, when.getFullYear());
      pick(s.Month, when.getMonth() + 1);
      pick(s.Day, when.getDate());
      pick(s.Hour, h % 12 || 12);
      pick(s.Minute, when.getMinutes());
      pick(s['AM/PM'], h < 12 ? 'am' : 'pm');
      await sleep(400);
      const zone = text([...s.dlg.querySelectorAll('*')].find((e) => /^time zone$/i.test(text(e)))?.nextElementSibling);
      const line = text(s.dlg).split('\n').find((l) => /will send on/i.test(l)) || '';
      if (sendTime(line) !== whenMs) throw new Error(`schedule dialog reads "${line}", wanted ${shown(whenMs)}`);
      $(SEL.scheduleConfirm).click();
      await sleep(1000);
      const box = await waitFor(SEL.composer);
      const banner = text(box.closest('[role=dialog]')).split('\n').find((l) => /will send on/i.test(l)) || '';
      if (sendTime(banner) !== whenMs) throw new Error(`composer banner reads "${banner}", wanted ${shown(whenMs)}`);
      return { line: banner, zone: zone || Intl.DateTimeFormat().resolvedOptions().timeZone };
    },

    // The video uploads while the composer is open. The attachment's [role=status] reads
    // "<name>: Uploading (N%)", then empties; a bad file reads "Something went wrong | Not a valid …".
    progress() {
      const btn = $(SEL.postButton);
      const att = $(SEL.attachments, { hidden: true });
      const status = text(att?.querySelector(SEL.uploadStatus)).replace(/\s*\n\s*/g, ' ');
      const all = text(att);
      const error = /something went wrong|not a valid|failed/i.test(all)
        ? all.split('\n').filter((l) => /wrong|valid|failed/i.test(l)).join(' · ') : '';
      const off = !btn || btn.disabled || btn.getAttribute('aria-disabled') === 'true';
      return { uploading: !error && /upload|process/i.test(status), error, off, button: text(btn), label: status };
    },

    // Press "Schedule" (or "Post") and wait for the composer to close.
    async submit() {
      const btn = await waitFor(SEL.postButton);
      const off = () => btn.disabled || btn.getAttribute('aria-disabled') === 'true';
      for (const end = Date.now() + 10 * 60000; off() && Date.now() < end;) await sleep(1000);
      if (off()) throw new Error(`"${text(btn)}" stayed disabled for 10 min (caption over 280, or upload failed?)`);
      const label = text(btn);
      btn.click();
      for (const end = Date.now() + 120000; Date.now() < end; await sleep(1000)) {
        if (!btn.isConnected || !$(SEL.composer)) return { button: label, confirm: text($(SEL.toast)) || 'composer closed' };
        const err = text($(SEL.toast));
        if (/wrong|error|failed|try again|limit/i.test(err)) throw new Error(`X said "${err}" after "${label}"`);
      }
      throw new Error(`composer still open 120 s after "${label}"`);
    },

    // On the Scheduled list: the post whose text matches, at whenMs. Null when not there.
    async findScheduled(caption, whenMs) {
      const rows = await scheduledRows();
      const mine = rows.filter((r) => fold(r.body) === fold(caption));
      const hit = mine.find((r) => r.at === whenMs);
      if (hit) return { line: hit.line, count: rows.length };
      if (mine.length) return { wrong: mine.map((r) => r.line).join(' / '), count: rows.length };
      return null;
    },
  };
})();
