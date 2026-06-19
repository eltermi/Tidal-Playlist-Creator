from pathlib import Path

from services.tidal_client import TidalClient


def test_new_client_is_not_authenticated_without_network(tmp_path: Path):
    client = TidalClient(tmp_path / "missing-session.json")

    assert client.is_authenticated is False
    assert client.has_saved_session is False
    assert client.restore_session() is False


def test_authentication_state_is_cached(tmp_path: Path):
    client = TidalClient(tmp_path / "missing-session.json")

    def fail_if_called():
        raise AssertionError("check_login must not be called by the UI state property")

    client.session.check_login = fail_if_called
    assert client.is_authenticated is False
