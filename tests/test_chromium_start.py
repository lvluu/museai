import asyncio

import pytest

from museai.drivers.browser.chromium import ChromiumProcess


def test_a_chromium_that_dies_at_start_names_its_own_error_and_the_sandbox_fix(tmp_path):
    fake = tmp_path / "chrome"
    fake.write_text("#!/bin/sh\necho 'FATAL: No usable sandbox! see apparmor docs' >&2\nexit 1\n")
    fake.chmod(0o755)
    proc = ChromiumProcess(str(fake), port=1, profile_dir=tmp_path / "profile")
    with pytest.raises(RuntimeError) as e:
        asyncio.run(proc.start())
    msg = str(e.value)
    assert "No usable sandbox" in msg and "AppArmor" in msg, msg
