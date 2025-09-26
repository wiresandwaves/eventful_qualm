from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from shared.config.loader import (
    load_agent_settings,
    load_coordinator_settings,
)


def _write_profile(dirpath: Path, name: str, text: str) -> Path:
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / f"{name}.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_agent_defaults_when_no_profile_and_no_env():
    # No profile file; empty env → fall back to model defaults
    s = load_agent_settings(env={}, profile="dev")
    assert s.agent_id == "vm1"  # default from your settings stub
    assert s.heartbeat_hz == 5.0
    assert s.ipc_impl == "zmq"  # default set earlier
    assert isinstance(s.cmd_bind, str)
    assert isinstance(s.telem_bind, str)


def test_agent_toml_overlay(tmp_path: Path):
    profiles = tmp_path / "profiles"
    _write_profile(
        profiles,
        "dev",
        """
        [agent]
        agent_id = "vmX"
        heartbeat_hz = 7.5
        ipc_impl = "zmq"
        cmd_bind = "tcp://127.0.0.1:9991"
        telem_bind = "tcp://127.0.0.1:9992"
        """,
    )

    env = {
        "EVQ_CONFIG_DIR": str(profiles),
        "EVQ_PROFILE": "dev",
    }
    s = load_agent_settings(env=env)
    assert s.agent_id == "vmX"
    assert s.heartbeat_hz == 7.5
    assert s.ipc_impl == "zmq"
    assert s.cmd_bind.endswith(":9991")
    assert s.telem_bind.endswith(":9992")


def test_agent_env_overrides_toml(tmp_path: Path):
    profiles = tmp_path / "profiles"
    _write_profile(
        profiles,
        "dev",
        """
        [agent]
        agent_id = "from_toml"
        heartbeat_hz = 1.0
        ipc_impl = "inproc"
        """,
    )

    env = {
        "EVQ_CONFIG_DIR": str(profiles),
        "EVQ_PROFILE": "dev",
        # Flat EVQ_* keys override TOML
        "EVQ_AGENT_ID": "from_env",
        "EVQ_HEARTBEAT_HZ": "9.0",  # string parses to float
        "EVQ_IPC_IMPL": "zmq",
    }
    s = load_agent_settings(env=env)
    assert s.agent_id == "from_env"
    assert s.heartbeat_hz == 9.0
    assert s.ipc_impl == "zmq"


def test_coordinator_defaults_no_profile_no_env():
    s = load_coordinator_settings(env={}, profile="dev")
    assert s.refresh_hz == 5.0
    assert s.ipc_impl == "zmq"
    assert isinstance(s.agents_cmd, dict)
    assert isinstance(s.telem_subs, list)


def test_coordinator_toml_overlay_and_env_json(tmp_path: Path):
    profiles = tmp_path / "profiles"
    _write_profile(
        profiles,
        "dev",
        """
        [coordinator]
        refresh_hz = 2.0
        ipc_impl = "zmq"
        agents_cmd = { vm1 = "tcp://127.0.0.1:7788" }
        telem_subs = ["tcp://127.0.0.1:7789"]
        """,
    )

    # Env provides JSON strings for complex types; loader should json.loads them.
    env: dict[str, Any] = {
        "EVQ_CONFIG_DIR": str(profiles),
        "EVQ_PROFILE": "dev",
        # Case-insensitive (post-prefix) per _collect_env_for:
        "EVQ_agents_cmd": '{"vmA":"tcp://127.0.0.1:9901","vmB":"tcp://127.0.0.1:9902"}',
        "EVQ_TELEM_SUBS": '["tcp://127.0.0.1:9910","tcp://127.0.0.1:9911"]',
        "EVQ_REFRESH_HZ": "3",  # numeric string → int
    }

    s = load_coordinator_settings(env=env)
    # Env should override TOML
    assert s.refresh_hz == 3
    assert s.agents_cmd == {
        "vmA": "tcp://127.0.0.1:9901",
        "vmB": "tcp://127.0.0.1:9902",
    }
    assert s.telem_subs == [
        "tcp://127.0.0.1:9910",
        "tcp://127.0.0.1:9911",
    ]


def test_profile_dir_override_via_env(tmp_path: Path):
    # Put a profile file in a non-standard location and point EVQ_CONFIG_DIR to it.
    profiles = tmp_path / "custom_profiles"
    _write_profile(
        profiles,
        "myprof",
        """
        [agent]
        agent_id = "custom"
        """,
    )

    env = {
        "EVQ_CONFIG_DIR": str(profiles),
        "EVQ_PROFILE": "myprof",
    }
    s = load_agent_settings(env=env)
    assert s.agent_id == "custom"


def test_bad_toml_raises_runtime_error(tmp_path: Path):
    profiles = tmp_path / "profiles"
    # Intentionally broken TOML
    (profiles / "dev.toml").parent.mkdir(parents=True, exist_ok=True)
    (profiles / "dev.toml").write_text("[agent]\nthis = not_valid\n", encoding="utf-8")

    env = {"EVQ_CONFIG_DIR": str(profiles), "EVQ_PROFILE": "dev"}

    with pytest.raises(RuntimeError):
        _ = load_agent_settings(env=env)
