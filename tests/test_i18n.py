from series_collector.i18n import TRANSLATIONS, translate


def test_languages_have_the_same_translation_keys() -> None:
    assert set(TRANSLATIONS["de"]) == set(TRANSLATIONS["en"])


def test_translation_formats_values() -> None:
    assert translate("de", "source_missing", path="/tmp/source").endswith("/tmp/source")
    assert translate("en", "new") == "New"
