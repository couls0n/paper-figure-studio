#!/usr/bin/env python3
"""Route a *semantically parsed* figure intent; deliberately not a keyword classifier.

The skill's language model interprets the original request, reference figure and
available data first. This module checks that interpretation and dispatches to
one of twelve stable template families, or to the multipanel composer.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TYPES = (
    "architecture", "comparison", "trajectory", "text_card", "taxonomy",
    "proportion", "bar", "line", "matrix", "scatter", "distribution", "radar",
)
PURPOSE_TO_TYPE = {
    "explain_system": "architecture",
    "compare_cases": "comparison",
    "show_execution": "trajectory",
    "present_text": "text_card",
    "organize_categories": "taxonomy",
    "show_composition": "proportion",
    "compare_values": "bar",
    "show_change": "line",
    "show_pairwise_values": "matrix",
    "show_relationship": "scatter",
    "show_distribution": "distribution",
    "compare_profiles": "radar",
}
RELATION_TO_TYPE = {
    "directed_flow": "architecture",
    "qualitative_contrast": "comparison",
    "event_sequence": "trajectory",
    "verbatim": "text_card",
    "hierarchy": "taxonomy",
    "category_mapping": "taxonomy",
    "part_to_whole": "proportion",
    "category_magnitude": "bar",
    "ordered_numeric": "line",
    "matrix": "matrix",
    "coordinate": "scatter",
    "sample_distribution": "distribution",
    "profile": "radar",
}
# Sets describe semantic compatibility, not claims about what data a renderer
# will silently aggregate. Data transformation still needs an explicit spec.
EVIDENCE_TYPES = {
    "nodes_edges": {"architecture", "taxonomy"},
    "text_cases": {"comparison", "text_card"},
    "step_records": {"trajectory", "architecture"},
    "screenshots": {"trajectory", "comparison"},
    "text_code": {"text_card", "comparison"},
    "category_tree": {"taxonomy"},
    "category_mapping": {"taxonomy"},
    "counts": {"proportion", "bar", "distribution"},
    "category_values": {"bar", "proportion"},
    "ordered_values": {"line", "bar", "scatter"},
    "matrix": {"matrix"},
    "point_coordinates": {"scatter", "line"},
    "raw_samples": {"distribution"},
    "metric_profiles": {"radar", "bar", "matrix"},
}
EXPLICIT_COMPATIBILITY = {
    "architecture": ({"explain_system"}, {"directed_flow"}),
    "comparison": ({"compare_cases"}, {"qualitative_contrast"}),
    "trajectory": ({"show_execution"}, {"event_sequence"}),
    "text_card": ({"present_text"}, {"verbatim"}),
    "taxonomy": ({"organize_categories"}, {"hierarchy", "category_mapping"}),
    "proportion": ({"show_composition"}, {"part_to_whole"}),
    # An explicit bar/matrix request can express a profile. Radar is only the
    # canonical inferred choice when the user actually asks for a profile.
    "bar": ({"compare_values", "show_composition", "show_change", "compare_profiles"},
            {"category_magnitude", "part_to_whole", "ordered_numeric", "profile"}),
    "line": ({"show_change"}, {"ordered_numeric"}),
    "matrix": ({"show_pairwise_values", "compare_profiles"}, {"matrix", "profile"}),
    "scatter": ({"show_relationship"}, {"coordinate"}),
    "distribution": ({"show_distribution"}, {"sample_distribution"}),
    "radar": ({"compare_profiles"}, {"profile"}),
}
# Only unambiguous evidence shapes can select a route alone. In particular,
# categories+numbers do not tell us whether the numbers form parts of a whole.
EVIDENCE_FALLBACK = {
    "category_tree": "taxonomy", "category_mapping": "taxonomy",
    "matrix": "matrix", "raw_samples": "distribution",
}
REQUIRED = {
    "architecture": ("节点、所属分组、带含义的有向边", "Nodes, containers, and semantically labelled directed edges"),
    "comparison": ("对照条件、共用对象及需突出的差异片段", "Conditions, aligned entities, and the differences to highlight"),
    "trajectory": ("步骤与动作记录；若使用截图，还需截图、来源及标注坐标", "Step/action records; screenshot assets, provenance and callout coordinates if used"),
    "text_card": ("完整文本或代码、语言及高亮片段", "Full text or code, language, and highlight spans"),
    "taxonomy": ("类别节点与明确的父子或字段映射关系", "Category nodes with explicit parent-child or field-mapping relationships"),
    "proportion": ("互斥类别的非负计数/比例、分母与每个整体的定义", "Nonnegative exclusive category counts/proportions and the denominator for each whole"),
    "bar": ("类别×系列的数值、单位；如有误差则附统计定义", "Category-by-series values and units; uncertainty definition if shown"),
    "line": ("有顺序的x值与各系列y值、单位；如有误差则附定义", "Ordered x values, series y values and units; uncertainty definition if shown"),
    "matrix": ("行列含义、二维数值、单位、缺失或掩码定义", "Row/column semantics, a 2-D value array, units, and missing/masked-cell meanings"),
    "scatter": ("每个点的坐标与身份/分组；配对图另需pair ID", "Point coordinates and identities/groups; pair IDs for paired displacement"),
    "distribution": ("逐样本观测或明确的分箱计数、分组与变换定义", "Observed samples or explicit bin counts, groups, and transformations"),
    "radar": ("实体×指标数值、固定指标顺序及可比较量程", "Entity-by-metric values, fixed metric order, and comparable scales"),
}
ALTERNATIVES = {
    "proportion": ["bar"],
    "radar": ["bar", "matrix"],
    "line": ["bar"],
}
FIELDS = {
    "schema_version", "request", "purpose", "relationship", "evidence",
    "explicit_type", "excluded_types", "data_status", "missing_inputs",
    "panels", "composition", "semantic_notes", "language",
}


def _enum(value: Any, choices: set[str], name: str) -> None:
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(sorted(choices))}; got {value!r}")


def validate_intent(intent: dict[str, Any], depth: int = 0) -> None:
    """Validate the stable public interface without requiring jsonschema."""
    if not isinstance(intent, dict):
        raise ValueError("intent must be a JSON object")
    if depth > 1:
        raise ValueError("Nested multipanel intents are not supported; flatten leaf panels")
    unknown = set(intent) - FIELDS
    if unknown:
        raise ValueError("Unknown intent fields: " + ", ".join(sorted(unknown)))
    if "schema_version" in intent and (type(intent["schema_version"]) is not int or intent["schema_version"] != 1):
        raise ValueError("schema_version must be 1")
    for k in ("request",):
        if k in intent and not isinstance(intent[k], str):
            raise ValueError(f"{k} must be a string")
    _enum(intent.get("purpose", "unknown"), set(PURPOSE_TO_TYPE) | {"unknown"}, "purpose")
    _enum(intent.get("relationship", "unknown"), set(RELATION_TO_TYPE) | {"unknown"}, "relationship")
    _enum(intent.get("evidence", "unknown"), set(EVIDENCE_TYPES) | {"unknown"}, "evidence")
    _enum(intent.get("data_status", "missing"), {"ready", "partial", "missing"}, "data_status")
    _enum(intent.get("language", "zh"), {"zh", "en"}, "language")
    if intent.get("explicit_type") is not None:
        _enum(intent["explicit_type"], set(TYPES) | {"multipanel"}, "explicit_type")
    for k in ("excluded_types", "missing_inputs", "semantic_notes"):
        if k in intent and (not isinstance(intent[k], list) or not all(isinstance(x, str) and x for x in intent[k])):
            raise ValueError(f"{k} must be an array of nonempty strings")
    for t in intent.get("excluded_types", []):
        _enum(t, set(TYPES) | {"multipanel"}, "excluded_types entry")
    if "composition" in intent and type(intent["composition"]) is not bool:
        raise ValueError("composition must be a boolean")
    if "panels" in intent:
        if not isinstance(intent["panels"], list):
            raise ValueError("panels must be an array")
        ids = []
        for p in intent["panels"]:
            if not isinstance(p, dict) or set(p) != {"id", "intent"}:
                raise ValueError("Each panel must have exactly id and intent")
            if not isinstance(p["id"], str) or not p["id"].strip():
                raise ValueError("Each panel id must be a nonempty string")
            ids.append(p["id"])
            validate_intent(p["intent"], depth + 1)
        if len(ids) != len(set(ids)):
            raise ValueError("Panel ids must be unique")


def _result() -> dict[str, Any]:
    return dict(primary_type=None, panel_routes=[], reasons=[], reason_codes=[],
                needs_clarification=False, clarification_question=None,
                alternatives=[], missing_inputs=[], template=None, reference=None,
                confidence="ambiguous", status="needs_clarification", render_ready=False)


def _message(intent: dict, zh: str, en: str) -> str:
    return en if intent.get("language") == "en" else zh


def _ask(result: dict, intent: dict, code: str, zh: str, en: str,
         alternatives: list[str] | None = None) -> dict:
    result["needs_clarification"] = True
    result["reason_codes"].append(code)
    result["reasons"].append(_message(intent, zh, en))
    result["clarification_question"] = _message(intent, zh, en)
    result["alternatives"] = alternatives or []
    return result


def _finish(result: dict, intent: dict, chart: str, confidence: str) -> dict:
    result["primary_type"] = chart
    result["confidence"] = confidence
    result["template"] = f"assets/templates/{chart}.json"
    result["reference"] = f"references/types/{chart}.md"
    missing = list(intent.get("missing_inputs", []))
    if intent.get("data_status", "missing") != "ready" and not missing:
        missing.append(REQUIRED[chart][1 if intent.get("language") == "en" else 0])
    result["missing_inputs"] = missing
    result["render_ready"] = not missing and intent.get("data_status", "missing") == "ready"
    result["status"] = "ready" if result["render_ready"] else "needs_inputs"
    return result


def _supports(chart: str, purpose: str, relation: str, evidence: str) -> bool:
    purposes, relations = EXPLICIT_COMPATIBILITY[chart]
    return ((purpose == "unknown" or purpose in purposes)
            and (relation == "unknown" or relation in relations)
            and (evidence == "unknown" or chart in EVIDENCE_TYPES[evidence]))


def _single(intent: dict[str, Any]) -> dict[str, Any]:
    result = _result()
    purpose = intent.get("purpose", "unknown")
    relation = intent.get("relationship", "unknown")
    evidence = intent.get("evidence", "unknown")
    explicit = intent.get("explicit_type")
    excluded = set(intent.get("excluded_types", []))
    if explicit:
        if explicit in excluded:
            return _ask(result, intent, "explicit_excluded_conflict",
                        f"你同时指定并排除了 {explicit}。这次应使用哪种图形？",
                        f"The request both requires and excludes {explicit}. Which form should this figure use?")
        if not _supports(explicit, purpose, relation, evidence):
            return _ask(result, intent, "explicit_semantic_conflict",
                        f"指定的 {explicit} 与当前记录的表达目的或数据关系不一致。是保留指定图型，还是以要表达的关系为准？请先核对意图解析。",
                        f"The explicit {explicit} request conflicts with the parsed purpose or data relationship. Keep that form or prioritize the relationship? First verify the intent interpretation.",
                        [explicit])
        result["reason_codes"].append("explicit_choice")
        result["reasons"].append(_message(intent, "采用用户明确指定且与图意兼容的图型。", "Use the user's explicit form, which is compatible with the parsed meaning."))
        return _finish(result, intent, explicit, "high")

    from_purpose = PURPOSE_TO_TYPE.get(purpose)
    from_relation = RELATION_TO_TYPE.get(relation)
    if from_purpose and from_relation and from_purpose != from_relation:
        return _ask(result, intent, "purpose_relation_conflict",
                    "这张图主要要表达哪种关系？当前目的与关系指向不同图型；若两个目的都要表达，请拆成独立面板。",
                    "Which relationship should this figure communicate? The parsed purpose and relationship imply different forms; use separate panels if both are needed.",
                    [from_purpose, from_relation])
    chart = from_purpose or from_relation
    confidence = "high" if from_purpose and from_relation else "medium"
    if chart is None:
        chart = EVIDENCE_FALLBACK.get(evidence)
        confidence = "medium"
        if chart:
            result["reason_codes"].append("unambiguous_evidence_shape")
            result["reasons"].append(_message(intent, f"已有材料 {evidence} 的结构足以选择图型。", f"The unambiguous {evidence} structure selects this form."))
        else:
            candidates = sorted(EVIDENCE_TYPES.get(evidence, set()))
            return _ask(result, intent, "insufficient_semantic_intent",
                        "这张图主要想说明什么：过程、案例差异、数值比较、占比、趋势，还是变量关系？",
                        "What should the figure show: a process, case differences, value comparisons, proportions, a trend, or a variable relationship?",
                        candidates)
    else:
        result["reason_codes"].append("semantic_mapping")
        result["reasons"].append(_message(intent,
            f"按表达目的 {purpose} 与关系 {relation} 路由；原句中的单个词不决定图型。",
            f"Route by purpose {purpose} and relationship {relation}, not isolated words in the request."))
    if evidence != "unknown" and chart not in EVIDENCE_TYPES[evidence]:
        return _ask(result, intent, "evidence_semantic_conflict",
                    f"想表达的关系指向 {chart}，但材料被记录为 {evidence}。请确认材料或关系，避免把不同含义的数据强行套图。",
                    f"The intended relationship suggests {chart}, but evidence is recorded as {evidence}. Verify the data structure or relationship before choosing a template.",
                    [chart])
    if chart in excluded:
        compatible = [c for c in ALTERNATIVES.get(chart, [])
                      if c not in excluded and _supports(c, purpose, relation, evidence)]
        if len(compatible) == 1:
            chart = compatible[0]
            result["reason_codes"].append("respected_exclusion")
            result["reasons"].append(_message(intent,
                "遵守用户的否定要求，采用保留同一数据含义的可用替代表达。",
                "Respect the excluded form and use an available alternative that preserves the meaning."))
            confidence = "medium"
        else:
            return _ask(result, intent, "excluded_inferred_form",
                        "最直接的图型被排除了。你希望采用哪种替代表达？我会保留同一数据含义。",
                        "The most direct form was excluded. Which alternative should preserve this data meaning?",
                        compatible)
    return _finish(result, intent, chart, confidence)


def route(intent: dict[str, Any]) -> dict[str, Any]:
    """Validate and route one figure intent, preserving ambiguity and missing data.

    This function does not claim to infer semantics from request text. The
    original request is retained for an agent/human to audit the interpretation.
    """
    validate_intent(intent)
    result = _result()
    panels = intent.get("panels", [])
    explicit = intent.get("explicit_type")
    wants_composition = intent.get("composition", False) or bool(panels) or explicit == "multipanel"
    if not wants_composition:
        return _single(intent)
    if "multipanel" in intent.get("excluded_types", []):
        return _ask(result, intent, "composition_excluded",
                    "请求包含多个面板，同时又排除了多面板。要合成一张图还是分别导出？",
                    "The request contains several panels but excludes a multipanel figure. Combine them or export separately?")
    if explicit and explicit != "multipanel":
        return _ask(result, intent, "single_composite_conflict",
                    "当前同时指定单一图型和多面板结构。该图型是用于每个面板，还是只需要一个面板？",
                    "A single chart type and a multipanel structure are both specified. Is that type for each panel, or is only one panel needed?")
    if len(panels) < 2:
        return _ask(result, intent, "composition_needs_panels",
                    "多面板图至少需要两个面板：每个面板分别表达什么，使用哪些材料？",
                    "A multipanel figure needs at least two panels. What should each panel show, and which evidence belongs to it?")
    result["primary_type"] = "multipanel"
    result["template"] = "assets/templates/multipanel.json"
    result["reference"] = "references/composition.md"
    result["confidence"] = "high"
    result["missing_inputs"] = list(intent.get("missing_inputs", []))
    if intent.get("data_status") in {"partial", "missing"} and not result["missing_inputs"]:
        result["missing_inputs"].append(_message(intent,
            "组合图的共享输入尚未齐备；请指出缺少的共享材料。",
            "Shared composition inputs are incomplete; identify the missing shared materials."))
    for panel in panels:
        child = dict(panel["intent"])
        if child.get("panels") or child.get("composition") or child.get("explicit_type") == "multipanel":
            raise ValueError("Nested multipanel intents are not supported; flatten leaf panels")
        child.setdefault("language", intent.get("language", "zh"))
        inherited_excluded = set(intent.get("excluded_types", [])) - {"multipanel"}
        child["excluded_types"] = sorted(inherited_excluded | set(child.get("excluded_types", [])))
        r = _single(child)
        result["panel_routes"].append({"id": panel["id"], **r})
        result["missing_inputs"].extend(f'{panel["id"]}: {x}' for x in r["missing_inputs"])
    unclear = [p for p in result["panel_routes"] if p["needs_clarification"]]
    if unclear:
        result["needs_clarification"] = True
        result["confidence"] = "ambiguous"
        result["clarification_question"] = "; ".join(f'{p["id"]}: {p["clarification_question"]}' for p in unclear)
        result["reason_codes"].append("panel_requires_clarification")
    else:
        result["status"] = "ready" if all(p["render_ready"] for p in result["panel_routes"]) and not result["missing_inputs"] else "needs_inputs"
        result["render_ready"] = result["status"] == "ready"
        result["reason_codes"].append("panelwise_routing")
    result["reasons"].append(_message(intent,
        "先按每个面板的表达目的分别路由，再由多面板组合器布局；不把整张图压成一种图型。",
        "Route each panel by its own purpose, then compose the layout; do not force the whole figure into a single type."))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", type=Path, help="Structured intent JSON; omit or use - for stdin")
    parser.add_argument("--out", type=Path, help="Optional output JSON file")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.intent is None or str(args.intent) == "-" else args.intent.read_text(encoding="utf-8")
        result = route(json.loads(raw))
        body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(body, encoding="utf-8")
        else:
            sys.stdout.write(body)
        return 3 if result["needs_clarification"] else 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
