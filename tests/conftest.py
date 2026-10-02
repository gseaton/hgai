"""Shared test fixtures."""

import os
import shutil
import socket
import subprocess
import time

import pytest

# Hermetic settings: a developer's own .env (tenancy on, telemetry on, an API key...) must not
# change what the suite tests. Environment variables outrank .env, so pin the switches the
# tests assume, before anything reads the cached settings.
for _name, _value in (
    ("HGAI_MULTITENANCY_ENABLED", "false"),
    ("HGAI_TELEMETRY_ENABLED", "false"),
    ("HGAI_PRIMARY_API_KEY", ""),
    ("HGAI_SECONDARY_API_KEY", ""),
):
    os.environ[_name] = _value

from hgai.config import get_settings  # noqa: E402

get_settings.cache_clear()


# One mongod for the whole test session: a server per module left gigabytes of journal
# files in /tmp and slowed the suite once the tenancy tests multiplied the modules.
@pytest.fixture(scope="session")
def mongod(tmp_path_factory):
    exe = shutil.which("mongod")
    if not exe:
        pytest.skip("mongod not installed")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [exe, "--dbpath", str(tmp_path_factory.mktemp("mongo")), "--port", str(port),
         "--bind_ip", "127.0.0.1", "--nounixsocket"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.skip("mongod did not start")
        yield f"mongodb://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=15)
