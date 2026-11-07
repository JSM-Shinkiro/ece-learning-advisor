"""Validated server bindings and a shell-free shared-host launch command."""

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
import re
import runpy
import sys

from .catalog import ROOT
from .settings import ConfigurationError


@dataclass(frozen=True)
class ServerOptions:
    address: str
    port: int
    base_path: str

    def public_summary(self):
        return {"address": self.address, "port": self.port, "base_path": self.base_path,
                "health_path": "/" + (self.base_path + "/" if self.base_path else "") + "_stcore/health"}

    def environment(self, environ):
        env = dict(environ)
        env.update(PORT=str(self.port), STREAMLIT_SERVER_PORT=str(self.port),
                   STREAMLIT_SERVER_ADDRESS=self.address, STREAMLIT_SERVER_BASE_URL_PATH=self.base_path)
        return env

    def command(self, *, root=ROOT, executable=None):
        return [executable or sys.executable, "-m", "streamlit", "run", str(Path(root).resolve() / "app.py"),
                "--server.address=" + self.address, "--server.port=" + str(self.port),
                "--server.baseUrlPath=" + self.base_path, "--server.headless=true",
                "--server.fileWatcherType=none", "--browser.gatherUsageStats=false"]


def load_server_options(environ=None, *, address=None, port=None, base_path=None):
    """Explicit CLI values win; PORT precedes Streamlit's port environment value."""
    env = os.environ if environ is None else environ
    raw_port = port if port is not None else env.get("PORT", env.get("STREAMLIT_SERVER_PORT", "8501"))
    if (type(raw_port) not in {str, int} or not re.fullmatch(r"[0-9]{1,5}", str(raw_port).strip())
            or not 1 <= int(str(raw_port).strip()) <= 65535):
        raise ConfigurationError("Check --port, PORT, or STREAMLIT_SERVER_PORT: use an integer from 1 to 65535.")
    raw_address = address if address is not None else env.get("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    if not isinstance(raw_address, str) or len(raw_address) > 64:
        raise ConfigurationError("Check --address or STREAMLIT_SERVER_ADDRESS: use an IP address or localhost.")
    normalized_address = raw_address.strip().lower()
    if normalized_address != "localhost":
        try:
            if "%" in normalized_address:
                raise ValueError()
            normalized_address = str(ipaddress.ip_address(normalized_address))
        except ValueError:
            raise ConfigurationError("Check --address or STREAMLIT_SERVER_ADDRESS: use an IP address or localhost.") from None
    raw_path = base_path if base_path is not None else env.get("STREAMLIT_SERVER_BASE_URL_PATH", "")
    if not isinstance(raw_path, str) or len(raw_path) > 200:
        raise ConfigurationError("Check --base-path or STREAMLIT_SERVER_BASE_URL_PATH: use a simple URL path.")
    normalized_path = raw_path.strip().strip("/")
    if (raw_path.strip().startswith("//") or raw_path.strip().endswith("//")
            or normalized_path and not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", normalized_path)):
        raise ConfigurationError("Check --base-path or STREAMLIT_SERVER_BASE_URL_PATH: use a simple URL path.")
    return ServerOptions(address=normalized_address, port=int(str(raw_port).strip()), base_path=normalized_path)


def launch_server(options, environ, *, root=ROOT, platform=None):
    """Start one server; Windows must stay in the process a host can monitor."""
    command = options.command(root=root)
    if (sys.platform if platform is None else platform) != "win32":
        os.execve(sys.executable, command, environ)
        return
    # Windows exec uses CreateProcess rather than POSIX process replacement.
    # Enter the same public -m entrypoint in this startup process instead.
    previous_argv, previous_environment = sys.argv, os.environ.copy()
    try:
        os.environ.clear()
        os.environ.update(environ)
        sys.argv = ["streamlit", *command[3:]]
        runpy.run_module("streamlit", run_name="__main__", alter_sys=True)
    finally:
        sys.argv = previous_argv
        os.environ.clear()
        os.environ.update(previous_environment)
