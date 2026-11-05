# postq + post-approve

Queue a finished video with its title, caption, schedule and target account. Review it in Chrome
and press Enter: the extension posts it through your own logged-in session (no API keys, no copied cookies).
Built like hotpot's `bbq` / bb-approve.

| Platform | `--platform` | Status |
|---|---|---|
| YouTube (Studio upload dialog) | `youtube` | adapter ready |
| Facebook + Instagram in one post (Meta Business Suite) | `meta --targets facebook,instagram` | queued only, adapter next |
| TikTok | `tiktok` | queued only |
| X | `x` | queued only |

## Install (once)

1. `chrome://extensions` → Developer mode → **Load unpacked** → `tools/postq/ext`
2. Pin **post-approve** (shortcut `Alt+Shift+P`).
3. `ln -s "$PWD/tools/postq/postq" ~/.local/bin/postq`

## Queue

```bash
postq add --platform youtube --account "Chinese Everyday For Everyone" --file out.mp4 \
  --title "3 ways to say hello in Chinese" --caption - --tags chinese,mandarin \
  --at "2026-11-07 19:00" --tz Asia/Ho_Chi_Minh <<'TXT'
Description text…
TXT
postq add ... --dry-run   # fill the form, never press Schedule/Publish; the tab stays open to look at
postq list | results
postq wait <id>           # exit 0 posted/scheduled, 2 failed/discarded, 3 timeout
postq approve <id>        # post without a click; warns when the extension has not polled for 90 s
```

### Episode folders

```bash
postq episode ~/Desktop/"Chinese 01 · Mon 16-11 18h30 · Tiếng Trung mỗi ngày 60 - Xin thử cỡ giày khác"
postq episode DIR --platforms youtube,meta,tiktok,x --dry-run
```

Reads `DIR/captions.txt` (`=== YouTube Shorts  Mon 16-11 18:30 ===` sections): the YouTube title is the
section's first line, the description the rest, the time the header's (year picked so the weekday
matches). The folder's first word picks the series in `SERIES` (top of `postq`): account, playlist and
time zone. `Chinese` → channel "Chinese Everyday For Everyone", playlist "Hội Thoại Tiếng Trung". Shorts also get a **Related video**: `--related "Tập 36"` (or the popup field), else the series rule
(`latest:Tập` = newest public "Tập …" video; only public videos can be linked). The
thumbnail image goes along as the cover. A video already queued for a platform is not queued twice.

Whole series at once (every `Chinese …` folder on the Desktop, posted one after another, no click):

```bash
postq episodes --series Chinese --auto
```

Platforms already ticked on the museai dashboard are skipped. `--auto` and `approve` only hand items to an
extension of version ≥ 0.2 that polled in the last 90 s (older code has no edit-page check); otherwise the
items stay queued for a click.

`add` checks each platform's limits (title/caption length, forbidden characters, tags,
how far ahead it may be scheduled) before anything is queued.

## Approve

Click the icon (badge = pending count). Each card has a video preview, editable title, caption,
publish time (in this browser's time zone, the zone YouTube Studio schedules in), visibility, and a
dry-run box. **Approve** opens the platform in a new tab in front (Studio does not render in a background tab; leave it open until the post finishes) and:

1. checks the logged-in channel/page equals `--account`, else stops (never posts to the wrong account);
2. moves the video into the tab in 4 MB chunks and picks it in the upload form;
3. fills the fields, sets the schedule and reads every value back;
4. waits until the upload is complete and Schedule/Publish turns enabled (up to 15 min), presses it, and
   requires Studio's "Video scheduled/published" confirmation;
5. opens the video's edit page in the same tab, uploads the cover as the custom thumbnail (the upload
   dialog has none for Shorts; needs a verified channel) and checks it as saved: title, description, made-for-kids,
   playlist ticked, related video (fixes and Saves any that drifted), thumbnail changed, visibility Scheduled with the exact
   date and time. Only then is the item archived as scheduled; any mismatch fails it and leaves the tab open.

A post that ends scheduled/posted also ticks its platform on the museai dashboard's card
(`POST /dashboard/posts/<video>`; the dashboard trashes the video once every box is ticked).

A failed post stays pending, its tab is brought to the front, and the error is shown in the popup.
Progress is visible in the popup and in the service worker console (`chrome://extensions` → post-approve → service worker).

## Files

- `postq`: CLI and queue server (`127.0.0.1:8766`, queue in `~/.local/state/postq/queue/`)
- `ext/background.js`: claim → open tab → run the platform flow → archive the result
- `ext/adapters/lib.js`: page helpers (wait, type into editors, chunked file transfer)
- `ext/adapters/<platform>.js`: one adapter per platform. All of its selectors sit in `SEL` at the top, so a UI change is fixed there.
