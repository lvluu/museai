"""Host CPU load for the dashboard: is the machine keeping up with the renders?"""

from __future__ import annotations

import os
import subprocess
from typing import Any

# Share of all cores in use (by load average or by CPU time) at which the host counts as
# busy or overloaded. Load above the core count means runnable work waits for a core.
BUSY = 0.75
OVERLOADED = 1.0


def _processes() -> list[tuple[int, int, float]]:
    """(pid, ppid, %cpu of one core) for every process; empty where `ps` is missing."""
    try:
        out = subprocess.run(
            ["ps", "-A", "-o", "pid=,ppid=,%cpu="],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    procs = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            try:
                procs.append((int(parts[0]), int(parts[1]), float(parts[2].replace(",", "."))))
            except ValueError:
                continue
    return procs


def _tree_cpu(procs: list[tuple[int, int, float]], root: int) -> float:
    """CPU of ``root`` and all its descendants (museai plus the Chromium it launched)."""
    children: dict[int, list[int]] = {}
    cpu = {}
    for pid, ppid, pct in procs:
        children.setdefault(ppid, []).append(pid)
        cpu[pid] = pct
    total, stack, seen = 0.0, [root], set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        total += cpu.get(pid, 0.0)
        stack.extend(children.get(pid, []))
    return total


def level(share: float) -> str:
    if share >= OVERLOADED:
        return "overloaded"
    if share >= BUSY:
        return "busy"
    return "ok"


def cpu_load() -> dict[str, Any]:
    """CPU use as a share of the whole machine (100 = every core busy)."""
    cores = os.cpu_count() or 1
    try:
        load = [round(x, 2) for x in os.getloadavg()]
    except OSError:
        load = None
    procs = _processes()
    cpu_pct = min(sum(p[2] for p in procs) / cores, 100.0) if procs else None
    museai_pct = _tree_cpu(procs, os.getpid()) / cores if procs else None
    share = max(load[0] / cores if load else 0.0, (cpu_pct or 0.0) / 100)
    return {
        "cores": cores,
        "load": load,
        "cpu_pct": None if cpu_pct is None else round(cpu_pct, 1),
        "museai_pct": None if museai_pct is None else round(museai_pct, 1),
        "level": level(share),
    }
