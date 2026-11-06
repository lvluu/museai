from __future__ import annotations

import importlib.util
import pathlib

_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "import_account.py"
_spec = importlib.util.spec_from_file_location("import_account", _path)
import_account = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(import_account)


def test_replace_drops_same_label_and_invalid_but_keeps_new_and_healthy():
    accounts = [
        {"id": "acc_new", "label": "shared-1", "status": "active"},
        {"id": "acc_old", "label": "shared-1", "status": "active"},
        {"id": "acc_banned", "label": "shared-2", "status": "invalid"},
        {"id": "acc_ok", "label": "shared-3", "status": "cooling"},
    ]
    gone = [a["id"] for a in import_account.replaced(accounts, "acc_new", "shared-1")]
    assert gone == ["acc_old", "acc_banned"]
