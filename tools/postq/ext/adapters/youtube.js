// YouTube Studio upload dialog (studio.youtube.com, opened via youtube.com/upload).
// Every selector lives in SEL: when Studio changes, fix it here. Run a --dry-run item after a fix.
globalThis.postqAdapters.youtube ??= (() => {
  const { sleep, $, waitFor, typeInto, setValue, key, takeFile, attach } = globalThis.postqLib;

  const SEL = {
    fileInput: ['ytcp-uploads-file-picker input[type=file]', 'input[type=file][name=Filedata]'],
    channelName: ['#entity-name'],
    // Only the account avatar. The topbar's first button is the nav-drawer hamburger (it opened Dashboard | Content | ...).
    avatar: ['#avatar-btn'],
    menuLinks: 'ytd-compact-link-renderer',
    accountItems: 'ytd-account-item-renderer', // #channel-title holds the channel name
    title: ['#title-textarea #textbox', 'ytcp-social-suggestions-textbox#title-textarea #textbox'],
    description: ['#description-textarea #textbox'],
    kids: (mfk) => [`tp-yt-paper-radio-button[name=${mfk ? 'VIDEO_MADE_FOR_KIDS_MFK' : 'VIDEO_MADE_FOR_KIDS_NOT_MFK'}]`],
    showMore: ['ytcp-uploads-details #toggle-button', '#toggle-button'],
    tags: ['#tags-container input', 'ytcp-free-text-chip-bar input'],
    playlistTrigger: ['ytcp-video-metadata-playlists ytcp-dropdown-trigger'],
    playlistItems: 'ytcp-playlist-dialog #items ytcp-ve', // each: span.label + [role=checkbox]
    playlistDone: ['ytcp-playlist-dialog .done-button'],
    // Shorts only: "Related video" links the Short to another video of the channel (public ones only).
    relatedTrigger: ['#linked-video-editor-link ytcp-dropdown-trigger'],
    relatedShown: ['#linked-video-editor-link'],
    relatedSearch: ['ytcp-video-pick-dialog #search-yours'],
    relatedCards: 'ytcp-video-pick-dialog ytcp-entity-card', // .title holds the video title
    relatedClose: ['ytcp-video-pick-dialog #close'],
    thumbInput: ['ytcp-thumbnail-uploader input[type=file]', 'ytcp-thumbnails-compact-editor-uploader input[type=file]', '#file-loader'],
    next: ['#next-button'],
    visibilityStep: ['ytcp-uploads-review #privacy-radios', '#privacy-radios'],
    privacy: (v) => [`tp-yt-paper-radio-button[name=${v.toUpperCase()}]`],
    scheduleExpand: ['#second-container-expand-button'],
    dateTrigger: ['#datepicker-trigger'],
    dateInput: ['ytcp-date-picker tp-yt-paper-input input', 'ytcp-date-picker input'],
    timeInput: ['#time-of-day-container input', 'ytcp-form-input-container#time-of-day-container input'],
    progress: ['ytcp-video-upload-progress .progress-label', 'ytcp-video-upload-progress'],
    videoLink: ['ytcp-video-info a[href*="youtu"]', '.video-url-fadeable a'],
    done: ['#done-button'],
    uploadProgress: 'ytcp-video-upload-progress', // inside the upload form's own dialog
    afterDone: ['ytcp-video-share-dialog', 'ytcp-uploads-still-processing-dialog', 'ytcp-prechecks-warning-dialog'],
    closeAfterDone: ['ytcp-video-share-dialog #close-button', 'ytcp-uploads-still-processing-dialog #close-button'],
    // Video edit page (studio.youtube.com/video/<id>/edit), used to check the post after Schedule/Publish.
    save: ['ytcp-button#save', '#save'],
    editDraft: 'ytcp-button, button', // the one reading "Edit draft"
    thumbShown: ['ytcp-thumbnail-uploader img[src*="ytimg"]', 'ytcp-video-thumbnail-editor img[src*="ytimg"]'],
    visibilityShown: ['ytcp-video-metadata-visibility'],
    visibilityOpen: ['ytcp-video-metadata-visibility #select-button'],
    visibilityPopover: ['ytcp-video-visibility-select'],
  };

  const text = (el) => (el?.innerText || el?.textContent || '').trim();
  // Names compare without case, Vietnamese accents, emoji or punctuation ("I’d Live 🏡" == "I'd Live").
  const fold = (s) => s.replace(/đ/g, 'd').replace(/Đ/g, 'D').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();

  // want: "Tập 36" (title prefix) or a full title; "latest:Tập" = newest public video whose title starts so.
  // Content list: 50 rows a page (Studio's largest) instead of 30, so scans turn fewer pages.
async function rows50() {
  const sel = document.querySelector('ytcp-select#page-size');
  if (!sel || /\b50\b/.test(text(sel.querySelector('#trigger') || sel))) return;
  const count = () => document.querySelectorAll('ytcp-video-row').length;
  const before = count();
  const total = +(text(document.querySelector('ytcp-table-footer')).match(/(\d+)\s*$/)?.[1] || 0);
  if (total && total <= before) return; // everything fits on this page already
  (sel.querySelector('#trigger') || sel).click();
  for (let t = 0; t < 20; t++) {
    const it = [...document.querySelectorAll('tp-yt-paper-item[test-id="50"]')].find((e) => e.offsetParent);
    if (it) { it.click(); break; }
    await sleep(150);
  }
  for (let t = 0; t < 60 && count() <= before; t++) await sleep(250); // page 1 refills with up to 50 rows
  await sleep(400);
}

async function setRelated(want) {
    // The trigger sometimes opens nothing (click lands before Studio wires it): retry the click, not just wait.
    let opened = false;
    for (let attempt = 1; attempt <= 3 && !opened; attempt++) {
      (await waitFor(SEL.relatedTrigger, { what: 'Related video field' })).click();
      opened = await waitFor([SEL.relatedCards], { timeout: 12000, what: 'related video list' }).then(() => true, () => false);
      // Dialog in the DOM but cards not laid out yet (slow channel list): give it time instead of closing it.
      if (!opened && document.querySelector('ytcp-video-pick-dialog')) {
        opened = await waitFor([SEL.relatedCards], { timeout: 45000, what: 'related video list (slow)' }).then(() => true, () => false);
      }
      if (!opened) { $(SEL.relatedClose)?.click(); key(document.body, 'Escape'); await sleep(1500); }
    }
    if (!opened) {
      const dlg = document.querySelector('ytcp-video-pick-dialog');
      const state = dlg
        ? `dialog open, ${dlg.querySelectorAll('ytcp-entity-card').length} cards, text "${text(dlg).slice(0, 80)}"`
        : `no dialog, hidden=${document.hidden}, field "${text($(SEL.relatedShown, { hidden: true })).slice(0, 60)}"`;
      throw new Error(`related video list did not open after 3 clicks (${state})`);
    }
    const latest = want.startsWith('latest:');
    const prefix = fold(latest ? want.slice(7) : want);
    const search = $(SEL.relatedSearch);
    if (search && !latest) {
      setValue(search, want);
      await sleep(2000);
    }
    const cards = [...document.querySelectorAll(SEL.relatedCards)].filter((c) => c.getBoundingClientRect().height);
    const title = (c) => text(c.querySelector('.title'));
    // "Tập 3" must not pick "Tập 30": the prefix has to end at a non-digit.
    // "latest:" alone = the newest video in the list (Studio lists newest first).
    const card = cards.find((c) => {
      const t = fold(title(c));
      return !prefix || t === prefix || (t.startsWith(prefix) && !/\d/.test(t[prefix.length] || ''));
    });
    if (!card) {
      $(SEL.relatedClose)?.click();
      throw new Error(`no public video "${want}" to set as related (first shown: ${cards.slice(0, 3).map(title).join(' / ')})`);
    }
    const picked = title(card);
    card.click();
    await sleep(1000);
    if ($(SEL.relatedClose)) $(SEL.relatedClose).click();
    const shown = text($(SEL.relatedShown));
    if (!fold(shown).includes(fold(picked))) throw new Error(`related video reads back as "${shown}", wanted "${picked}"`);
    return picked;
  }

  const sameTime = (a, b) => a.replace(/\s/g, '').toLowerCase() === b.replace(/\s/g, '').toLowerCase();
  const timeFor = (when, shown) => when.toLocaleTimeString(/am|pm/i.test(shown) ? 'en-US' : 'en-GB',
    { hour: 'numeric', minute: '2-digit', hour12: /am|pm/i.test(shown) });

  // Fills the open schedule picker (upload form or edit page popover) with `when`, local time.
  // Date first: changing the date resets the time to 12:00 AM, and the date can land a moment late,
  // so the time is re-read after a pause and typed again when it got reset.
  async function setWhen(when) {
    const lang = document.documentElement.lang || 'en';
    (await waitFor(SEL.dateTrigger)).click();
    const dateInput = await waitFor(SEL.dateInput, { what: 'date input' });
    const date = when.toLocaleDateString(lang, { month: 'short', day: 'numeric', year: 'numeric' });
    setValue(dateInput, date);
    // A synthetic Enter does not commit the picker; submitting its form does (checked 2026-11).
    dateInput.closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await sleep(500);
    if ($(SEL.dateInput)) $(SEL.dateTrigger)?.click(); // close the calendar if it stayed open
    await sleep(800);
    const shownDate = text($(SEL.dateTrigger));
    if (!shownDate.includes(String(when.getFullYear())) || !shownDate.includes(String(when.getDate()))) {
      throw new Error(`date reads back as "${shownDate}", wanted ${date}`);
    }
    const timeInput = await waitFor(SEL.timeInput, { what: 'time input' });
    const time = timeFor(when, timeInput.value);
    for (let i = 0; i < 3 && !sameTime(timeInput.value, time); i++) {
      timeInput.focus();
      setValue(timeInput, time);
      key(timeInput, 'Enter');
      timeInput.blur();
      await sleep(1500);
    }
    if (!sameTime(timeInput.value, time)) throw new Error(`time reads back as "${timeInput.value}", wanted ${time}`);
    return { shownDate: text($(SEL.dateTrigger)), shownTime: timeInput.value };
  }

  async function addToPlaylist(name) {
    (await waitFor(SEL.playlistTrigger, { what: 'playlist dropdown' })).click();
    await waitFor(['ytcp-playlist-dialog #items ytcp-ve'], { what: 'playlist list' });
    const items = [...document.querySelectorAll(SEL.playlistItems)];
    const item = items.find((i) => fold(text(i.querySelector('.label'))) === fold(name));
    if (!item) {
      $(SEL.playlistDone)?.click();
      throw new Error(`no playlist "${name}" on this channel (has: ${items.map((i) => text(i.querySelector('.label'))).join(', ')})`);
    }
    const box = item.querySelector('[role=checkbox]');
    if (box.getAttribute('aria-checked') !== 'true') box.click();
    await sleep(300);
    if (box.getAttribute('aria-checked') !== 'true') throw new Error(`playlist "${name}" did not tick`);
    (await waitFor(SEL.playlistDone)).click();
    await sleep(600);
    const shown = text($(SEL.playlistTrigger));
    if (!fold(shown).includes(fold(name))) throw new Error(`playlist reads back as "${shown}"`);
  }

  return {
    async ready() {
      await waitFor(SEL.fileInput, { hidden: true, timeout: 45000, what: 'upload dialog (are you logged in to YouTube?)' });
      return location.href.split('?')[0];
    },

    // Any Studio page (dashboard, content): the top bar is up. Cheaper than the upload dialog.
    async studio() {
      await waitFor(SEL.avatar, { hidden: true, timeout: 45000, what: 'Studio top bar (are you logged in to YouTube?)' });
      await waitFor(SEL.channelName, { hidden: true, timeout: 15000, what: 'channel name' });
      return location.href.split('?')[0];
    },

    whoami() {
      return { name: text($(SEL.channelName, { hidden: true })), id: location.pathname.match(/channel\/(UC[\w-]+)/)?.[1] };
    },

    // Avatar → Switch account → the channel titled `name`. The click reloads Studio on that channel,
    // so it fires after this step has answered; the caller reopens the upload page.
    async switchChannel(name) {
      const until = async (fn, what, ms = 15000) => {
        for (const end = Date.now() + ms; Date.now() < end; await sleep(250)) {
          const v = fn();
          if (v) return v;
        }
        throw new Error(`not found after ${ms / 1000}s: ${what}`);
      };
      // Studio's menu markup varies (compact links, paper items, plain links): match any menu entry by its text.
      const entryOf = () => [...document.querySelectorAll(`${SEL.menuLinks}, tp-yt-paper-item, yt-multi-page-menu-section-renderer a, a, [role=menuitem], [role=menuitem] *`)]
        .filter((e) => e.getBoundingClientRect().height && /switch account/i.test(text(e)))
        .sort((a, b) => text(a).length - text(b).length)[0];
      // The avatar click sometimes opens the nav drawer (Dashboard | Content | ...) or lands before the menu
      // renders. Retry: Escape, re-click the avatar, wait for the entry each time.
      let entry = null;
      let seen = [];
      for (let attempt = 1; attempt <= 3 && !entry; attempt++) {
        (await waitFor(SEL.avatar, { what: 'account avatar' })).click();
        entry = await until(() => entryOf(), 'Switch account entry', 4000).catch(() => null);
        if (!entry) {
          seen = [...document.querySelectorAll('tp-yt-paper-item, ytd-compact-link-renderer, [role=menuitem]')]
            .filter((e) => e.getBoundingClientRect().height).map((e) => text(e)).filter(Boolean).slice(0, 8);
          key(document.body, 'Escape');
          await sleep(1000);
        }
      }
      if (!entry) throw new Error(`not found after 3 avatar clicks: Switch account entry; menu shows: ${seen.join(' | ') || 'nothing'}`);
      (entry.querySelector('tp-yt-paper-item') || entry).click();
      const items = await until(() => {
        const all = [...document.querySelectorAll(SEL.accountItems)].filter((i) => text(i.querySelector('#channel-title')));
        return all.length ? all : null;
      }, 'channel list');
      const title = (i) => text(i.querySelector('#channel-title'));
      const item = items.find((i) => fold(title(i)) === fold(name));
      if (!item) {
        key(document.body, 'Escape');
        throw new Error(`no channel "${name}" under this Google account (has: ${items.map(title).join(', ')})`);
      }
      setTimeout(() => (item.querySelector('tp-yt-paper-icon-item') || item).click(), 200);
      return title(item);
    },

    async setVideo(name, type) {
      attach($(SEL.fileInput, { hidden: true }), takeFile('video', name, type));
      await waitFor(SEL.title, { timeout: 60000, what: 'details form after picking the video' });
      // Studio creates the draft (and its link) a moment after the form shows; fields typed before
      // that get overwritten by the draft's defaults (filename title, channel description).
      await waitFor(SEL.videoLink, { hidden: true, timeout: 120000, what: 'video link (draft not created)' });
      await sleep(1500);
      return true;
    },

    async fill(item) {
      const warn = [];
      const title = await waitFor(SEL.title);
      await typeInto(title, item.title);
      if (text(title) !== item.title) throw new Error(`title reads back as "${text(title)}"`);
      if (item.caption) {
        const desc = await waitFor(SEL.description);
        await typeInto(desc, item.caption);
        if (text(desc).replace(/\s+/g, ' ') !== item.caption.trim().replace(/\s+/g, ' ')) warn.push('description read-back differs');
      }
      if (item.playlist) await addToPlaylist(item.playlist);
      if (item.related) {
        if ($(SEL.relatedTrigger)) warn.push(`related: ${await setRelated(item.related)}`);
        else warn.push('no Related video field (not detected as a Short?)');
      }
      (await waitFor(SEL.kids(item.made_for_kids), { what: 'made-for-kids radio' })).click();
      if (item.tags?.length) {
        $(SEL.showMore)?.click();
        await sleep(500);
        const tags = $(SEL.tags);
        if (tags) {
          tags.focus();
          setValue(tags, item.tags.join(','));
          key(tags, 'Enter');
          tags.blur();
        } else warn.push('tags box not found');
      }
      return warn;
    },

    // Details -> Video elements -> Checks -> Visibility.
    async toVisibility() {
      for (let i = 0; i < 5 && !$(SEL.visibilityStep); i++) {
        (await waitFor(SEL.next)).click();
        await sleep(1200);
      }
      await waitFor(SEL.visibilityStep, { what: 'visibility step' });
      return true;
    },

    // whenMs: epoch ms or null. Studio schedules in the browser's local time zone.
    async visibility(item, whenMs) {
      if (!whenMs) {
        (await waitFor(SEL.privacy(item.visibility))).click();
        return { mode: item.visibility };
      }
      (await waitFor(SEL.scheduleExpand, { what: 'Schedule section' })).click();
      await sleep(600);
      const { shownDate, shownTime } = await setWhen(new Date(whenMs));
      return { mode: 'scheduled', date: shownDate, time: shownTime, zone: Intl.DateTimeFormat().resolvedOptions().timeZone };
    },

    // Upload keeps running in this tab: closing it before the upload ends loses the video.
    progress() {
      const label = text($(SEL.progress, { hidden: true }));
      const uploading = /\d+\s*%/.test(label) && /upload/i.test(label);
      return { label, uploading, url: $(SEL.videoLink, { hidden: true })?.href || null };
    },

    // Schedule/Publish turns enabled once Studio accepts the upload; wait for it, then press it.
    async submit() {
      const done = await waitFor(SEL.done);
      const off = () => done.hasAttribute('disabled') || done.getAttribute('aria-disabled') === 'true';
      for (const end = Date.now() + 15 * 60000; off() && Date.now() < end;) await sleep(1000);
      if (off()) throw new Error(`"${text(done)}" stayed disabled for 15 min: a required field is missing?`);
      const url = $(SEL.videoLink, { hidden: true })?.href || null;
      done.click();
      // Only Studio's own confirmation counts; anything else (a checks warning, nothing) is a failure.
      const ok = /video (scheduled|published)|still processing|processing will begin/i;
      for (const end = Date.now() + 90000; Date.now() < end; await sleep(1000)) {
        // Not the upload form's dialog: its progress label reads "Processing will begin shortly" while
        // the save is still running, and leaving the page then leaves the video a draft.
        const shown = [...document.querySelectorAll([...SEL.afterDone, 'tp-yt-paper-dialog'].join(','))]
          .filter((d) => d.getBoundingClientRect().height && !d.querySelector(SEL.uploadProgress)).map(text);
        const hit = shown.find((t) => ok.test(t));
        if (hit) return { url, button: text(done), confirm: hit.replace(/\s+/g, ' ').slice(0, 160) };
        // "We're still checking your content": YouTube finishes the checks after scheduling, so
        // acknowledge it ("Got it") and keep going. Any other checks warning stops the post.
        const warnDlg = $(['ytcp-prechecks-warning-dialog']);
        if (warnDlg && /still checking/i.test(text(warnDlg))) {
          const btns = [...document.querySelectorAll('ytcp-button, button, tp-yt-paper-button, [role=button]')]
            .filter((x) => x.getBoundingClientRect().height);
          const label = (x) => `${text(x)} ${x.getAttribute('aria-label') || ''}`.trim();
          const ack = btns.find((x) => /got it|schedule anyway|publish anyway/i.test(label(x)));
          if (ack) ack.click();
          else key(warnDlg, 'Escape');
          await sleep(2000);
          // Shown after Studio saved the schedule (checked 2026-11: the video lists as Scheduled);
          // the edit-page check right after confirms it, and finishes it if it is still a draft.
          return { url, button: text(done), confirm: 'still checking content (YouTube finishes the checks itself)' };
        }
        if (warnDlg) throw new Error(`YouTube checks warning after "${text(done)}": ${text($(['ytcp-prechecks-warning-dialog'])).slice(0, 200)}`);
      }
      throw new Error(`no "Video scheduled/published" confirmation 90 s after pressing "${text(done)}"`);
    },

    // Channel content > Shorts, every page: [{ id, title, vis }]. Lets a post find a copy an earlier,
    // interrupted run already uploaded (its id never reached the queue) instead of uploading again.
    async uploads() {
      await waitFor(['ytcp-video-row', 'ytcp-video-list-empty-state, #empty-state'], { timeout: 60000, what: 'content list' });
      await sleep(1500);
      await rows50();
      const seen = new Map();
      for (let n = 0; n < 20; n++) {
        for (const r of document.querySelectorAll('ytcp-video-row')) {
          // Drafts have no link: their thumbnail (ytimg.com/vi/<id>/…) still names the video.
          const id = [...r.querySelectorAll('a[href]')].map((a) => a.href.match(/(?:shorts\/|video\/|[?&]v=)([\w-]{11})/)?.[1])
            .concat([...r.querySelectorAll('img')].map((i) => i.src.match(/\/vi\/([\w-]{11})\//)?.[1])).find(Boolean);
          if (id) seen.set(id, { id, title: text(r.querySelector('#video-title')), vis: text(r.querySelector('.tablecell-visibility')),
            date: text(r.querySelector('.tablecell-date')).replace(/\s+/g, ' ') });
        }
        const next = $(['#navigate-after']);
        if (!next || next.disabled || next.getAttribute('aria-disabled') === 'true') break;
        const first = document.querySelector('ytcp-video-row')?.innerText;
        next.click();
        for (let t = 0; t < 40 && document.querySelector('ytcp-video-row')?.innerText === first; t++) await sleep(250);
        await sleep(800);
      }
      return [...seen.values()];
    },

    // Content > Shorts: Options → Delete forever on the row of video `id`, only if it still carries
    // `title` (the list may have shifted since the user looked). Runs on the user's click per video.
    async deleteForever(id, title) {
      await waitFor(['ytcp-video-row'], { timeout: 60000, what: 'content list' });
      await sleep(1500);
      await rows50();
      const rowOf = () => [...document.querySelectorAll('ytcp-video-row')].find((r) =>
        [...r.querySelectorAll('a[href]')].some((a) => a.href.includes(id)) || [...r.querySelectorAll('img')].some((i) => i.src.includes(`/vi/${id}/`)));
      let row = rowOf();
      for (let n = 0; !row && n < 20; n++) {
        const next = $(['#navigate-after']);
        if (!next || next.disabled || next.getAttribute('aria-disabled') === 'true') break;
        const first = document.querySelector('ytcp-video-row')?.innerText;
        next.click();
        for (let t = 0; t < 40 && document.querySelector('ytcp-video-row')?.innerText === first; t++) await sleep(250);
        await sleep(800);
        row = rowOf();
      }
      if (!row) throw new Error(`video ${id} is not on this channel (already deleted?)`);
      const shown = text(row.querySelector('#video-title'));
      if (fold(shown) !== fold(title)) throw new Error(`row ${id} reads "${shown}", expected "${title}": not deleted`);
      row.scrollIntoView({ block: 'center' });
      // Studio renders the row's hover icons (Options among them) only on pointer events that reach
      // the inner row elements; a bare mouseover on the row element is not enough.
      const opts = () => row.querySelector('ytcp-icon-button[aria-label=Options]');
      for (let t = 0; t < 20 && !opts(); t++) {
        const y = row.getBoundingClientRect().top + 10;
        for (const el of [row, row.querySelector('#row-container'), row.querySelector('#hover-items'), row.firstElementChild]) {
          if (!el) continue;
          for (const type of ['pointerover', 'pointerenter', 'mouseover', 'mouseenter', 'mousemove'])
            el.dispatchEvent(new MouseEvent(type, { bubbles: true, composed: true, clientX: 500, clientY: y }));
        }
        await sleep(250);
      }
      if (!opts()) throw new Error(`no Options button on the row of ${id}`);
      opts().click();
      const del = await waitFor(['ytcp-text-menu tp-yt-paper-item[test-id=delete]'], { timeout: 10000, what: 'Delete forever menu item' });
      del.click();
      const box = await waitFor(['ytcp-dialog #confirm-checkbox'], { timeout: 10000, what: 'delete confirmation' });
      (box.querySelector('#checkbox') || box).click();
      const ok = await waitFor(['ytcp-dialog #confirm-button'], { what: 'Delete forever button' });
      const off = () => ok.hasAttribute('disabled') || ok.getAttribute('aria-disabled') === 'true';
      for (let t = 0; t < 20 && off(); t++) await sleep(250);
      if (off()) throw new Error('Delete forever stayed disabled after ticking the box');
      ok.click();
      for (const end = Date.now() + 30000; Date.now() < end; await sleep(500)) {
        if (!rowOf()) return { id, title: shown };
      }
      throw new Error(`pressed Delete forever, ${id} is still listed after 30 s`);
    },

    // Edit page of a video that is still a draft: open its upload form ("Edit draft"). False when not a draft.
    async openDraft() {
      await waitFor(SEL.title, { timeout: 60000, what: 'edit page title (video missing?)' });
      const btn = [...document.querySelectorAll(SEL.editDraft)].find((b) => /^edit draft$/i.test(text(b)) && b.getBoundingClientRect().height);
      if (!btn) return false;
      btn.click();
      await waitFor(SEL.next, { what: 'draft upload form' });
      await sleep(1500);
      return true;
    },

    // Runs on the video's edit page after posting: re-checks every field, fixes title, description,
    // made-for-kids, playlist and related video (then Saves), and reads the schedule back.
    async verify(item, whenMs) {
      const ok = [];
      const title = await waitFor(SEL.title, { timeout: 60000, what: 'edit page title (video missing?)' });
      await sleep(1500);
      if (text(title) !== item.title) {
        await typeInto(title, item.title);
        if (text(title) !== item.title) throw new Error(`edit page: title reads "${text(title)}"`);
        ok.push('title fixed');
      }
      const flat = (s) => s.trim().replace(/\s+/g, ' ');
      if (item.caption) {
        const desc = await waitFor(SEL.description);
        if (flat(text(desc)) !== flat(item.caption)) {
          await typeInto(desc, item.caption);
          ok.push('description fixed');
        }
      }
      // Thumbnail first: it is the step that must not be lost behind a slow playlist / related-video dialog.
      const dirty = () => { const save = $(SEL.save); return save && save.getAttribute('aria-disabled') !== 'true' && !save.hasAttribute('disabled'); };
      const thumbSrc = () => $(SEL.thumbShown, { hidden: true })?.src || '';
      const thumbWas = thumbSrc();
      let thumbLater = false;
      if (item.cover) {
        // Studio renders the thumbnail uploader lazily: wait for it instead of treating a slow page as "no upload".
        let input = $(SEL.thumbInput, { hidden: true });
        for (const end = Date.now() + 25000; !input && Date.now() < end;) { await sleep(500); input = $(SEL.thumbInput, { hidden: true }); }
        // A channel that restricts custom thumbnails still posts, with YouTube's default frame; the cover
        // stays in the covers folder to set by hand later.
        if (!input) {
          thumbLater = true;
          ok.push('thumbnail skipped: channel has no custom thumbnail upload (not verified), set it later');
        } else attach(input, takeFile('cover', item.cover.name, item.cover.type));
        // Accepted = Save lights up, or the shown thumbnail changes (Studio sometimes swaps the image
        // without enabling Save until it finished processing it).
        const took = () => dirty() || (thumbSrc() && thumbSrc() !== thumbWas);
        // "Daily custom thumbnail limit reached" (2026-11-06, up to 24 h): close the dialog and post
        // without the custom thumbnail (YouTube's default frame). The thumbnail is set later by hand.
        const limit = () => [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, [role=dialog]')]
          .find((d) => d.offsetParent !== null && /custom thumbnail limit/i.test(text(d)));
        for (const end = Date.now() + 60000; !thumbLater && !took() && Date.now() < end;) {
          const dlg = limit();
          if (dlg) {
            [...dlg.querySelectorAll('button, ytcp-button, tp-yt-paper-button')].find((b) => /^\s*close\s*$/i.test(text(b)))?.click();
            thumbLater = true;
            ok.push('thumbnail skipped: daily limit reached, set it later');
            break;
          }
          await sleep(500);
        }
        if (!thumbLater && !took()) {
          attach(input, takeFile('cover', item.cover.name, item.cover.type));
          for (const end = Date.now() + 30000; !took() && Date.now() < end;) await sleep(500);
        }
        if (!thumbLater) {
          if (!took()) {
            thumbLater = true;
            ok.push(`thumbnail skipped: "${item.cover.name}" was not accepted (over 2 MB / wrong type?), set it later`);
          } else ok.push('thumbnail uploaded');
        }
      }
      const kids = $(SEL.kids(item.made_for_kids));
      if (kids && !kids.hasAttribute('checked')) { kids.click(); ok.push('made-for-kids fixed'); }
      if (item.playlist) {
        if (!fold(text($(SEL.playlistTrigger))).includes(fold(item.playlist))) {
          await addToPlaylist(item.playlist);
          ok.push('playlist ticked');
        }
        ok.push(`playlist ✓ ${item.playlist}`);
      }
      if (item.related) {
        if (!$(SEL.relatedTrigger)) ok.push('no Related video field (not a Short?)');
        else {
          const want = fold(item.related.replace(/^latest:/, ''));
          const shown = fold(text($(SEL.relatedShown)));
          // "latest:" has no name to compare against, so it is always (re)picked.
          ok.push(`related ✓ ${want && shown.includes(want) ? text($(SEL.relatedShown)).split('\n').pop() : await setRelated(item.related)}`);
        }
      }
      if (dirty()) {
        $(SEL.save).click();
        for (const end = Date.now() + 240000; dirty() && Date.now() < end;) await sleep(500); // slow under machine load
        if (dirty()) throw new Error('edit page: Save did not finish within 240 s');
        ok.push('saved');
      }
      if (item.cover && !thumbLater) {
        // Studio bumps the thumbnail's ?v= once the new image is stored.
        for (const end = Date.now() + 60000; thumbSrc() === thumbWas && Date.now() < end;) await sleep(500);
        if (thumbSrc() === thumbWas) ok.push('thumbnail skipped: did not change after Save, set it later');
      }

      let vis = text(await waitFor(SEL.visibilityShown, { what: 'visibility on edit page' }));
      // "Pending" shows while Studio still stores the visibility change.
      for (const end = Date.now() + 120000; /pending/i.test(vis) && Date.now() < end; vis = text($(SEL.visibilityShown)) || vis) await sleep(2000);
      if (!whenMs) {
        if (!new RegExp(item.visibility, 'i').test(vis)) throw new Error(`edit page: visibility reads "${vis}", wanted ${item.visibility}`);
        return [...ok, `visibility ✓ ${item.visibility}`];
      }
      if (!/scheduled/i.test(vis)) throw new Error(`edit page: visibility reads "${vis}", wanted Scheduled (still a draft?)`);
      const when = new Date(whenMs);
      const sameDay = (shown) => {
        // Studio's trigger can carry extra words ("Scheduled Nov 13, 2026"): take the date part only.
        const m = String(shown).match(/([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})/);
        const d = m ? new Date(`${m[1]} ${m[2]}, ${m[3]}`) : new Date(Date.parse(shown));
        return !isNaN(d) && d.getFullYear() === when.getFullYear() && d.getMonth() === when.getMonth() && d.getDate() === when.getDate();
      };
      const readSchedule = async () => {
        // A click can land while Studio still re-renders after Save: retry before giving up.
        let pop;
        for (let n = 1; !pop; n++) {
          (await waitFor(SEL.visibilityOpen)).click();
          try { pop = await waitFor(SEL.visibilityPopover, { what: 'visibility popover', timeout: 10000 }); }
          catch (e) { if (n >= 4) throw e; await sleep(2000); }
        }
        await sleep(1200);
        const date = text(await waitFor(SEL.dateTrigger, { what: 'scheduled date' }));
        const time = (await waitFor(SEL.timeInput, { what: 'scheduled time' })).value;
        return { pop, date, time, right: sameDay(date) && sameTime(time, timeFor(when, time)) };
      };
      const closePop = async (pop) => {
        key(document.activeElement || pop, 'Escape');
        if ($(SEL.dateTrigger)) key(pop, 'Escape');
        await sleep(600);
      };
      let s = await readSchedule();
      if (!s.right) {
        // Wrong date/time on the saved video: set it in the popover, Done, Save, read it again.
        const was = `${s.date} ${s.time}`;
        await setWhen(when);
        const doneBtn = [...(s.pop.closest('tp-yt-paper-dialog, ytcp-dialog, tp-yt-iron-dropdown') || document).querySelectorAll('ytcp-button, button')].find((b) => /^(done|save)$/i.test(text(b)) && b.getBoundingClientRect().height);
        if (!doneBtn) throw new Error('edit page: no Done button in the visibility popover');
        doneBtn.click();
        await sleep(1000);
        for (const end = Date.now() + 15000; !dirty() && Date.now() < end;) await sleep(500);
        if (!dirty()) {
          // Diagnostics for the next failure: what the picker shows now, wanted vs read back.
          const now = await readSchedule().catch(() => null);
          throw new Error(`edit page: schedule fix (was ${was}) did not make the page savable · wanted ${when.toISOString()} ` +
            `· picker now "${now?.date}" "${now?.time}" right=${now?.right}`);
        }
        $(SEL.save).click();
        for (const end = Date.now() + 90000; dirty() && Date.now() < end;) await sleep(500);
        if (dirty()) throw new Error('edit page: Save of the schedule fix did not finish within 90 s');
        ok.push(`schedule fixed (was ${was})`);
        s = await readSchedule();
        if (!s.right) {
          await closePop(s.pop);
          throw new Error(`edit page: schedule still reads "${s.date} ${s.time}" after the fix, wanted ${when.toString()}`);
        }
      }
      await closePop(s.pop);
      const shownDate = s.date, shownTime = s.time;
      if (dirty()) throw new Error('edit page: closing the schedule popover left unsaved changes');
      return [...ok, `schedule ✓ ${shownDate} ${shownTime}`];
    },
  };
})();
