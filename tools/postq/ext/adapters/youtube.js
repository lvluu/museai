// YouTube Studio upload dialog (studio.youtube.com, opened via youtube.com/upload).
// Every selector lives in SEL: when Studio changes, fix it here. Run a --dry-run item after a fix.
globalThis.postqAdapters.youtube ??= (() => {
  const { sleep, $, waitFor, typeInto, setValue, key, takeFile, attach } = globalThis.postqLib;

  const SEL = {
    fileInput: ['ytcp-uploads-file-picker input[type=file]', 'input[type=file][name=Filedata]'],
    channelName: ['#entity-name'],
    avatar: ['#avatar-btn', 'ytcp-topbar-menu-button-renderer button'],
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
  async function setRelated(want) {
    (await waitFor(SEL.relatedTrigger, { what: 'Related video field' })).click();
    await waitFor([SEL.relatedCards], { timeout: 40000, what: 'related video list' });
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

    whoami() {
      return { name: text($(SEL.channelName, { hidden: true })), id: location.pathname.match(/channel\/(UC[\w-]+)/)?.[1] };
    },

    // Avatar → Switch account → the channel titled `name`. The click reloads Studio on that channel,
    // so it fires after this step has answered; the caller reopens the upload page.
    async switchChannel(name) {
      (await waitFor(SEL.avatar, { what: 'account avatar' })).click();
      const until = async (fn, what) => {
        for (const end = Date.now() + 15000; Date.now() < end; await sleep(250)) {
          const v = fn();
          if (v) return v;
        }
        throw new Error(`not found after 15s: ${what}`);
      };
      (await until(() => [...document.querySelectorAll(SEL.menuLinks)]
        .find((e) => /switch account/i.test(text(e)))?.querySelector('tp-yt-paper-item'), 'Switch account entry')).click();
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
          const ack = [...warnDlg.querySelectorAll('ytcp-button, button')]
            .find((b) => /got it|schedule anyway|publish anyway|^ok$/i.test(text(b)) && b.getBoundingClientRect().height);
          if (ack) {
            ack.click();
            await sleep(1500);
            // Back on the form with Schedule still there: press it again.
            if (done.isConnected && done.getBoundingClientRect().height && !off()) done.click();
            continue;
          }
        }
        if (warnDlg) throw new Error(`YouTube checks warning after "${text(done)}": ${text($(['ytcp-prechecks-warning-dialog'])).slice(0, 200)}`);
      }
      throw new Error(`no "Video scheduled/published" confirmation 90 s after pressing "${text(done)}"`);
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
      const save = $(SEL.save);
      const dirty = () => save && save.getAttribute('aria-disabled') !== 'true' && !save.hasAttribute('disabled');
      const thumbSrc = () => $(SEL.thumbShown, { hidden: true })?.src || '';
      const thumbWas = thumbSrc();
      if (item.cover) {
        const input = $(SEL.thumbInput, { hidden: true });
        if (!input) throw new Error('edit page: no thumbnail upload (custom thumbnails need a verified channel)');
        attach(input, takeFile('cover', item.cover.name, item.cover.type));
        for (const end = Date.now() + 30000; !dirty() && Date.now() < end;) await sleep(500);
        if (!dirty()) throw new Error(`edit page: thumbnail "${item.cover.name}" was not accepted (over 2 MB / wrong type?)`);
        ok.push('thumbnail uploaded');
      }
      if (dirty()) {
        save.click();
        for (const end = Date.now() + 90000; dirty() && Date.now() < end;) await sleep(500);
        if (dirty()) throw new Error('edit page: Save did not finish within 90 s');
        ok.push('saved');
      }
      if (item.cover) {
        // Studio bumps the thumbnail's ?v= once the new image is stored.
        for (const end = Date.now() + 30000; thumbSrc() === thumbWas && Date.now() < end;) await sleep(500);
        if (thumbSrc() === thumbWas) throw new Error('edit page: thumbnail did not change after Save');
      }

      const vis = text(await waitFor(SEL.visibilityShown, { what: 'visibility on edit page' }));
      if (!whenMs) {
        if (!new RegExp(item.visibility, 'i').test(vis)) throw new Error(`edit page: visibility reads "${vis}", wanted ${item.visibility}`);
        return [...ok, `visibility ✓ ${item.visibility}`];
      }
      if (!/scheduled/i.test(vis)) throw new Error(`edit page: visibility reads "${vis}", wanted Scheduled (still a draft?)`);
      const when = new Date(whenMs);
      const sameDay = (shown) => {
        const d = new Date(Date.parse(shown));
        return !isNaN(d) && d.getFullYear() === when.getFullYear() && d.getMonth() === when.getMonth() && d.getDate() === when.getDate();
      };
      const readSchedule = async () => {
        (await waitFor(SEL.visibilityOpen)).click();
        const pop = await waitFor(SEL.visibilityPopover, { what: 'visibility popover' });
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
        if (!dirty()) throw new Error(`edit page: schedule fix (was ${was}) did not make the page savable`);
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
