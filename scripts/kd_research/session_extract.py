"""Hermetic extractors: session disk files → comparison / snapshot fields.

No live market fetches. Prefer orchestrator price_snapshot when present.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _num(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict) and "value" in v:
        return _num(v.get("value"))
    if isinstance(v, str):
        try:
            return float(v.strip().replace(",", ""))
        except ValueError:
            return None
    return None


def unwrap_prob(v: Any) -> float | None:
    """scenario_probabilities entry: bare float or {value, rationale, ...}."""
    n = _num(v)
    if n is None:
        return None
    # Accept 0-1 or 0-100 (percent) — normalize to 0-1 if clearly percent
    if n > 1.0 and n <= 100.0:
        return n / 100.0
    return n


def extract_scenario_probs(
    valuation: dict[str, Any] | None,
    risk_bridge: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    probs: dict[str, float | None] = {"bear": None, "base": None, "bull": None}
    sources: list[Any] = []
    if valuation:
        fv = valuation.get("fair_value") or {}
        if isinstance(fv, dict) and isinstance(fv.get("scenario_probabilities"), dict):
            sources.append(fv["scenario_probabilities"])
        if isinstance(valuation.get("scenario_probabilities"), dict):
            sources.append(valuation["scenario_probabilities"])
    if risk_bridge and isinstance(risk_bridge.get("scenario_probabilities"), dict):
        sources.append(risk_bridge["scenario_probabilities"])

    for src in sources:
        for k in ("bear", "base", "bull"):
            if probs[k] is None and k in src:
                probs[k] = unwrap_prob(src[k])
        if all(probs[k] is not None for k in probs):
            break
    return probs


def normalize_mos_pct(
    mos: Any,
    *,
    asof: float | None = None,
    fv_base: float | None = None,
    field_hint: str | None = None,
) -> float | None:
    """Return margin of safety as a *percent* (e.g. -17.65), not a fraction.

    Prefer recomputing from asof/base when both present (consistent for compare DB).
    Else: values from ``*_pct`` fields are treated as percent; bare ``margin_of_safety``
    with |n|<=1.5 is treated as a ratio and multiplied by 100.
    """
    if isinstance(asof, (int, float)) and isinstance(fv_base, (int, float)) and fv_base:
        return round((1.0 - float(asof) / float(fv_base)) * 100.0, 4)

    n = _num(mos)
    if n is None:
        return None
    hint = (field_hint or "").lower()
    if "pct" in hint or "percent" in hint:
        return round(n, 4)
    if abs(n) <= 1.5:
        return round(n * 100.0, 4)
    return round(n, 4)


def _price_from_snapshot(session: Path) -> tuple[float | None, str | None]:
    snap = load_json(session / "data" / "price_snapshot.json")
    if not snap:
        return None, None
    for key in ("close", "current_price", "price", "last_close", "asof_price"):
        n = _num(snap.get(key))
        if n is not None:
            return n, "data/price_snapshot.json"
    return None, None


def _price_from_technical(technical: dict[str, Any] | None) -> tuple[float | None, str | None]:
    if not technical:
        return None, None
    anchor = technical.get("price_anchor")
    if isinstance(anchor, dict):
        n = _num(anchor.get("last_close") or anchor.get("close") or anchor.get("price"))
        if n is not None:
            return n, "registry/technical.json#price_anchor"
    for key in ("asof_price", "last_price", "price", "close"):
        n = _num(technical.get(key))
        if n is not None:
            return n, f"registry/technical.json#{key}"
    levels = technical.get("levels")
    if isinstance(levels, dict):
        for key in ("last", "close", "price", "asof_price"):
            n = _num(levels.get(key))
            if n is not None:
                return n, f"registry/technical.json#levels.{key}"
    latest = technical.get("latest_snapshot")
    if isinstance(latest, dict):
        n = _num(latest.get("close") or latest.get("price"))
        if n is not None:
            return n, "registry/technical.json#latest_snapshot"
    indicators = technical.get("indicators")
    if isinstance(indicators, dict):
        for key in ("last_close", "close", "price"):
            n = _num(indicators.get(key))
            if n is not None:
                return n, f"registry/technical.json#indicators.{key}"
        price_block = indicators.get("price")
        if isinstance(price_block, dict):
            n = _num(price_block.get("last_close") or price_block.get("close"))
            if n is not None:
                return n, "registry/technical.json#indicators.price"
    return None, None


def _price_from_valuation(valuation: dict[str, Any] | None) -> tuple[float | None, str | None]:
    if not valuation:
        return None, None
    for key in ("asof_price", "price", "current_price"):
        n = _num(valuation.get(key))
        if n is not None:
            return n, f"data/valuation_model.json#{key}"
    fv = valuation.get("fair_value")
    if isinstance(fv, dict):
        for key in ("current_price", "asof_price", "price"):
            n = _num(fv.get(key))
            if n is not None:
                return n, f"data/valuation_model.json#fair_value.{key}"
    return None, None


def _price_from_csv(session: Path) -> tuple[float | None, str | None]:
    data = session / "data"
    if not data.is_dir():
        return None, None
    candidates = ["prices_stock.csv"]
    candidates.extend(sorted(p.name for p in data.glob("prices_*.csv")))
    seen: set[str] = set()
    for name in candidates:
        if name in seen:
            continue
        seen.add(name)
        if "benchmark" in name or "sector" in name:
            continue
        p = data / name
        if not p.is_file():
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            if len(lines) < 2:
                continue
            header = [h.strip().lower() for h in lines[0].split(",")]
            close_idx = next(
                (i for i, h in enumerate(header) if h in ("close", "adj close", "adj_close", "price")),
                None,
            )
            if close_idx is None:
                continue
            last = lines[-1].split(",")
            if close_idx < len(last):
                return float(last[close_idx]), f"data/{name}"
        except Exception:  # noqa: BLE001
            continue
    return None, None


def price_looks_insane(asof: float | None, fv_base: float | None) -> bool:
    """Heuristic for wrong-unit / wrong-series prices (e.g. SOFI 7757 vs FV 13)."""
    if asof is None or fv_base is None:
        return False
    if asof <= 0 or fv_base <= 0:
        return False
    ratio = asof / fv_base
    return ratio > 50.0 or ratio < 0.02


def extract_asof_price(
    session: Path,
    valuation: dict[str, Any] | None = None,
    technical: dict[str, Any] | None = None,
) -> tuple[float | None, str | None, list[str]]:
    """Return (price, source, gaps). Prefer price_snapshot; reject insane vs fv_base."""
    gaps: list[str] = []
    if valuation is None:
        valuation = load_json(session / "data" / "valuation_model.json")
    if technical is None:
        technical = load_json(session / "registry" / "technical.json")

    fv_base = None
    if valuation:
        fv = valuation.get("fair_value") or {}
        if isinstance(fv, dict):
            fv_base = _num(fv.get("base"))

    candidates: list[tuple[float, str]] = []
    for extractor in (
        _price_from_snapshot,
        lambda s: _price_from_technical(technical),
        lambda s: _price_from_valuation(valuation),
        _price_from_csv,
    ):
        # first extractor takes session only
        if extractor is _price_from_snapshot or extractor is _price_from_csv:
            price, src = extractor(session)
        else:
            price, src = extractor(session)  # type: ignore[misc]
        if price is not None and src:
            candidates.append((price, src))

    # Prefer non-insane; else first
    for price, src in candidates:
        if not price_looks_insane(price, fv_base):
            return round(price, 6), src, gaps

    if candidates:
        price, src = candidates[0]
        gaps.append(
            f"asof_price {price} looks inconsistent vs fv_base={fv_base}; kept best available from {src}"
        )
        return round(price, 6), src, gaps

    gaps.append("asof_price not found in price_snapshot/technical/valuation/prices csv")
    return None, None, gaps


def extract_fair_value(valuation: dict[str, Any] | None) -> dict[str, Any]:
    fv_raw = (valuation or {}).get("fair_value") or {}
    if not isinstance(fv_raw, dict):
        fv_raw = {}
    return {
        "base": _num(fv_raw.get("base")),
        "bear": _num(fv_raw.get("bear")),
        "bull": _num(fv_raw.get("bull")),
        "probability_weighted": _num(
            fv_raw.get("probability_weighted") or fv_raw.get("weighted") or fv_raw.get("pw")
        ),
        "currency": fv_raw.get("currency") or (valuation or {}).get("currency") or "",
    }


def _map_trend_word(text: str) -> str | None:
    t = text.lower()
    bear_kw = ("bear", "downtrend", "breakdown", "sell", "weak", "negative")
    bull_kw = ("bull", "uptrend", "breakout", "buy", "strong_up", "positive", "resume")
    neut_kw = ("neutral", "range", "sideways", "chop", "consolidate", "pullback")
    # order: explicit neutral in mixed names
    if any(k in t for k in neut_kw) and not any(k in t for k in ("strong_up", "strong_down")):
        if "uptrend" in t:
            return "bullish"
        if "downtrend" in t:
            return "bearish"
        return "neutral"
    if any(k in t for k in bull_kw) and not any(k in t for k in bear_kw):
        return "bullish"
    if any(k in t for k in bear_kw) and not any(k in t for k in bull_kw):
        return "bearish"
    if any(k in t for k in bull_kw) and any(k in t for k in bear_kw):
        return "neutral"
    return None


def extract_technical_summary(technical: dict[str, Any] | None) -> dict[str, Any]:
    """Best-effort tech_signal / tech_regime across heterogeneous agent shapes."""
    out: dict[str, Any] = {
        "tech_signal": None,
        "tech_regime": None,
        "tech_summary": {},
    }
    if not technical:
        return out

    summary: dict[str, Any] = {}
    signal: str | None = None
    regime: str | None = None

    # Direct fields
    for key in ("overall_signal", "signal", "tech_signal", "recommendation"):
        v = technical.get(key)
        if isinstance(v, str) and v.strip():
            signal = _map_trend_word(v) or v.strip().lower()
            summary["signal_source"] = key
            break
        if isinstance(v, dict) and v.get("value"):
            signal = _map_trend_word(str(v["value"])) or str(v["value"]).lower()
            summary["signal_source"] = key
            break

    bias = technical.get("near_term_bias")
    if signal is None and bias is not None:
        if isinstance(bias, dict):
            raw = str(bias.get("value") or bias.get("bias") or "")
        else:
            raw = str(bias)
        if raw:
            signal = _map_trend_word(raw) or "neutral"
            summary["near_term_bias"] = raw[:200]
            summary["signal_source"] = "near_term_bias"

    trend = technical.get("trend")
    if isinstance(trend, dict):
        classification = trend.get("classification") or trend.get("value")
        if classification:
            regime = str(classification)
            summary["trend_classification"] = regime
            if signal is None:
                signal = _map_trend_word(regime)
                summary["signal_source"] = "trend.classification"
    elif isinstance(trend, str) and trend:
        regime = trend
        if signal is None:
            signal = _map_trend_word(trend)

    indicators = technical.get("indicators")
    if isinstance(indicators, dict):
        ind_trend = indicators.get("trend")
        if isinstance(ind_trend, dict):
            for k in ("classification", "regime", "label", "value"):
                if ind_trend.get(k):
                    if regime is None:
                        regime = str(ind_trend[k])
                    if signal is None:
                        signal = _map_trend_word(str(ind_trend[k]))
                        summary["signal_source"] = f"indicators.trend.{k}"
                    break
            summary["indicators_trend"] = {
                k: ind_trend[k]
                for k in list(ind_trend)[:8]
                if not isinstance(ind_trend[k], (dict, list))
            }
        # highest_probability_near_term_scenario string
        hp = indicators.get("highest_probability_near_term_scenario")
        if isinstance(hp, str) and hp:
            summary["highest_probability_scenario"] = hp[:200]
            if signal is None:
                signal = _map_trend_word(hp)
                summary["signal_source"] = "indicators.highest_probability_near_term_scenario"

    scenarios = technical.get("scenarios")
    if isinstance(scenarios, list) and scenarios:
        best_name = None
        best_p = -1.0
        for s in scenarios:
            if not isinstance(s, dict):
                continue
            p = unwrap_prob(s.get("probability"))
            if p is not None and p > best_p:
                best_p = p
                best_name = s.get("name") or s.get("id")
        if best_name:
            summary["top_scenario"] = str(best_name)
            summary["top_scenario_p"] = best_p
            if signal is None:
                signal = _map_trend_word(str(best_name))
                summary["signal_source"] = "scenarios[max p]"

    levels = technical.get("levels")
    if isinstance(levels, dict):
        compact = {}
        for k in ("entry", "stop_loss", "stop", "targets"):
            if k not in levels:
                continue
            v = levels[k]
            if isinstance(v, dict) and "value" in v:
                compact[k] = _num(v.get("value"))
            else:
                compact[k] = _num(v)
        if compact:
            summary["levels"] = compact

    out["tech_signal"] = signal
    out["tech_regime"] = regime
    out["tech_summary"] = summary
    return out


def extract_key_risks(session: Path) -> list[str]:
    risks: list[str] = []
    rb = load_json(session / "registry" / "risk_bridge.json")
    if rb:
        scenarios = (rb.get("stress_test") or {}).get("scenarios") or rb.get("scenarios") or []
        if isinstance(scenarios, list):
            for s in scenarios[:5]:
                if isinstance(s, dict):
                    name = s.get("name") or s.get("id") or s.get("scenario")
                    if name:
                        risks.append(str(name))
        top = rb.get("top_risks") or rb.get("key_risks")
        if isinstance(top, list):
            for r in top[:5]:
                if isinstance(r, str):
                    risks.append(r)
                elif isinstance(r, dict) and r.get("name"):
                    risks.append(str(r["name"]))
    lq = load_json(session / "registry" / "latest_quarter.json")
    if lq and isinstance(lq.get("risks"), list):
        for r in lq["risks"][:5]:
            if isinstance(r, str):
                risks.append(r)
            elif isinstance(r, dict):
                label = r.get("risk") or r.get("description") or r.get("name") or r.get("id")
                if isinstance(label, str) and label.strip():
                    risks.append(label.strip())
    seen: set[str] = set()
    out: list[str] = []
    for r in risks:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out[:8]


def extract_verdict_line(session: Path, ticker: str) -> str:
    readme = session / "reports" / f"00_{ticker.upper()}_README.md"
    if not readme.is_file():
        matches = list((session / "reports").glob("00_*README.md")) if (session / "reports").is_dir() else []
        readme = matches[0] if matches else readme
    if not readme.is_file():
        return ""
    text = readme.read_text(encoding="utf-8", errors="replace")
    for pattern in (
        r"(?im)^#+\s*verdict[^\n]*\n+([^\n]+)",
        r"(?im)^\*\*verdict\*\*[:\s]+([^\n]+)",
        r"(?im)^verdict[:\s]+([^\n]+)",
    ):
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()[:500]
    for line in text.splitlines():
        low = line.lower()
        if "bull" in low and "bear" in low:
            return line.strip()[:500]
    return ""


def extract_peers(session: Path, sector: dict[str, Any] | None) -> list[str]:
    if sector:
        for key in ("peers", "peer_tickers", "closest_peers"):
            v = sector.get(key)
            if isinstance(v, list):
                return [str(x) for x in v if str(x).upper() != (sector.get("ticker") or "").upper()]
            if isinstance(v, str) and v.strip():
                return [p.strip() for p in v.split(",") if p.strip()]
    brief = load_json(session / "registry" / "research_brief.json")
    if brief:
        for key in ("peers", "peer_tickers", "closest_peers"):
            v = brief.get(key)
            if isinstance(v, list):
                return [str(x) for x in v]
    peer_csv = session / "data" / "peer_comparison.csv"
    if peer_csv.is_file():
        try:
            lines = peer_csv.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) >= 2:
                header = [h.strip().lower() for h in lines[0].split(",")]
                t_idx = header.index("ticker") if "ticker" in header else 0
                tickers = []
                self_t = session.parent.name.upper()
                for line in lines[1:8]:
                    parts = line.split(",")
                    if t_idx < len(parts):
                        t = parts[t_idx].strip()
                        if t and t.upper() != self_t:
                            tickers.append(t)
                return tickers[:6]
        except Exception:  # noqa: BLE001
            pass
    return []


def _extract_decision_action(session: Path) -> str | None:
    from scripts.kd_research.decision import extract_decision_action  # noqa: WPS433

    return extract_decision_action(session)


def _extract_kill_triggers(session: Path) -> list[str]:
    from scripts.kd_research.decision import extract_kill_triggers  # noqa: WPS433

    return extract_kill_triggers(session)


def extract_session_bundle(session: Path) -> dict[str, Any]:
    """Full comparison payload derived only from session files."""
    from scripts.kd_research.roic_identity import thin_roic_from_valuation  # noqa: WPS433

    session = session.resolve()
    # session_key is folder name; ticker is parent
    session_key = session.name
    ticker = session.parent.name.upper()
    session_date = session_key.split("__", 1)[0]

    valuation = load_json(session / "data" / "valuation_model.json")
    technical = load_json(session / "registry" / "technical.json")
    sector = load_json(session / "registry" / "sector_config.json")
    market = load_json(session / "registry" / "market_context.json")
    audit = load_json(session / "registry" / "audit.json")
    risk_bridge = load_json(session / "registry" / "risk_bridge.json")
    manifest = load_json(session / "meta" / "run_manifest.json")
    brief = load_json(session / "registry" / "research_brief.json")

    gaps: list[str] = []
    if valuation is None:
        gaps.append("data/valuation_model.json missing or unparseable")
    if audit is None:
        gaps.append("registry/audit.json missing")

    fair_value = extract_fair_value(valuation)
    probs = extract_scenario_probs(valuation, risk_bridge)
    price, price_src, price_gaps = extract_asof_price(session, valuation, technical)
    gaps.extend(price_gaps)

    mos_raw = None
    mos_hint = None
    if valuation:
        fv = valuation.get("fair_value") or {}
        if isinstance(fv, dict):
            if fv.get("margin_of_safety_pct") is not None:
                mos_raw = fv.get("margin_of_safety_pct")
                mos_hint = "margin_of_safety_pct"
            elif fv.get("margin_of_safety") is not None:
                mos_raw = fv.get("margin_of_safety")
                mos_hint = "margin_of_safety"
        if mos_raw is None and valuation.get("margin_of_safety_pct") is not None:
            mos_raw = valuation.get("margin_of_safety_pct")
            mos_hint = "margin_of_safety_pct"
    mos = normalize_mos_pct(
        mos_raw,
        asof=price,
        fv_base=fair_value.get("base"),
        field_hint=mos_hint,
    )

    tech = extract_technical_summary(technical)

    model_name = None
    if valuation:
        m = valuation.get("model")
        if isinstance(m, str):
            model_name = m
        elif isinstance(m, dict):
            model_name = m.get("name") or m.get("type") or m.get("id")

    priced = None
    decision_usefulness = None
    if valuation is not None:
        from scripts.kd_research.decision_quality import (  # noqa: WPS433
            extract_priced_for_perfection,
        )

        priced, _pfp_rationale = extract_priced_for_perfection(valuation)
        fv_block = valuation.get("fair_value") if isinstance(valuation.get("fair_value"), dict) else {}
        du = fv_block.get("decision_usefulness")
        if isinstance(du, dict):
            du = du.get("value") or du.get("class")
        if isinstance(du, str) and du.strip():
            decision_usefulness = du.strip().lower()

    provenance = {
        "experiment_id": (manifest or {}).get("experiment_id"),
        "experiment_label": (manifest or {}).get("experiment_label"),
        "replicate": (manifest or {}).get("replicate"),
        "harness_version": (manifest or {}).get("harness_version"),
        "harness_spec": (manifest or {}).get("harness_spec") or "v2",
        "harness_git_sha": (manifest or {}).get("harness_git_sha"),
        "harness_dirty": (manifest or {}).get("harness_dirty"),
        "agents_md_sha256": (manifest or {}).get("agents_md_sha256"),
        "research_agents_sha256": (manifest or {}).get("research_agents_sha256"),
        "prompts_sha256": (manifest or {}).get("prompts_sha256"),
        "version_file_sha256": (manifest or {}).get("version_file_sha256"),
        "orchestrator_model": (manifest or {}).get("orchestrator_model"),
        "default_subagent_model": (manifest or {}).get("default_subagent_model"),
        "model_map": (manifest or {}).get("model_map"),
        "temperature": (manifest or {}).get("temperature"),
        "seed": (manifest or {}).get("seed"),
        "notes": (manifest or {}).get("notes"),
    }

    research_depth = None
    if brief:
        rd = brief.get("research_depth")
        if isinstance(rd, dict):
            research_depth = rd.get("value") or rd.get("depth")
        elif isinstance(rd, str):
            research_depth = rd

    benchmark = ""
    if technical:
        benchmark = (
            technical.get("benchmark")
            or technical.get("benchmark_symbol")
            or ""
        )
        if not benchmark and isinstance(technical.get("benchmarks"), dict):
            # first key or named
            b = technical["benchmarks"]
            benchmark = str(b.get("primary") or b.get("symbol") or next(iter(b), "") or "")
        if not benchmark and isinstance(technical.get("benchmarks"), list) and technical["benchmarks"]:
            b0 = technical["benchmarks"][0]
            if isinstance(b0, str):
                benchmark = b0
            elif isinstance(b0, dict):
                benchmark = str(b0.get("symbol") or b0.get("ticker") or "")

    peers = extract_peers(session, sector)
    audit_verdict = (audit or {}).get("verdict") if audit else None

    return {
        "ticker": ticker,
        "session_date": session_date,
        "session_key": session_key,
        "asof_price": price,
        "asof_price_source": price_src,
        "currency": fair_value.get("currency") or "",
        "fair_value": fair_value,
        "scenario_probabilities": probs,
        "margin_of_safety_pct": mos,
        "verdict_line": extract_verdict_line(session, ticker),
        "primary_sector": (sector or {}).get("primary_sector") or "",
        "region": (market or {}).get("primary_region") or "",
        "intensity": (market or {}).get("intensity") or "",
        "key_risks": extract_key_risks(session),
        "peers": peers,
        "benchmark": benchmark if isinstance(benchmark, str) else str(benchmark),
        "data_quality": (sector or {}).get("data_quality")
        or ((valuation or {}).get("data_quality") if valuation else None)
        or ("degraded" if gaps else "ok"),
        "audit_verdict": audit_verdict,
        "priced_for_perfection": priced,
        "decision_usefulness": decision_usefulness,
        "roic_identity": thin_roic_from_valuation(valuation),
        "model_name": model_name,
        "tech_signal": tech.get("tech_signal"),
        "tech_regime": tech.get("tech_regime"),
        "tech_summary": tech.get("tech_summary") or {},
        "research_depth": research_depth,
        "decision_action": _extract_decision_action(session),
        "kill_triggers": _extract_kill_triggers(session),
        "provenance": provenance,
        "gaps": gaps,
        "status": (manifest or {}).get("status")
        or ("complete" if audit_verdict == "PASS" else ("audited" if audit_verdict else "unknown")),
    }
