"""Shared test fixtures."""

import shutil
import socket
import subprocess
import time

import pytest


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
