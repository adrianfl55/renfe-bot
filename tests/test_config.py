from unittest.mock import patch
import pytest
from config import get_bot_token


def test_get_bot_token_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "123456789:ABC_TEST_TOKEN")
    assert get_bot_token() == "123456789:ABC_TEST_TOKEN"


def test_get_bot_token_missing_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_SECRET_TOKEN", raising=False)
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(RuntimeError) as exc_info:
            get_bot_token()
        assert "No se encontró el TELEGRAM_TOKEN" in str(exc_info.value)
