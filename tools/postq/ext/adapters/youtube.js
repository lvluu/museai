// YouTube Studio upload dialog (studio.youtube.com, opened via youtube.com/upload).
// Every selector lives in SEL: when Studio changes, fix it here. Run a --dry-run item after a fix.
globalThis.postqAdapters.youtube ??= (() => {
  const { sleep, $, waitFor, typeInto, setValue, key, takeFile, attach } = globalThis.postqLib;

  const SEL = {
    fileInput: ['ytcp-uploads-file-picker input[type=file]', 'input[type=file][name=Filedata]'],
    channelName: ['#entity-name'],
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
    afterDone: ['ytcp-video-share-dialog', 'ytcp-uploads-still-processing-dialog', 'ytcp-prechecks-warning-dialog'],
    closeAfterDone: ['ytcp-video-share-dialog #close-button', 'ytcp-uploads-still-processing-dialog #close-button'],
    // Video edit page (studio.youtube.com/video/<id>/edit), used to check the post after Schedule/Publish.
    save: ['ytcp-button#save', '#save'],
    thumbShown: ['ytcp-thumbnail-uploader img[src*="ytimg"]', 'ytcp-video-thumbnail-editor img[src*="ytimg"]'],
    visibilityShown: ['ytcp-video-metadata-visibility'],
    visibilityOpen: ['ytcp-video-metadata-visibility #select-button'],
    visibilityPopover: ['ytcp-video-visibility-select'],
  };

  const text = (el) => (el?.innerText || el?.textContent || '').trim();
  // Playlist names compare without case or Vietnamese accents.
  const fold = (s) => s.replace(/đ/g, 'd').replace(/Đ/g, 'D').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();

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
    const card = cards.find((c) => {
      const t = fold(title(c));
      return t === prefix || (t.startsWith(prefix) && !/\d/.test(t[prefix.length] || ''));
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
      const when = new Date(whenMs);
      const lang = document.documentElement.lang || 'en';

      // Date first: changing the date resets the time to 12:00 AM.
      (await waitFor(SEL.dateTrigger)).click();
      const dateInput = await waitFor(SEL.dateInput, { what: 'date input' });
      const date = when.toLocaleDateString(lang, { month: 'short', day: 'numeric', year: 'numeric' });
      setValue(dateInput, date);
      // A synthetic Enter does not commit the picker; submitting its form does (checked 2026-11).
      dateInput.closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      await sleep(500);
      if ($(SEL.dateInput)) $(SEL.dateTrigger)?.click(); // close the calendar if it stayed open
      await sleep(500);

      const timeInput = await waitFor(SEL.timeInput, { what: 'time input' });
      const h12 = /am|pm/i.test(timeInput.value);
      const time = when.toLocaleTimeString(h12 ? 'en-US' : 'en-GB', { hour: 'numeric', minute: '2-digit', hour12: h12 });
      timeInput.focus();
      setValue(timeInput, time);
      key(timeInput, 'Enter');
      timeInput.blur();
      await sleep(500);

      const shownDate = text($(SEL.dateTrigger));
      const shownTime = timeInput.value;
      if (!shownDate.includes(String(when.getFullYear())) || !shownDate.includes(String(when.getDate()))) {
        throw new Error(`date reads back as "${shownDate}", wanted ${date}`);
      }
      if (shownTime.replace(/\s/g, '').toLowerCase() !== time.replace(/\s/g, '').toLowerCase()) {
        throw new Error(`time reads back as "${shownTime}", wanted ${time}`);
      }
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
        const shown = [...document.querySelectorAll([...SEL.afterDone, 'tp-yt-paper-dialog'].join(','))]
          .filter((d) => d.getBoundingClientRect().height).map(text);
        const hit = shown.find((t) => ok.test(t));
        if (hit) return { url, button: text(done), confirm: hit.replace(/\s+/g, ' ').slice(0, 160) };
        if ($(['ytcp-prechecks-warning-dialog'])) throw new Error(`YouTube checks warning after "${text(done)}": ${text($(['ytcp-prechecks-warning-dialog'])).slice(0, 200)}`);
      }
      throw new Error(`no "Video scheduled/published" confirmation 90 s after pressing "${text(done)}"`);
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
          ok.push(`related ✓ ${shown.includes(want) ? text($(SEL.relatedShown)).split('\n').pop() : await setRelated(item.related)}`);
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
      (await waitFor(SEL.visibilityOpen)).click();
      const pop = await waitFor(SEL.visibilityPopover, { what: 'visibility popover' });
      await sleep(800);
      const shownDate = text(await waitFor(SEL.dateTrigger, { what: 'scheduled date' }));
      const shownTime = (await waitFor(SEL.timeInput, { what: 'scheduled time' })).value;
      key(document.activeElement || pop, 'Escape');
      if ($(SEL.dateTrigger)) key(pop, 'Escape');
      await sleep(600);
      const when = new Date(whenMs);
      const d = new Date(Date.parse(shownDate));
      if (isNaN(d) || d.getFullYear() !== when.getFullYear() || d.getMonth() !== when.getMonth() || d.getDate() !== when.getDate()) {
        throw new Error(`edit page: scheduled date reads "${shownDate}", wanted ${when.toDateString()}`);
      }
      const h12 = /am|pm/i.test(shownTime);
      const time = when.toLocaleTimeString(h12 ? 'en-US' : 'en-GB', { hour: 'numeric', minute: '2-digit', hour12: h12 });
      if (shownTime.replace(/\s/g, '').toLowerCase() !== time.replace(/\s/g, '').toLowerCase()) {
        throw new Error(`edit page: scheduled time reads "${shownTime}", wanted ${time}`);
      }
      if (dirty()) throw new Error('edit page: closing the schedule popover left unsaved changes');
      return [...ok, `schedule ✓ ${shownDate} ${shownTime}`];
    },
  };
})();
