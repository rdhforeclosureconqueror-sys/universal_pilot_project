import pytest

from fastapi import HTTPException

from api.routes.cases import _resolve_allowed_meta_fields, _validate_meta_fields_or_422


def test_allowed_meta_fields_supported():
    cfg = {"allowed_meta_fields": ["contact_hash", "source"]}
    assert _resolve_allowed_meta_fields(cfg) == ["contact_hash", "source"]
    _validate_meta_fields_or_422(incoming_meta={"contact_hash": "x"}, policy_config=cfg)


def test_unknown_fields_rejected():
    cfg = {"allowed_meta_fields": ["contact_hash"]}
    with pytest.raises(HTTPException) as exc:
        _validate_meta_fields_or_422(incoming_meta={"unknown": 1}, policy_config=cfg)
    assert exc.value.status_code == 422


def test_legacy_allowed_fields_supported():
    cfg = {"allowed_fields": ["legacy"]}
    assert _resolve_allowed_meta_fields(cfg) == ["legacy"]
    _validate_meta_fields_or_422(incoming_meta={"legacy": "ok"}, policy_config=cfg)
