import importlib
import json

import pytest


def test_issue_number_starts_from_configured_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ISSUE_START_NUMBER", "1")

    import config
    import src.analyzer.digest as digest

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    importlib.reload(digest)

    assert digest.get_next_issue_number() == 1
    assert json.loads((tmp_path / "issue_counter.json").read_text())["issue_number"] == 1


def test_call_ai_uses_reasoning_content_when_content_is_empty(monkeypatch):
    import src.analyzer.digest as digest

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "reasoning_content": '{"summary":"ok","items":[{"title":"t"}]}',
                        }
                    }
                ]
            }

    monkeypatch.setattr(digest.requests, "post", lambda *args, **kwargs: FakeResponse())
    analyzer = digest.DigestAnalyzer(mode="quick_json")

    assert analyzer.call_ai("prompt") == '{"summary":"ok","items":[{"title":"t"}]}'


def test_run_json_does_not_save_or_increment_when_ai_items_empty(monkeypatch, tmp_path):
    import config
    import src.analyzer.digest as digest

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "WEB_JSON_DIR", tmp_path / "web-json")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    config.WEB_JSON_DIR.mkdir(parents=True)
    config.REPORTS_DIR.mkdir(parents=True)
    monkeypatch.setattr(digest, "ISSUE_COUNTER_FILE", tmp_path / "issue_counter.json")

    class FakeAggregator:
        def gather(self, date=None):
            return (
                [
                    {
                        "id": "1",
                        "source": "rss",
                        "source_name": "RSS",
                        "author": "Author",
                        "title": "AI news",
                        "summary": "Important AI news",
                        "content": "Important AI news",
                        "url": "https://example.com/news",
                        "published_at": "2026-04-12T00:00:00+0000",
                        "score": 10,
                    }
                ],
                tmp_path / "aggregated.jsonl",
            )

    analyzer = digest.DigestAnalyzer(mode="quick_json")
    analyzer.aggregator = FakeAggregator()
    monkeypatch.setattr(analyzer, "call_ai", lambda prompt: '{"summary":"empty","total":0,"items":[]}')
    monkeypatch.setattr(analyzer, "_load_recent_source_urls", lambda hours=48: set())
    monkeypatch.setattr(analyzer, "_load_recent_titles", lambda hours=48: [])

    with pytest.raises(ValueError, match="AI 未生成有效快讯"):
        analyzer.run_json()

    assert not (tmp_path / "issue_counter.json").exists()
    assert list((tmp_path / "web-json").glob("*.json")) == []
