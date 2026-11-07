"""Validated runtime configuration; credentials never enter public summaries."""

from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import ConfigDict, Field, SecretStr, ValidationError

from .catalog import ROOT
from .models import StrictModel

ModelID = r"^(?:models/)?gemini-[a-z0-9][a-z0-9._-]{0,100}$"


class ConfigurationError(ValueError):
    pass


class RuntimeSettings(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    development_mode: bool = False
    refresh_sources: bool = True
    embedding_model: str = Field(default="gemini-embedding-2", pattern=ModelID)
    generation_model: str = Field(default="gemini-3.5-flash-lite", pattern=ModelID)
    embedding_dimensions: int = Field(default=768, ge=1, le=3072, strict=True)
    ai_time_budget_seconds: int = Field(default=45, ge=5, le=120, strict=True)
    cache_root: Path
    gemini_key: SecretStr = Field(default_factory=lambda: SecretStr(""), exclude=True, repr=False)
    adzuna_app_id: SecretStr = Field(default_factory=lambda: SecretStr(""), exclude=True, repr=False)
    adzuna_app_key: SecretStr = Field(default_factory=lambda: SecretStr(""), exclude=True, repr=False)

    @property
    def ai_configured(self):
        return bool(self.gemini_key.get_secret_value())

    @property
    def adzuna_configured(self):
        return bool(self.adzuna_app_id.get_secret_value() and self.adzuna_app_key.get_secret_value())

    def public_summary(self):
        return {"development_mode": self.development_mode, "refresh_sources": self.refresh_sources,
            "embedding_model": self.embedding_model, "generation_model": self.generation_model,
            "embedding_dimensions": self.embedding_dimensions, "ai_key_present": self.ai_configured,
            "ai_time_budget_seconds": self.ai_time_budget_seconds,
            "adzuna_credentials_present": self.adzuna_configured}


def load_settings(environ=None, *, root=ROOT):
    env = os.environ if environ is None else environ

    def flag(name, default):
        value = env.get(name)
        if value is None:
            return default
        value = value.strip().lower()
        if value not in {"true", "false", "1", "0"}:
            raise ConfigurationError(name + " must be true, false, 1, or 0.")
        return value in {"true", "1"}

    def credential(name):
        value = env.get(name, "").strip()
        if len(value) > 4096 or any(c.isspace() or ord(c) < 32 for c in value):
            raise ConfigurationError(name + " must be a single credential without whitespace.")
        return value

    raw_dimension = env.get("EMBEDDING_DIMENSION", "768").strip()
    if not re.fullmatch(r"[0-9]{1,4}", raw_dimension):
        raise ConfigurationError("EMBEDDING_DIMENSION must be an integer from 1 to 3072.")
    raw_budget = env.get("AI_TIME_BUDGET_SECONDS", "45").strip()
    if not re.fullmatch(r"[0-9]{1,3}", raw_budget) or not 5 <= int(raw_budget) <= 120:
        raise ConfigurationError("AI_TIME_BUDGET_SECONDS must be an integer from 5 to 120.")
    raw_cache = env.get("ECE_CACHE_DIR", "").strip()
    if len(raw_cache) > 1024 or any(ord(c) < 32 for c in raw_cache):
        raise ConfigurationError("ECE_CACHE_DIR must be a valid directory path.")
    try:
        cache = Path(raw_cache).expanduser() if raw_cache else Path(root) / ".cache"
        cache = (cache if cache.is_absolute() else Path(root) / cache).resolve()
    except (OSError, ValueError, RuntimeError):
        raise ConfigurationError("ECE_CACHE_DIR must be a valid directory path.") from None
    try:
        return RuntimeSettings(development_mode=flag("ECE_DEVELOPMENT_MODE", False),
            refresh_sources=flag("ECE_REFRESH_SOURCES", True),
            embedding_model=env.get("EMBEDDING_MODEL", "gemini-embedding-2").strip(),
            generation_model=env.get("GENERATION_MODEL", "gemini-3.5-flash-lite").strip(),
            embedding_dimensions=int(raw_dimension), ai_time_budget_seconds=int(raw_budget), cache_root=cache,
            gemini_key=credential("GEMINI_API_KEY") or credential("GOOGLE_API_KEY"),
            adzuna_app_id=credential("ADZUNA_APP_ID"), adzuna_app_key=credential("ADZUNA_APP_KEY"))
    except ValidationError as exc:
        names = {"embedding_dimensions": "EMBEDDING_DIMENSION", "embedding_model": "EMBEDDING_MODEL",
                 "generation_model": "GENERATION_MODEL"}
        fields = sorted({names.get(error["loc"][0], "runtime settings") for error in exc.errors(include_input=False)})
        raise ConfigurationError("Check application configuration: " + ", ".join(fields) + ".") from None
