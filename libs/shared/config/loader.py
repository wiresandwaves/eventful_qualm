from __future__ import annotations

import json
import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from apps.agent.settings import AgentSettings
from apps.coordinator.settings import CoordinatorSettings

# --- paths --------------------------------------------------------------------


def _repo_root() -> Path:
    """Heuristic: walk up from this file until we find pyproject.toml."""
    p = Path(__file__).resolve()
    for ancestor in [p, *p.parents]:
        if (ancestor / "pyproject.toml").exists():
            return ancestor
    return Path.cwd()


def _profiles_dir(env: Mapping[str, str]) -> Path:
    # Allow override (useful for tests): EVQ_CONFIG_DIR points *at* profiles/
    override = env.get("EVQ_CONFIG_DIR")
    if override:
        return Path(override)
    return _repo_root() / "configs" / "profiles"


def _load_profile_table(env: Mapping[str, str], profile: str) -> dict[str, Any]:
    f = _profiles_dir(env) / f"{profile}.toml"
    if not f.exists():
        return {}
    text = f.read_text("utf-8")
    try:
        return tomllib.loads(text)
    except Exception as e:
        raise RuntimeError(f"Failed to parse profile TOML: {f}") from e


# --- env overlay helpers ------------------------------------------------------


def _coerce_env_value(raw: str) -> Any:
    """
    Try to parse JSON first (so lists/dicts/numbers/bools work),
    then fall back to the original string.
    """
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _collect_env_for(
    fields: set[str], env: Mapping[str, str], prefix: str = "EVQ_"
) -> dict[str, Any]:
    """
    Collect overrides like EVQ_AGENT_ID, EVQ_HEARTBEAT_HZ -> {'agent_id': '...'}.
    Case-insensitive; underscores only.
    """
    out: dict[str, Any] = {}
    upper_to_field = {f.upper(): f for f in fields}
    plen = len(prefix)
    for k, v in env.items():
        if not k.startswith(prefix):
            continue
        key = k[plen:].upper()
        if key in upper_to_field:
            out[upper_to_field[key]] = _coerce_env_value(v)
    return out


# --- public API ---------------------------------------------------------------


def load_agent_settings(
    env: Mapping[str, str] | None = None, profile: str | None = None
) -> AgentSettings:
    """
    Merge defaults (AgentSettings) <- TOML [agent] <- env EVQ_*.
    Env examples: EVQ_AGENT_ID=vm2, EVQ_HEARTBEAT_HZ=10.0, EVQ_CMD_BIND=...
    """
    env = env or os.environ
    profile = (profile or env.get("EVQ_PROFILE") or "dev").strip()

    # start from defaults exposed by the model
    base = AgentSettings().model_dump()

    # TOML overlay
    toml_table = _load_profile_table(env, profile)
    toml_agent = toml_table.get("agent", {}) if isinstance(toml_table, dict) else {}
    if isinstance(toml_agent, dict):
        base.update(toml_agent)

    # env overlay
    env_over = _collect_env_for(set(base.keys()), env)
    base.update(env_over)

    # validate
    return AgentSettings.model_validate(base)


def load_coordinator_settings(
    env: Mapping[str, str] | None = None, profile: str | None = None
) -> CoordinatorSettings:
    """
    Merge defaults (CoordinatorSettings) <- TOML [coordinator] <- env EVQ_*.
    Env examples: EVQ_REFRESH_HZ=5, EVQ_AGENTS_CMD={"vm1":"tcp://..."},
    EVQ_TELEM_SUBS=["tcp://...","tcp://..."]
    """
    env = env or os.environ
    profile = (profile or env.get("EVQ_PROFILE") or "dev").strip()

    base = CoordinatorSettings().model_dump()

    toml_table = _load_profile_table(env, profile)
    toml_coord = toml_table.get("coordinator", {}) if isinstance(toml_table, dict) else {}
    if isinstance(toml_coord, dict):
        base.update(toml_coord)

    env_over = _collect_env_for(set(base.keys()), env)
    base.update(env_over)

    return CoordinatorSettings.model_validate(base)
