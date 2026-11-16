# Video folder template

Copy this folder to `production/NNN-slug/` for each new video, then copy these into it from `templates/`:

- `research-template.md` → `research.md`
- `script-template.md` → `script.md`
- `storyboard-template.md` → `storyboard.md`
- `qa-checklist.md` → `qa-checklist.md`

Subfolders:

| Folder | Contents |
|---|---|
| `voice/` | Narration exports (`narration_v1.wav`) |
| `illustrations/` | `S##-name_v#.png` |
| `music/` | Licensed tracks and SFX (log them in the asset licence log) |
| `project/` | DaVinci Resolve project / .drp |
| `exports/` | Final MP4, thumbnail, SRT captions |

**Rule:** keep `research.md` and `script.md` separate so unverified notes never leak into the narration.
