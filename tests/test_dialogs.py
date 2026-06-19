from ui.dialogs import normalize_external_url


def test_normalize_external_url_adds_https_to_tidal_link():
    assert (
        normalize_external_url("link.tidal.com/EZHHR")
        == "https://link.tidal.com/EZHHR"
    )


def test_normalize_external_url_preserves_https():
    assert (
        normalize_external_url("https://link.tidal.com/EZHHR")
        == "https://link.tidal.com/EZHHR"
    )


def test_normalize_external_url_rejects_non_web_schemes():
    assert normalize_external_url("file:///tmp/login") == ""
