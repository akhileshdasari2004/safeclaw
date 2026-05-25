"""SSH automation via Paramiko."""

from __future__ import annotations

import socket
import time
from pathlib import Path

import paramiko

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parents[4] / "infrastructure" / "scripts"


class SSHClient:
    def __init__(
        self,
        host: str,
        username: str = "root",
        private_key_pem: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host
        self.username = username
        self.private_key_pem = private_key_pem
        self.password = password
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        settings = get_settings()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs: dict = {
            "hostname": self.host,
            "username": self.username,
            "timeout": settings.ssh_connect_timeout,
            "allow_agent": False,
            "look_for_keys": False,
        }
        if self.private_key_pem:
            from io import StringIO

            key = paramiko.RSAKey.from_private_key(StringIO(self.private_key_pem))
            kwargs["pkey"] = key
        elif self.password:
            kwargs["password"] = self.password
        else:
            raise ValueError("SSH requires private key or password")

        client.connect(**kwargs)
        self._client = client
        logger.info("ssh_connected", host=self.host)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def run(self, command: str, timeout: int | None = None) -> tuple[int, str, str]:
        if not self._client:
            raise RuntimeError("SSH not connected")
        settings = get_settings()
        timeout = timeout or settings.ssh_command_timeout
        _, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return exit_code, out, err

    def upload_and_run_script(self, script_name: str, env: dict[str, str] | None = None) -> str:
        script_path = SCRIPTS_DIR / script_name
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        content = script_path.read_text()
        remote_path = f"/tmp/safeclaw-{script_name}"
        if not self._client:
            raise RuntimeError("SSH not connected")

        sftp = self._client.open_sftp()
        with sftp.file(remote_path, "w") as f:
            f.write(content)
        sftp.chmod(remote_path, 0o755)
        sftp.close()

        env_exports = ""
        if env:
            env_exports = " ".join(f'{k}="{v}"' for k, v in env.items()) + " "
        cmd = f"{env_exports}bash {remote_path}"
        code, out, err = self.run(cmd)
        log = f"$ {cmd}\n{out}\n{err}"
        if code != 0:
            raise RuntimeError(f"Script {script_name} failed (exit {code}): {err or out}")
        return log


def wait_for_ssh(
    host: str,
    port: int = 22,
    max_wait: int = 300,
    interval: int = 5,
) -> bool:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except OSError:
            time.sleep(interval)
    return False
