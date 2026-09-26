from datetime import date
from types import SimpleNamespace

from agent import prompts


def test_build_system_prompt_includes_date_profile_and_disclaimer():
    text = prompts.build_system_prompt(date(2026, 9, 27), "- Група ФОП: 3")

    assert "2026-09-27" in text
    assert "- Група ФОП: 3" in text
    assert prompts.TAX_DISCLAIMER in text
    assert "українською" in text


def test_format_profile_context_formats_values_and_skips_missing():
    text = prompts.format_profile_context(
        {"fop_group": 3, "is_vat_payer": False, "has_employees": True, "tax_system": None}
    )

    assert text == "- Група ФОП: 3\n- Платник ПДВ: ні\n- Має найманих працівників: так"


def test_format_profile_context_empty():
    assert prompts.format_profile_context({}) == prompts.PROFILE_UNAVAILABLE


def test_load_profile_context_uses_current_user(monkeypatch):
    calls = {}

    def fake(user_id, current_user_id):
        calls.update(user_id=user_id, current=current_user_id)
        return SimpleNamespace(model_dump=lambda mode: {"fop_group": 2})

    monkeypatch.setattr(prompts.settings_router, "get_fop_settings", fake)

    assert prompts.load_profile_context("user-1") == "- Група ФОП: 2"
    assert calls == {"user_id": "user-1", "current": "user-1"}


def test_load_profile_context_accepts_dict(monkeypatch):
    monkeypatch.setattr(
        prompts.settings_router, "get_fop_settings", lambda user_id, current_user_id: {"fop_group": 1}
    )

    assert prompts.load_profile_context("user-1") == "- Група ФОП: 1"


def test_load_profile_context_never_raises(monkeypatch):
    def fake(user_id, current_user_id):
        raise RuntimeError("db down")

    monkeypatch.setattr(prompts.settings_router, "get_fop_settings", fake)

    assert prompts.load_profile_context("user-1") == prompts.PROFILE_UNAVAILABLE
