"""Runtime settings validate before widgets/provider calls and redact credentials."""

import json

import pytest

from src.settings import ConfigurationError, load_settings


def test_defaults_allow_preview_and_resolve_cache_from_project_root(tmp_path):
    settings = load_settings({}, root=tmp_path)
    assert not settings.ai_configured and not settings.adzuna_configured
    assert not settings.development_mode and settings.refresh_sources
    assert settings.embedding_dimensions == 768
    assert settings.cache_root == tmp_path / ".cache"
    assert not settings.cache_root.exists()  # Parsing does not write directories.


@pytest.mark.parametrize("value,expected", [("true", True), (" TRUE ", True), ("1", True),
    ("false", False), ("False", False), ("0", False)])
@pytest.mark.parametrize("field,attribute", [("ECE_DEVELOPMENT_MODE", "development_mode"), ("ECE_REFRESH_SOURCES", "refresh_sources")])
def test_environment_flags_are_parsed_explicitly(tmp_path, value, expected, field, attribute):
    assert getattr(load_settings({field: value}, root=tmp_path), attribute) is expected


@pytest.mark.parametrize("field", ["ECE_DEVELOPMENT_MODE", "ECE_REFRESH_SOURCES"])
@pytest.mark.parametrize("value", ["yes", "off", "", "invalid-private-value"])
def test_invalid_flags_report_the_variable_without_echoing_its_value(tmp_path, field, value):
    with pytest.raises(ConfigurationError) as exc:
        load_settings({field: value}, root=tmp_path)
    assert field in str(exc.value)
    assert "invalid-private-value" not in str(exc.value)


@pytest.mark.parametrize("dimension", [1, 768, 1536, 3072])
def test_supported_local_dimension_range(tmp_path, dimension):
    assert load_settings({"EMBEDDING_DIMENSION": str(dimension)}, root=tmp_path).embedding_dimensions == dimension


@pytest.mark.parametrize("dimension", ["0", "3073", "768.5", "NaN", "-1", "true", "", "8" * 100])
def test_invalid_dimensions_fail_before_provider_initialization(tmp_path, dimension):
    with pytest.raises(ConfigurationError, match="EMBEDDING_DIMENSION"):
        load_settings({"EMBEDDING_DIMENSION": dimension}, root=tmp_path)


@pytest.mark.parametrize("field", ["EMBEDDING_MODEL", "GENERATION_MODEL"])
@pytest.mark.parametrize("value", ["private-model-value-never-echo", "https://invalid.example/?secret=private", "gemini invalid", ""])
def test_invalid_model_ids_have_sanitized_errors(tmp_path, field, value):
    with pytest.raises(ConfigurationError) as exc:
        load_settings({field: value}, root=tmp_path)
    assert field in str(exc.value)
    if value:
        assert value not in str(exc.value)


def test_compatible_model_paths_and_key_alias_precedence(tmp_path):
    settings = load_settings({"GEMINI_API_KEY": "fixture-primary", "GOOGLE_API_KEY": "fixture-alias",
        "EMBEDDING_MODEL": "models/gemini-embedding-2"}, root=tmp_path)
    assert settings.gemini_key.get_secret_value() == "fixture-primary"
    assert settings.embedding_model == "models/gemini-embedding-2"
    assert load_settings({"GOOGLE_API_KEY": "fixture-alias"}, root=tmp_path).ai_configured


def test_credentials_are_excluded_from_repr_exports_and_public_summary(tmp_path):
    values = {"GEMINI_API_KEY": "fixture-sensitive-key", "ADZUNA_APP_ID": "fixture-sensitive-id",
              "ADZUNA_APP_KEY": "fixture-sensitive-job-key"}
    settings = load_settings(values, root=tmp_path)
    assert settings.ai_configured and settings.adzuna_configured
    outputs = [repr(settings), settings.model_dump_json(), json.dumps(settings.public_summary())]
    assert not any(secret in output for secret in values.values() for output in outputs)


def test_partial_adzuna_configuration_keeps_the_optional_adapter_disabled(tmp_path):
    assert not load_settings({"ADZUNA_APP_ID": "fixture-id"}, root=tmp_path).adzuna_configured


def test_cache_location_is_independent_of_working_directory(tmp_path, monkeypatch):
    project = tmp_path / "project"
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    assert load_settings({"ECE_CACHE_DIR": "runtime-cache"}, root=project).cache_root == project / "runtime-cache"
    assert load_settings({"ECE_CACHE_DIR": str(other)}, root=project).cache_root == other


@pytest.mark.parametrize("value", ["private-path\x00", "x" * 1025])
def test_invalid_cache_paths_do_not_leak_in_errors(tmp_path, value):
    with pytest.raises(ConfigurationError) as exc:
        load_settings({"ECE_CACHE_DIR": value}, root=tmp_path)
    assert "ECE_CACHE_DIR" in str(exc.value) and value not in str(exc.value)


def test_invalid_credential_reports_only_its_environment_name(tmp_path):
    with pytest.raises(ConfigurationError) as exc:
        load_settings({"GEMINI_API_KEY": "private\ncredential"}, root=tmp_path)
    assert "GEMINI_API_KEY" in str(exc.value) and "private" not in str(exc.value)
