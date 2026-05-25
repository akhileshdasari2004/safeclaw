"""Configurable SSH mocks for integration tests."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SSHMockConfig:
    ssh_ready: bool = True
    connect_raises: Exception | None = None
    script_results: dict[str, str] = field(default_factory=dict)
    script_failures: set[str] = field(default_factory=set)
    health_ok: bool = True
    run_exit_code: int = 0


# Global config toggled per test via patch helper
_config = SSHMockConfig()


def set_ssh_config(**kwargs) -> SSHMockConfig:
    global _config
    _config = SSHMockConfig(**kwargs)
    return _config


def get_ssh_config() -> SSHMockConfig:
    return _config


class MockSSHClient:
    def __init__(self, host: str, username: str = "root", private_key_pem: str | None = None, password: str | None = None):
        self.host = host
        self.username = username

    def connect(self) -> None:
        if _config.connect_raises:
            raise _config.connect_raises

    def close(self) -> None:
        pass

    def run(self, command: str, timeout: int | None = None) -> tuple[int, str, str]:
        if not _config.health_ok and "curl" in command:
            return 1, "", "connection refused"
        return _config.run_exit_code, "active\n", ""

    def upload_and_run_script(self, script_name: str, env: dict[str, str] | None = None) -> str:
        if script_name in _config.script_failures:
            raise RuntimeError(f"Simulated failure running {script_name}")
        return _config.script_results.get(script_name, f"[mock] {script_name} completed successfully")


def mock_wait_for_ssh(host: str, port: int = 22, max_wait: int = 300, interval: int = 5) -> bool:
    return _config.ssh_ready
