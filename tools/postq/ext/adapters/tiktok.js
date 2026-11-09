// TikTok Studio web upload (www.tiktok.com/tiktokstudio/upload) and its post list (/tiktokstudio/content).
// Every selector lives in SEL: when TikTok changes, fix it here. Run a --dry-run item after a fix.
// Checked on @blue_eyes_wander 2026-11: Draft.js description (4000 chars), Now/Schedule radios, a date
// picker open 30 days ahead, a time picker in 5-minute steps, zone = the browser's ("(GMT+7) Local Time"),
// cover through "Edit cover" -> "Upload cover" -> Save. Scheduled rows read "Nov 12, 7:00 AM (GMT+7) Saigon".
globalThis.postqAdapters.tiktok ??= (() => {
  const { sleep, $, waitFor, takeFile, attach } = globalThis.postqLib;

  const SEL = {
    videoInput: ['input[type=file][accept*=video]'],
    editor: ['.public-DraftEditor-content'],
    blocks: '[data-block=true]',
    avatar: ['[data-tt="Header_NewHeader_Clickable"][aria-haspopup]'],
    profileItem: ['a.TUXMenuItem[href*="/@"]'],
    coverEdit: ['.cover-container .edit-container', '.cover-container'],
    coverImg: '.cover-container img',
    coverInput: ['input[type=file][accept*=image]'],
    coverHeaderBtn: 'button.header-button', // "Cancel" / "Save" of the cover editor
    radioSchedule: 'input[type=radio][value=schedule]',
    pickers: '.scheduled-picker .Picker__trigger', // [0] date, [1] time
    pickerValue: '.Picker__value',
    dayButton: '.DatePicker__day',
    calTitle: '.DatePicker__title', // "November\n2026"
    calNav: '.DatePicker__nav', // [0] previous month, [1] next month
    timeColumn: '.TimePicker__column', // [0] hours 00-23, [1] minutes 00-55
    timeItem: '.TimePicker__item',
    zone: '.timezone-select input',
    postButton: ['button[data-e2e=post_video_button]'],
    dialog: '[role=dialog], .TUXModal, [class*=Modal__]',
    toast: ['.TUXTopToast', '[class*=Toast]', '[role=alert]'],
    timeCell: /\(GMT[+-]\d{1,2}(?::\d{2})?\)/, // a scheduled row's time text
  };

  const text = (el) => (el?.innerText || el?.textContent || '').trim();
  // Compare without case, accents, emoji, punctuation or line breaks (the list joins lines with spaces).
  const fold = (s) => (s || '').replace(/đ/g, 'd').replace(/Đ/g, 'D').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^\p{L}\p{N}#@]+/gu, ' ').trim();
  // Same caption: equal, or the list cut one short (prefix of 60+ characters).
  const same = (a, b) => {
    const [x, y] = [fold(a), fold(b)];
    return x === y || (Math.min(x.length, y.length) >= 60 && (x.startsWith(y) || y.startsWith(x)));
  };
  const editorText = (box) => [...box.querySelectorAll(SEL.blocks)].map((b) => text(b)).join('\n');
  const pad = (n) => String(n).padStart(2, '0');
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const shown = (ms) => new Date(ms).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
  const gmt = (ms) => { // browser zone as TikTok writes it: "GMT+7", "GMT+5:30"
    const off = -new Date(ms).getTimezoneOffset();
    const h = Math.trunc(Math.abs(off) / 60), m = Math.abs(off) % 60;
    return `GMT${off < 0 ? '-' : '+'}${h}${m ? `:${pad(m)}` : ''}`;
  };

  // "Nov 12, 7:00 AM (GMT+7) Saigon" -> epoch ms (year: the one that puts it nearest to now).
  function rowTime(s) {
    const m = s.replace(/\s+/g, ' ').match(/(\w{3}) (\d{1,2}), (\d{1,2}):(\d{2}) ?([AP]M) \(GMT([+-])(\d{1,2})(?::(\d{2}))?\)/i);
    if (!m) return NaN;
    const [, mon, d, h, mi, ap, sign, oh, om] = m;
    const off = (sign === '-' ? -1 : 1) * (Number(oh) * 60 + Number(om || 0));
    const hour = (Number(h) % 12) + (/pm/i.test(ap) ? 12 : 0);
    const y = new Date().getFullYear();
    const at = [y - 1, y, y + 1].map((yy) => Date.UTC(yy, MONTHS.indexOf(mon), Number(d), hour, Number(mi)) - off * 60000);
    return at.sort((a, b) => Math.abs(a - Date.now()) - Math.abs(b - Date.now()))[0];
  }

  // A cover editor / dialog button by its label.
  const button = (root, re) => [...root.querySelectorAll('button')].find((b) => b.getClientRects().length && re.test(text(b)));

  async function openPicker(i) {
    const trig = document.querySelectorAll(SEL.pickers)[i];
    if (!trig) throw new Error('schedule pickers not shown (Schedule radio not on?)');
    trig.click();
    await sleep(500);
  }
  const pickerValues = () => [...document.querySelectorAll(SEL.pickers)].map((t) => text(t.querySelector(SEL.pickerValue)));
  async function closePickers() {
    for (let i = 0; i < 3 && (document.querySelector('.DatePicker__panel') || document.querySelector('.TimePicker__panel')); i++) {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
      await sleep(300);
      if (document.querySelector('.TimePicker__panel') || document.querySelector('.DatePicker__panel')) {
        document.querySelector('.scheduled-container .title-v2, .scheduled-container')?.click();
        await sleep(300);
      }
    }
  }

  // Rows of the post list (scheduled ones first; the list renders lazily, so scroll it).
  async function listRows() {
    for (const end = Date.now() + 45000; Date.now() < end && !document.querySelector('a[href*="/video/"]'); ) await sleep(500);
    const rows = new Map();
    const ids = (el) => new Set([...el.querySelectorAll('a[href*="/video/"]')].map((x) => x.getAttribute('href').match(/\/video\/(\d+)/)?.[1])).size;
    const scroller = [...document.querySelectorAll('*')].filter((e) => e.scrollHeight > e.clientHeight + 50
      && /auto|scroll/.test(getComputedStyle(e).overflowY)).sort((a, b) => b.scrollHeight - a.scrollHeight)[0]
      || document.scrollingElement;
    scroller.scrollTop = 0; // virtualized: rows scrolled past are gone from the DOM
    await sleep(1200);
    for (let i = 0, last = -1; i < 15 && rows.size !== last; i++) {
      last = rows.size;
      for (const a of document.querySelectorAll('a[href*="/video/"]')) {
        const id = a.getAttribute('href').match(/\/video\/(\d+)/)?.[1];
        // The row: the largest ancestor whose links all go to this one video.
        let row = a;
        while (row.parentElement && ids(row.parentElement) === 1) row = row.parentElement;
        const lines = text(row).split('\n').map((l) => l.trim()).filter(Boolean);
        const timeLine = lines.find((l) => SEL.timeCell.test(l)) || '';
        const caption = lines.filter((l) => !/^\d{1,2}:\d{2}$/.test(l) && l !== timeLine).sort((x, y) => y.length - x.length)[0] || '';
        const thumb = [...row.querySelectorAll('img')].some((img) => img.naturalWidth > 0 || img.src)
          || [...row.querySelectorAll('*')].some((e) => getComputedStyle(e).backgroundImage !== 'none');
        if (id) rows.set(id, { id, caption, line: timeLine, at: timeLine ? rowTime(timeLine) : null, thumb });
      }
      scroller.scrollTop += 3000;
      await sleep(700);
    }
    return [...rows.values()];
  }

  return {
    async ready() {
      await waitFor(SEL.videoInput, { timeout: 60000, hidden: true, what: 'TikTok Studio upload input (logged in to tiktok.com?)' });
      return location.href;
    },

    // The logged-in account: the avatar menu's Profile link (@handle). The menu closes again.
    async whoami() {
      const av = await waitFor(SEL.avatar, { what: 'TikTok Studio avatar (logged in?)' });
      av.click();
      const link = await waitFor(SEL.profileItem, { hidden: true, timeout: 8000, what: 'Profile item in the avatar menu' });
      const handle = link.getAttribute('href').match(/\/@([^/?#]+)/)?.[1] || '';
      av.click();
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
      await sleep(300);
      return { name: handle, id: handle };
    },

    async setVideo(name, type) {
      attach($(SEL.videoInput, { hidden: true }), takeFile('video', name, type));
      await waitFor(SEL.editor, { timeout: 120000, what: 'details form after picking the video' });
      return true;
    },

    // "Uploading 42%" -> "Uploaded（432.45KB）" in the file row above the form.
    progress() {
      const all = text(document.body);
      const failed = all.split('\n').find((l) => /upload failed|couldn.t upload|unsupported|try again/i.test(l));
      const line = all.split('\n').find((l) => /^upload(ing|ed)/i.test(l.trim())) || '';
      const pct = line.match(/(\d+)\s*%/)?.[1];
      return { uploading: !failed && !/^uploaded/i.test(line), failed: failed || '', label: line || 'waiting for TikTok…', pct };
    },

    // Draft.js takes one paste over a real selection (its own selection must be updated first: keyup +
    // selectionchange). The blur afterwards makes the form store it, as on Business Suite.
    async fill(item) {
      const box = await waitFor(SEL.editor);
      box.focus();
      box.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
      await sleep(200);
      const range = document.createRange();
      range.selectNodeContents(box);
      getSelection().removeAllRanges();
      getSelection().addRange(range);
      box.dispatchEvent(new KeyboardEvent('keyup', { key: 'Shift', bubbles: true }));
      document.dispatchEvent(new Event('selectionchange'));
      await sleep(300);
      const dt = new DataTransfer();
      dt.setData('text/plain', item.caption);
      box.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
      await sleep(1000);
      box.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
      box.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
      box.dispatchEvent(new FocusEvent('blur'));
      await sleep(500);
      const got = editorText(box);
      if (fold(got) !== fold(item.caption)) throw new Error(`description reads back as ${JSON.stringify(got.slice(0, 160))}`);
      const counter = [...document.querySelectorAll('*')].find((e) => !e.children.length && /^\d+\/4000$/.test(text(e)));
      return text(counter) || `${got.length} chars`;
    },

    // Edit cover -> Upload cover (the image arrives through pg.send('cover')) -> Save; the form's cover
    // image must change.
    async setCover(name, type) {
      const before = document.querySelector(SEL.coverImg)?.src;
      if (!$(SEL.coverInput, { hidden: true })) {
        (await waitFor(SEL.coverEdit, { what: 'Edit cover' })).click();
      }
      const input = await waitFor(SEL.coverInput, { hidden: true, timeout: 20000, what: 'Upload cover input' });
      attach(input, takeFile('cover', name, type));
      await sleep(2500);
      let save;
      for (const end = Date.now() + 30000; Date.now() < end; await sleep(500)) {
        save = [...document.querySelectorAll(SEL.coverHeaderBtn)].find((b) => /^save$/i.test(text(b)));
        if (save && !save.disabled && save.getAttribute('aria-disabled') !== 'true') break;
      }
      if (!save) throw new Error('cover editor has no Save button');
      save.click();
      for (const end = Date.now() + 30000; document.querySelector(SEL.coverHeaderBtn) && Date.now() < end;) await sleep(300);
      if (document.querySelector(SEL.coverHeaderBtn)) throw new Error('cover editor still open after Save');
      await sleep(1000);
      const after = document.querySelector(SEL.coverImg)?.src;
      if (!after || after === before) throw new Error('cover did not change after Save');
      return 'cover uploaded';
    },

    // whenMs in the browser's zone (TikTok's zone select says "(GMT+7) Local Time"): Schedule radio,
    // date from the calendar, hour + minute from the wheels, then read all three back.
    async schedule(whenMs) {
      const radio = document.querySelector(SEL.radioSchedule);
      if (!radio) throw new Error('no Schedule option (account not allowed to schedule?)');
      if (!radio.checked) radio.click();
      await sleep(800);
      const when = new Date(whenMs);
      if (when.getMinutes() % 5) throw new Error(`TikTok schedules in 5-minute steps, ${shown(whenMs)} is not one`);
      await openPicker(0);
      for (let i = 0; i < 14; i++) {
        const [mon, yr] = text(document.querySelector(SEL.calTitle)).split(/\s+/);
        const diff = (when.getFullYear() - Number(yr)) * 12 + when.getMonth() - new Date(`${mon} 1, 2000`).getMonth();
        if (!diff) break;
        document.querySelectorAll(SEL.calNav)[diff > 0 ? 1 : 0].click();
        await sleep(400);
      }
      // Leading/trailing days of other months repeat numbers: take the one inside the month's run 1..N.
      const days = [...document.querySelectorAll(SEL.dayButton)];
      const first = days.findIndex((d) => text(d) === '1');
      const day = days.slice(first).find((d) => text(d) === String(when.getDate()));
      if (!day || day.disabled) throw new Error(`${shown(whenMs)} is not open in TikTok's calendar (max 30 days ahead)`);
      day.click();
      await sleep(600);
      await openPicker(1);
      for (const [col, v] of [[0, pad(when.getHours())], [1, pad(when.getMinutes())]]) {
        const item = [...(document.querySelectorAll(SEL.timeColumn)[col]?.querySelectorAll(SEL.timeItem) || [])]
          .find((b) => text(b) === v);
        if (!item) throw new Error(`time picker has no ${col ? 'minute' : 'hour'} ${v}`);
        item.click();
        await sleep(400);
      }
      await closePickers();
      const [date, time] = pickerValues();
      const wantDate = `${MONTHS[when.getMonth()]} ${when.getDate()}, ${when.getFullYear()}`;
      const wantTime = `${pad(when.getHours())}:${pad(when.getMinutes())}`;
      if (date !== wantDate || time !== wantTime) throw new Error(`schedule reads "${date} ${time}", wanted "${wantDate} ${wantTime}"`);
      const zone = document.querySelector(SEL.zone)?.value || '';
      if (!zone.includes(`(${gmt(whenMs)})`)) throw new Error(`TikTok zone is "${zone}", this browser is ${gmt(whenMs)}`);
      return { date, time, zone };
    },

    // Press "Schedule"/"Post"; a confirm dialog of the same post (content check still running) is
    // accepted once. Done when Studio leaves the upload page (it opens the post list).
    async submit() {
      const btn = await waitFor(SEL.postButton, { what: 'Post/Schedule button' });
      const off = () => btn.disabled || btn.getAttribute('aria-disabled') === 'true';
      for (const end = Date.now() + 10 * 60000; off() && Date.now() < end;) await sleep(1000);
      if (off()) throw new Error(`"${text(btn)}" stayed disabled for 10 min`);
      const label = text(btn);
      btn.click();
      let confirmed = '';
      for (const end = Date.now() + 180000; Date.now() < end; await sleep(1000)) {
        if (!location.pathname.includes('/upload') || !btn.isConnected) {
          return { button: label, confirm: [confirmed, text($(SEL.toast)) || 'left the upload page'].filter(Boolean).join(' · ') };
        }
        const err = text($(SEL.toast));
        if (/fail|error|try again|couldn.t|limit/i.test(err)) throw new Error(`TikTok said "${err}" after "${label}"`);
        const dlg = [...document.querySelectorAll(SEL.dialog)].find((d) => d.getClientRects().length);
        const ok = !confirmed && dlg && button(dlg, /^(post now|schedule|continue|confirm|post)$/i);
        if (ok) { confirmed = `${text(dlg).split('\n')[0]} → ${text(ok)}`; ok.click(); }
      }
      throw new Error(`still on the upload page 180 s after "${label}"${confirmed ? ` (${confirmed})` : ''}`);
    },

    // On /tiktokstudio/content: every row with caption, time ("Nov 12, 7:00 AM (GMT+7) Saigon" for a
    // scheduled one) and match = same caption.
    async findScheduled(caption) {
      const rows = await listRows();
      return rows.map((r) => ({ ...r, match: same(r.caption, caption) }));
    },
  };
})();
