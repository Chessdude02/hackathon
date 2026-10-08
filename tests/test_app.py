"""The Streamlit screen, driven headless: demo data to ranked list."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from generator.generate import generate

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(scope="module")
def demo_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("demo")
    generate(11, 50, base / "data", base / "truth")
    return base / "data"


def test_demo_data_to_ranked_list(demo_dir, monkeypatch):
    monkeypatch.setenv("CLIENTPROFIT_DEMO_DIR", str(demo_dir))
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.radio[0].set_value("Use demo data (generated)").run()
    assert not at.exception
    assert [h.value for h in at.header][:3] == ["1. Check the column mapping", "2. Settings",
                                               "3. Problems in the files"]
    rank = [b for b in at.button if b.label == "Rank clients"][0]
    rank.click().run()
    assert not at.exception
    assert "4. Ranked clients" in [h.value for h in at.header]
    ranked = [d.value for d in at.dataframe if "Rank" in d.value.columns]
    assert len(ranked) == 1 and len(ranked[0]) >= 40
    assert list(ranked[0].columns)[:2] == ["Rank", "Client"]


def test_ranked_list_has_actions_and_asks_before_long_labelling(demo_dir, monkeypatch):
    monkeypatch.setenv("CLIENTPROFIT_DEMO_DIR", str(demo_dir))
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.radio[0].set_value("Use demo data (generated)").run()
    [b for b in at.button if b.label == "Rank clients"][0].click().run()
    assert not at.exception
    ranked = [d.value for d in at.dataframe if "Rank" in d.value.columns][0]
    assert {"Suggested action", "Effect per year", "Profit (last 3 mo)", "Heading to a loss"} <= set(ranked.columns)
    rows = [d.value for d in at.dataframe if "Row" in d.value.columns]
    assert rows and all("_src_row" not in d.columns for d in rows)
    dates = rows[0].iloc[:, 2].astype(str)
    assert not dates.str.contains("00:00:00").any()
    # Fresh data: about 2,600 unsaved messages, above the public limit, so no AI calls at all (D-35)
    assert not any(b.label == "Label them now" for b in at.button)
    assert any("labels at most 500 new messages" in w.value for w in at.warning)
    assert any("Suggested action" in m.value for m in at.markdown)


def test_missing_demo_data_is_built_on_first_start(tmp_path, monkeypatch):
    """D-28: a fresh deploy has no data/ folder; choosing the demo builds it (seed 42) instead of failing."""
    folder = tmp_path / "generated"
    monkeypatch.setenv("CLIENTPROFIT_DEMO_DIR", str(folder))
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert any("Demo only" in c.value for c in at.caption)
    at.radio[0].set_value("Use demo data (generated)").run()
    assert not at.exception
    assert (folder / "invoices.csv").exists() and (folder / "requests.csv").exists()
    assert "1. Check the column mapping" in [h.value for h in at.header]


def test_result_from_older_app_version_is_dropped(demo_dir, monkeypatch):
    """A tab kept open across an update holds a result made by the old code; it must not crash."""
    monkeypatch.setenv("CLIENTPROFIT_DEMO_DIR", str(demo_dir))
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.radio[0].set_value("Use demo data (generated)").run()
    [b for b in at.button if b.label == "Rank clients"][0].click().run()
    old = at.session_state["result"]
    old["client_month"] = old["client_month"].drop(columns=["direct_cost"])  # shape before D-31
    at.session_state["result_version"] = 1
    at.run()
    assert not at.exception
    assert any("updated since you last ranked" in i.value for i in at.info)


def test_client_detail_shows_margin_trend_and_forecast(demo_dir, monkeypatch):
    """D-34: the forecast is on the screen, with its typical error measured on the loaded data."""
    monkeypatch.setenv("CLIENTPROFIT_DEMO_DIR", str(demo_dir))
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.radio[0].set_value("Use demo data (generated)").run()
    [b for b in at.button if b.label == "Rank clients"][0].click().run()
    assert not at.exception
    assert any("Margin trend and next quarter" in m.value for m in at.markdown)
    assert any("Next quarter, if nothing changes" in c.value and "off by" in c.value for c in at.caption)
