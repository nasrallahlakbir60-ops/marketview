from app.config import Settings


def test_cors_origins_accepts_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://marketview.example")

    assert Settings().cors_origins == ["http://localhost:5173", "https://marketview.example"]


def test_api_keys_are_stripped(monkeypatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "  abc  ")

    assert Settings().fred_api_key == "abc"
