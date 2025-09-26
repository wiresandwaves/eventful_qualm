from __future__ import annotations

from pathlib import Path

from shared.config.loader import load_agent_settings, load_coordinator_settings


def test_defaults_when_no_profile_file(tmp_path: Path, monkeypatch):
    # Point to an empty profiles dir and a non-existent profile
    profiles = tmp_path / "profiles"
    profiles.mkdir(parents=True)
    monkeypatch.setenv("EVQ_CONFIG_DIR", str(profiles))
    monkeypatch.setenv("EVQ_PROFILE", "does_not_exist")

    a = load_agent_settings()
    c = load_coordinator_settings()

    assert a.agent_id == "vm1" and a.heartbeat_hz == 5.0
    assert c.refresh_hz == 5.0 and "vm1" in c.agents_cmd


def test_toml_overrides_defaults(tmp_path: Path, monkeypatch):
    profiles = tmp_path / "profiles"
    profiles.mkdir(parents=True)
    monkeypatch.setenv("EVQ_CONFIG_DIR", str(profiles))
    monkeypatch.setenv("EVQ_PROFILE", "myprof")

    # Write a profile file
    (profiles / "myprof.toml").write_text(
        """
        [agent]
        agent_id = "from_toml"
        heartbeat_hz = 7.5

        [coordinator]
        refresh_hz = 3.0
        """,
        encoding="utf-8",
    )

    a = load_agent_settings()
    c = load_coordinator_settings()

    assert a.agent_id == "from_toml" and a.heartbeat_hz == 7.5
    assert c.refresh_hz == 3.0


def test_env_overrides_toml(monkeypatch, tmp_path: Path):
    profiles = tmp_path / "profiles"
    profiles.mkdir(parents=True)
    monkeypatch.setenv("EVQ_CONFIG_DIR", str(profiles))
    monkeypatch.setenv("EVQ_PROFILE", "p1")

    (profiles / "p1.toml").write_text(
        """
        [agent]
        agent_id = "from_toml"
        heartbeat_hz = 5.0
        """,
        encoding="utf-8",
    )

    # Env should win
    monkeypatch.setenv("EVQ_AGENT_ID", "from_env")
    monkeypatch.setenv("EVQ_HEARTBEAT_HZ", "9.25")

    a = load_agent_settings()
    assert a.agent_id == "from_env"
    assert abs(a.heartbeat_hz - 9.25) < 1e-6
