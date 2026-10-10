"""The story-first screen (app_story.py), driven headless on generated demo data. No AI calls."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from generator.generate import generate

APP = str(Path(__file__).resolve().parent.parent / "app_story.py")
SYMBOLS = set("—–−×→←…✅💲✂️🛑⚠ℹ⏱💬•★✨")


@pytest.fixture(autouse=True)
def no_real_ai_calls(monkeypatch):
    from clientprofit import explain, llm
    from clientprofit.scope import llm_detector

    def offline(*args, **kwargs):
        raise llm.LLMError("AI calls are switched off in tests")
    for module in (llm, explain, llm_detector):
        if hasattr(module, "complete"):
            monkeypatch.setattr(module, "complete", offline)


@pytest.fixture(scope="module")
def demo_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("demo")
    generate(11, 50, base / "data", base / "truth")
    return base / "data"


@pytest.fixture
def story(demo_dir, monkeypatch):
    monkeypatch.setenv("CLIENTPROFIT_DEMO_DIR", str(demo_dir))
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()          # demo data is the default and ranks itself
    return at


def test_demo_tells_the_story_without_a_click(story):
    assert not story.exception
    headers = [h.value for h in story.header]
    assert headers[:4] == ["1. What we found", "2. Revenue is not profit", "3. What to do",
                           "4. Why: one client, down to the source rows"]
    labels = [m.label for m in story.metric]
    assert labels == ["Clients losing money (12 mo)", "What they cost you (12 mo)",
                      "Clients that need a decision", "Profit from all ranked clients (12 mo)"]


def test_headline_numbers_match_the_ranking(story):
    from clientprofit import config, pipeline, validate
    import os
    cfg = config.load_config()
    folder = os.environ["CLIENTPROFIT_DEMO_DIR"]
    cfg["staff_costs"] = config.read_staff_costs(Path(folder) / "staff_costs.csv")
    tables = pipeline.apply_mappings(pipeline.load_files(pipeline.find_files(folder)))
    r = pipeline.run_pipeline(tables, cfg, pipeline.suggested_exclusions(validate.validate_inputs(tables, cfg)))
    losing = r["ranked"][r["ranked"]["profit_last_12m"] < 0]
    shown = {m.label: m.value for m in story.metric}
    assert shown["Clients losing money (12 mo)"] == f"{len(losing)} of {len(r['ranked'])}"
    assert shown["What they cost you (12 mo)"] == f"${-losing['profit_last_12m'].sum():,.0f}"


def test_decision_table_and_client_detail(story):
    need = [d.value for d in story.dataframe if "Effect per year" in d.value.columns
            and "Rank" not in d.value.columns][0]
    assert len(need) > 0 and "keep as is" not in set(need["Suggested action"])
    assert list(need["Profit (12 mo)"]) == sorted(need["Profit (12 mo)"])          # worst first
    detail = [s for s in story.selectbox if s.label == "Client detail"][0]
    assert detail.value == need["Client"].iloc[0]                                   # opens on the worst
    assert any("Margin trend and the effect of the suggested action" in m.value for m in story.markdown)


def test_rank_again_with_new_settings(story):
    target = [n for n in story.number_input if n.label == "Target margin"][0]
    target.set_value(0.1).run()
    [b for b in story.button if b.label == "Rank again with these settings"][0].click().run()
    assert not story.exception
    assert any("10% target" in c.value for c in story.caption)


def test_story_screen_has_no_underscores_or_symbols(story):
    at = story
    texts = [e.value for kind in ("title", "header", "subheader", "markdown", "caption", "info", "warning", "error")
             for e in getattr(at, kind)]
    texts += [e.label for e in list(at.selectbox) + list(at.button) + list(at.checkbox) + list(at.radio)
              + list(at.number_input) + list(at.expander) + list(at.metric)]
    texts += [str(m.value) for m in at.metric]
    texts += [str(o) for sb in at.selectbox for o in sb.options]
    for df in at.dataframe:
        texts += [str(c) for c in df.value.columns]
        texts += [str(v) for col in df.value.columns if df.value[col].dtype == object for v in df.value[col]]
    bad = [t for t in texts if "_" in t or SYMBOLS & set(t)]
    assert not bad, bad[:5]
