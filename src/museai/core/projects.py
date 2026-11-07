"""Turn a chat reply into project files and a zip.

The prompt asks muse for fenced blocks whose info string carries ``path=<file>``.
Replies that ignore that still work: a ``path:`` comment on the first line names
the file, and a single unnamed block gets a default name from its language.
"""

from __future__ import annotations

import io
import posixpath
import re
import zipfile

from ..errors import InvalidRequest

PROJECT_INSTRUCTIONS = (
    "Build the project below. Reply with every file as its own fenced code block. Put the line "
    "`FILE: <path>` right before each block and always open the fence with ```text, whatever the file "
    "type (HTML included), so it is never rendered as a preview. No file may be left out or "
    "abbreviated. Keep prose to one short sentence.\n\nProject: "
)

_FENCE = re.compile(r"^```[ \t]*([^\n`]*)\n(.*?)^```[ \t]*$", re.S | re.M)
_PATH_ATTR = re.compile(r"""(?:path|file|filename|title)\s*=\s*["']?([^\s"']+)""")
_PATH_COMMENT = re.compile(
    r"^\s*(?://|#|<!--|/\*|--)\s*(?:path|file|filename)\s*:\s*([^\s*]+?)\s*(?:-->|\*/)?\s*$", re.I)
_FILE_LINE = re.compile(r"^[\s*`_>-]*(?:file|path|filename)\s*:?\s*[`*_\"']*([\w./-]+?)[`*_\"']*\s*:?\s*$", re.I)
_DEFAULT_NAME = {"html": "index.html", "css": "style.css", "js": "script.js", "javascript": "script.js",
                 "ts": "index.ts", "python": "main.py", "py": "main.py", "json": "data.json",
                 "md": "README.md", "markdown": "README.md", "sh": "run.sh", "bash": "run.sh"}


def safe_path(raw: str) -> str:
    path = posixpath.normpath(raw.strip() or "")
    if not path or path.startswith(("/", "..")) or "/../" in f"/{path}/" or len(path) > 200:
        raise InvalidRequest(f"unsafe file path in reply: {raw!r}")
    return path


def _label_before(text: str, pos: int) -> str | None:
    """Path from a ``FILE: x`` line directly above the fence that starts at ``pos``."""
    lines = text[:pos].rstrip().rsplit("\n", 1)
    m = _FILE_LINE.match(lines[-1]) if lines and lines[-1].strip() else None
    return m.group(1) if m else None


def extract_files(text: str) -> dict[str, str]:
    """Return ``{path: content}`` from the fenced blocks of ``text`` (later blocks win)."""
    text = text.replace("\r\n", "\n")
    blocks = [(m.group(1).strip(), m.group(2), _label_before(text, m.start()))
              for m in _FENCE.finditer(text)]
    files: dict[str, str] = {}
    for info, body, label in blocks:
        name = label
        if (m := _PATH_ATTR.search(info)):
            name = m.group(1)
        elif name is None:
            first, _, rest = body.partition("\n")
            if (m := _PATH_COMMENT.match(first)):
                name, body = m.group(1), rest
        if name is None:
            lang = info.split()[0].lower() if info else ""
            default = _DEFAULT_NAME.get(lang)  # ```text blocks have no language: label only
            if default and default not in files:
                name = default
        if name:
            files[safe_path(name)] = body if body.endswith("\n") else body + "\n"
    return files


def build_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, content in files.items():
            z.writestr(path, content)
    return buf.getvalue()
