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
