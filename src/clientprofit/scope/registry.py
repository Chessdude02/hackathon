"""Name -> request detector (config key scope.detector)."""
from clientprofit.scope.keyword import KeywordDetector
from clientprofit.scope.llm_detector import LLMDetector


def get_detector(name, cfg=None, **kwargs):
    if name == "keyword":
        return KeywordDetector()
    if name == "llm":
        llm = (cfg or {}).get("llm", {})
        return LLMDetector(llm.get("model", "Qwen/Qwen2.5-14B-Instruct"), llm.get("provider", "featherless"),
                           **kwargs)
    raise ValueError(f"Unknown scope.detector '{name}'. Known: keyword, llm")


def services_by_client(tables):
    """{client: services text} from the optional clients table (D-17)."""
    c = tables.get("clients")
    if c is None:
        return {}
    return {r.client: str(r.services_covered).strip() for r in c.itertuples()
            if isinstance(r.services_covered, str) and r.services_covered.strip()}
