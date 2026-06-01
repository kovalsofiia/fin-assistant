"""
Валідація КВЕД користувача проти довідника kved_restrictions.

Логіка збігу code_pattern з user KVED (напр. 62.01 ↔ 62):
  - точний збіг;
  - user_code починається з pattern + '.';
  - user_code починається з pattern (цілий розділ/підрозділ).

Boolean-прапорці:
  scope=simplified → Allow_g1..g4 = False, лише загальна система;
  scope=group_2  → Allow_g2 = False;
  scope=group_1  → Allow_g1 = False.
"""

from typing import Any, Dict, List, Optional, Set

from core.database import supabase
from core.kved_restrictions_seed import DEFAULT_KVED_RESTRICTIONS

KVED_SIMPLIFIED_BLOCK_REASON = (
    "КВЕД заборонений для спрощеної системи оподаткування — "
    "доступна лише загальна система (перевірте перелік у ДПС)."
)


def normalize_kved_code(code: str) -> str:
    return (code or "").strip().replace(" ", "")


def code_matches_pattern(user_code: str, pattern: str) -> bool:
    """
    Перевірка префікса КВЕД: pattern '62' → '62.01', '62.02';
    pattern '47.1' → '47.11', але не '47.2'.
    """
    u = normalize_kved_code(user_code)
    p = normalize_kved_code(pattern)
    if not u or not p:
        return False
    if u == p:
        return True
    if u.startswith(p + "."):
        return True
    # Цілий розділ (62, 46) — лише якщо наступний символ '.' або кінець
    if len(u) > len(p) and u.startswith(p) and u[len(p)] == ".":
        return True
    return False


def _load_restrictions_from_db() -> List[Dict[str, Any]]:
    try:
        res = (
            supabase.table("kved_restrictions")
            .select("code_pattern, scope, title, note")
            .eq("is_active", True)
            .execute()
        )
        if res.data:
            return res.data
    except Exception as e:
        print(f"KVED restrictions DB load failed: {e}")
    return DEFAULT_KVED_RESTRICTIONS


def _find_hits_for_code(
    user_code: str, rules: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, str]]]:
    hits: Dict[str, List[Dict[str, str]]] = {
        "simplified": [],
        "group_1": [],
        "group_2": [],
    }
    for rule in rules:
        pattern = rule.get("code_pattern", "")
        scope = rule.get("scope", "")
        if scope not in hits:
            continue
        if not code_matches_pattern(user_code, pattern):
            continue
        hits[scope].append(
            {
                "user_code": user_code,
                "pattern": pattern,
                "title": rule.get("title") or pattern,
                "note": rule.get("note"),
            }
        )
    return hits


def _kved_code_from_payload(item: Dict[str, Any]) -> str:
    """API приймає code або kved_code; у БД зберігається kved_code."""
    raw = item.get("kved_code") or item.get("code") or ""
    return normalize_kved_code(str(raw))


def _kved_name_from_payload(item: Dict[str, Any]) -> Optional[str]:
    """API приймає name або kved_name; у БД зберігається kved_name."""
    raw = item.get("kved_name") or item.get("name") or ""
    text = str(raw).strip()[:500]
    return text or None


def _row_to_api_kved(row: Dict[str, Any]) -> Dict[str, Any]:
    code = normalize_kved_code(row.get("kved_code") or row.get("code") or "")
    title = row.get("kved_name") or row.get("name")
    return {"code": code, "kved_code": code, "kved_name": title, "name": title}


def ensure_kved_catalog_entries(kveds: List[Dict[str, Any]]) -> None:
    """
    user_kveds.kved_code → FK на kved_catalog (зазвичай kved_catalog.code).
    Перед insert у user_kveds додаємо відсутні коди в довідник.
    """
    pairs: List[tuple[str, str]] = []
    seen: Set[str] = set()
    for item in kveds:
        code = _kved_code_from_payload(item)
        if not code or code in seen:
            continue
        seen.add(code)
        title = _kved_name_from_payload(item) or f"КВЕД {code}"
        pairs.append((code, title))

    if not pairs:
        return

    # У Supabase довідник часто: code + name (не kved_code)
    primary_rows = [{"code": c, "name": t} for c, t in pairs]
    try:
        supabase.table("kved_catalog").upsert(primary_rows, on_conflict="code").execute()
        return
    except Exception as e:
        err = str(e).lower()
        if "pgrst204" not in err and "code" not in err:
            print(f"kved_catalog upsert (code): {e}")

    alt_rows = [{"kved_code": c, "kved_name": t} for c, t in pairs]
    try:
        supabase.table("kved_catalog").upsert(alt_rows, on_conflict="kved_code").execute()
    except Exception as e2:
        print(f"kved_catalog upsert failed: {e2}")
        raise RuntimeError(
            "Не вдалося додати КВЕД до kved_catalog (очікується code/name або kved_code/kved_name)"
        ) from e2


class KvedValidationService:
    @staticmethod
    def load_user_kveds(user_id: str) -> List[Dict[str, Any]]:
        try:
            res = (
                supabase.table("user_kveds")
                .select("kved_code, kved_name")
                .eq("user_id", user_id)
                .order("kved_code")
                .execute()
            )
            out: List[Dict[str, Any]] = []
            for r in res.data or []:
                mapped = _row_to_api_kved(r)
                if not mapped["code"]:
                    continue
                out.append(mapped)
            return out
        except Exception as e:
            print(f"Load user_kveds failed for {user_id}: {e}")
            raise

    @staticmethod
    def load_user_kved_codes(user_id: str) -> List[str]:
        try:
            return [row["code"] for row in KvedValidationService.load_user_kveds(user_id)]
        except Exception:
            return []

    @staticmethod
    def sync_user_kveds(user_id: str, kveds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ensure_kved_catalog_entries(kveds)
        supabase.table("user_kveds").delete().eq("user_id", user_id).execute()
        rows = []
        for item in kveds:
            kved_code = _kved_code_from_payload(item)
            if not kved_code:
                continue
            rows.append(
                {
                    "user_id": user_id,
                    "kved_code": kved_code,
                    "kved_name": _kved_name_from_payload(item),
                }
            )
        if not rows:
            return []
        res = supabase.table("user_kveds").insert(rows).execute()
        return [_row_to_api_kved(r) for r in (res.data or [])]

    @staticmethod
    def validate_user_kveds(
        user_kveds: List[str],
        restrictions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        codes = [normalize_kved_code(c) for c in user_kveds if normalize_kved_code(c)]
        rules = restrictions if restrictions is not None else _load_restrictions_from_db()

        simplified_hits: List[Dict[str, str]] = []
        group1_hits: List[Dict[str, str]] = []
        group2_hits: List[Dict[str, str]] = []
        per_code: List[Dict[str, Any]] = []

        for user_code in codes:
            code_hits = _find_hits_for_code(user_code, rules)
            per_code.append({"code": user_code, "hits": code_hits})
            simplified_hits.extend(code_hits["simplified"])
            group1_hits.extend(code_hits["group_1"])
            group2_hits.extend(code_hits["group_2"])

        blocks_simplified = len(simplified_hits) > 0
        blocked_groups: Set[int] = set()

        # scope = simplified → усі групи спрощеної недоступні
        if blocks_simplified:
            blocked_groups.update({1, 2, 3, 4})
        if group1_hits:
            blocked_groups.add(1)
        if group2_hits:
            blocked_groups.add(2)

        allow_g1 = 1 not in blocked_groups
        allow_g2 = 2 not in blocked_groups
        allow_g3 = 3 not in blocked_groups
        allow_g4 = 4 not in blocked_groups

        return {
            "user_kved_codes": codes,
            "has_kveds": len(codes) > 0,
            "blocks_simplified_system": blocks_simplified,
            "blocked_groups": sorted(blocked_groups),
            "allow": {
                "group_1": allow_g1,
                "group_2": allow_g2,
                "group_3": allow_g3,
                "group_4": allow_g4,
                "simplified_system": not blocks_simplified,
                "general_system": True,
            },
            "simplified_violations": simplified_hits,
            "group_1_violations": group1_hits,
            "group_2_violations": group2_hits,
            "per_code": per_code,
            "simplified_block_reason": KVED_SIMPLIFIED_BLOCK_REASON if blocks_simplified else None,
        }

    @staticmethod
    def apply_kved_blocks_to_groups(
        groups: List[Dict[str, Any]], kved_validation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        blocked: Set[int] = set(kved_validation.get("blocked_groups") or [])
        if not blocked:
            return groups

        blocks_simplified = kved_validation.get("blocks_simplified_system")
        out = []
        for row in groups:
            g = row["group"]
            if g not in blocked:
                out.append(row)
                continue

            if blocks_simplified:
                violations = kved_validation.get("simplified_violations") or []
                codes = ", ".join(
                    dict.fromkeys(f"{v['user_code']} ({v['pattern']})" for v in violations[:5])
                )
                reason = KVED_SIMPLIFIED_BLOCK_REASON
                if codes:
                    reason += f" Збіги: {codes}."
            elif g == 1:
                hits = kved_validation.get("group_1_violations") or []
                reason = "КВЕД не дозволяє 1 групу: " + ", ".join(
                    f"{h['user_code']} → {h['pattern']}" for h in hits[:3]
                )
            elif g == 2:
                hits = kved_validation.get("group_2_violations") or []
                reason = "КВЕД не дозволяє 2 групу: " + ", ".join(
                    f"{h['user_code']} → {h['pattern']}" for h in hits[:3]
                )
            else:
                reason = KVED_SIMPLIFIED_BLOCK_REASON

            out.append(
                {
                    **row,
                    "eligible": False,
                    "disqualifyReason": reason,
                    "estimatedAnnualTaxUah": None,
                    "blockedByKved": True,
                }
            )
        return out
