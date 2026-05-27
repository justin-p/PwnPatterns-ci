"""Enriched reviewdog messages (ported from automation/filters/lib/*-message.jq)."""

from __future__ import annotations


def message_join(parts: list[str | None]) -> str:
    return " — ".join(p for p in parts if p)


def vale_message(alert: dict) -> str:
    check = alert.get("Check") or "vale"
    parts: list[str | None] = [
        f"[vale] {check}: {alert.get('Message') or ''}",
    ]
    action = alert.get("Action") or {}
    params = action.get("Params") or []
    if (action.get("Name") or "").lower() == "replace" and params:
        parts.append(f"Suggested replacement: «{params[0]}»")
    ctx = ""
    if "Contractions" in check:
        ctx = (
            "Expand contractions in prose (e.g. wasn't → was not). "
            "YAML [list] blocks are checked separately."
        )
    elif "Terms" in check:
        ctx = "Use allowlisted spelling/casing, or add the term via sync-allowlists."
    elif "Spelling" in check:
        ctx = "Add domain terms to allowlists if the spelling is intentional."
    if ctx:
        parts.append(ctx)
    return message_join(parts)


def harper_replace_text(suggestions: list) -> str:
    if not suggestions:
        return ""
    text = str(suggestions[0])
    if text.startswith("Replace with: "):
        text = text[len("Replace with: ") :]
        for q in ('"', '"', '"', "'"):
            if text.startswith(q) and text.endswith(q):
                text = text[1:-1]
                break
    return text


def harper_message(lint: dict) -> str:
    rule = lint.get("rule") or "?"
    parts: list[str | None] = [
        f"[harper] {rule}: {lint.get('message') or 'lint'}",
    ]
    matched = lint.get("matched_text") or ""
    if matched:
        parts.append(f"In text: «{matched}»")
    repl = harper_replace_text(lint.get("suggestions") or [])
    if repl:
        parts.append(f"Suggested replacement: «{repl}»")
    ctx_map = {
        "MoreAdjective": (
            "Style only: Harper prefers a one-word comparative/superlative "
            "(e.g. more robust → robuster)."
        ),
        "InflectedVerbAfterTo": 'After "to", use the base verb (infinitive), not a conjugated form.',
        "DidPast": 'After "did", use the base verb (e.g. "did enable", not "did enabled").',
        "RepeatedWords": "A word appears twice in a row; remove the duplicate unless intentional.",
    }
    if rule in ctx_map:
        parts.append(ctx_map[rule])
    return message_join(parts)


def textlint_message(msg: dict) -> str:
    rule = msg.get("ruleId") or "textlint"
    parts: list[str | None] = [
        f"[textlint] {rule}: {msg.get('message') or 'textlint issue'}",
    ]
    fix = msg.get("fix") or {}
    if fix.get("text"):
        parts.append(f"Suggested: «{fix['text']}»")
    parts.append("If intentional, add the word to allowlists and sync.")
    return message_join(parts)


def typos_message(rec: dict) -> str:
    corrections = rec.get("corrections") or []
    parts: list[str | None] = [
        f"[typos] Spelling: «{rec.get('typo') or '?'}»",
    ]
    if corrections:
        parts.append(f"Suggested: «{corrections[0]}»")
    else:
        parts.append("No automatic correction available")
    if len(corrections) > 1:
        opts = ", ".join(f"«{c}»" for c in corrections[1:])
        parts.append(f"Other options: {opts}")
    parts.append(
        "If intentional (product name, path, jargon), add to allowlists and re-run sync."
    )
    return message_join(parts)


def rumdl_message(diag: dict) -> str:
    rule = diag.get("rule") or "rumdl"
    parts: list[str | None] = [
        f"[rumdl] {rule}: {diag.get('message') or 'Markdown lint'}",
    ]
    if diag.get("fixable") is True:
        parts.append("Auto-fixable: run rumdl check --fix locally.")
    ctx_map = {
        "MD031": "Markdown: leave a blank line after closing ``` fences.",
        "MD012": "Markdown: remove consecutive blank lines between sections.",
        "MD041": "Markdown: the first line should be a single # heading.",
    }
    if rule in ctx_map:
        parts.append(ctx_map[rule])
    return message_join(parts)


def languagetool_message(match: dict) -> str:
    rule = match.get("rule") or {}
    rule_id = rule.get("id") or match.get("ruleId") or "?"
    issue_type = (rule.get("issueType") or match.get("type", {}).get("typeName") or "").lower()
    parts: list[str | None] = [
        f"[languagetool] {rule_id}: {match.get('message') or 'grammar/spelling issue'}",
    ]
    if issue_type:
        parts.append(f"Type: {issue_type}")
    ctx = match.get("context") or {}
    text = ctx.get("text") or ""
    offset = ctx.get("offset") or 0
    length = ctx.get("length") or 0
    if issue_type == "misspelling" and text and length > 0:
        matched = text[offset : offset + length].strip()
        if matched:
            parts.append(f"Matched: «{matched}»")
    elif text:
        snippet = text if len(text) <= 96 else text[:95] + "…"
        parts.append(f"In text: «{snippet}»")
    replacements = match.get("replacements") or []
    if replacements and replacements[0].get("value"):
        parts.append(f"Suggestion: «{replacements[0]['value']}»")
    return message_join(parts)
