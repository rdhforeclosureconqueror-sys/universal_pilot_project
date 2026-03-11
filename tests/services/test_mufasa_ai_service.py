from uuid import uuid4

from app.services.ai_orchestration_service import handle_mufasa_prompt


class _Query:
    def __init__(self, value=None):
        self.value = value

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.value


class _DB:
    def __init__(self):
        self.added = []
        self.committed = False

    def query(self, _model):
        return _Query(None)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True


def test_handle_mufasa_prompt_runs_system_diagnostics(monkeypatch):
    db = _DB()
    user_id = uuid4()

    result = handle_mufasa_prompt("verify platform and run diagnostics", user_id=user_id, db=db)

    assert "verify_platform" in result["actions_executed"]
    assert "diagnostics" in result["response"].lower() or "system" in result["response"].lower()
    assert db.committed is True
    assert db.added, "Expected AI command log to be persisted"


def test_handle_mufasa_prompt_ingest_leads(monkeypatch):
    db = _DB()
    user_id = uuid4()

    def _fake_ingest(_db, *, source_name, source_type, leads):
        assert source_name == "mufasa"
        assert source_type == "ai"
        assert isinstance(leads, list)
        return {"source": source_name, "leads_ingested": len(leads)}

    monkeypatch.setattr("app.services.ai_orchestration_service.ingest_leads", _fake_ingest)

    result = handle_mufasa_prompt("ingest leads", user_id=user_id, db=db)

    assert "ingest_leads" in result["actions_executed"]
    assert result["results"]["ingest_leads"]["leads_ingested"] >= 1
