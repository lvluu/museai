from museai.core import system


def test_tree_cpu_sums_root_and_descendants_only():
    procs = [(10, 1, 5.0), (11, 10, 40.0), (12, 11, 30.0), (20, 1, 99.0)]
    assert system._tree_cpu(procs, 10) == 75.0


def test_level_flags_overload_at_full_cores():
    assert system.level(0.5) == "ok"
    assert system.level(0.8) == "busy"
    assert system.level(1.3) == "overloaded"


def test_cpu_load_reads_this_host():
    cpu = system.cpu_load()
    assert cpu["cores"] >= 1
    assert cpu["level"] in {"ok", "busy", "overloaded"}
    assert cpu["cpu_pct"] is None or 0 <= cpu["cpu_pct"] <= 100
