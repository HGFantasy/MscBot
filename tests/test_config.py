def test_config_defaults_imports():
    # Ensure importing config helpers works without a config.ini present
    from data.config_settings import (
        get_eta_filter,
        get_headless,
        get_mission_delay,
        get_threads,
        get_transport_delay,
        get_transport_prefs,
    )

    ef = get_eta_filter()
    tp = get_transport_prefs()

    assert isinstance(get_threads(), int)
    assert isinstance(get_headless(), bool)
    assert isinstance(get_mission_delay(), int)
    assert isinstance(get_transport_delay(), int)

    for key in ("enable", "max_minutes", "max_km", "max_per_mission"):
        assert key in ef

    for key in (
        "max_hospital_km",
        "max_hospital_tax_pct",
        "max_prison_km",
        "max_prison_tax_pct",
    ):
        assert key in tp


def test_env_credentials_override(monkeypatch):
    monkeypatch.setenv("MISSIONCHIEF_USER", "u")
    monkeypatch.setenv("MISSIONCHIEF_PASS", "p")
    from data.config_settings import get_password, get_username

    assert get_username() == "u"
    assert get_password() == "p"
