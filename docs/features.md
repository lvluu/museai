# Feature status

Checked live on 2026-11-07 against muse.ai with the browser driver (LXC `muse`, account `shared-1`).
Evidence = what the check printed; rerun with the commands in the last column.

| Feature | Endpoint | Status | How it was checked |
|---|---|---|---|
| Chat | `POST /v1/chat/completions` | works | reply text; code cards come back as fenced blocks |
| Image generation | `POST /v1/images/generations` | works | `file` says WebP, 1919x1279 |
| Image edit | `POST /v1/images/edits` (multipart) | partial | endpoint + upload work (mock test; muse describes the attached picture correctly) but muse's edited image never shows up as an attachment node, so the live call times out. Open: find where muse renders edit results |
| Text to video | `POST /v1/videos`, `GET /v1/videos/{id}` | works | 5 s prompt, done in ~1 min: MP4 (ISO Media), 1280x720 |
| First-frame image to video | same, `image` field | not rechecked today | covered by the existing `muse-video` flow |
| Code / HTML / whole project as zip | `POST /v1/projects` | works | 3 files (index.html, style.css, app.js) in one zip; `app.js` passes `node --check` |
| Streaming chat | `stream: true` | works | SSE chunks |
| Tool calls | `tools` | not supported | muse.ai has no tool API; ignored (TODO C3) |

## How `/v1/projects` works

muse.ai shows code in cards and hides long HTML behind a collapsed card; plain `innerText` loses fences and the HTML file.
The prompt asks for `FILE: <path>` above each block; the driver rebuilds fences from the page (a visible token before
each `<pre>`, climbing past hidden ancestors, one span per line joined with newlines); `core/projects.py` maps blocks
to paths (`FILE:` line, `path=` in the info string, a `path:` comment, or a default name per language), rejects
absolute and `..` paths, and zips them. The reply text and the file list come back with the zip URL.
