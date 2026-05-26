# Helpers for languagetool-to-rdjsonl.jq (reviewdog PR comments).

def lt_rule_id:
  .rule.id // .ruleId // "?";

def lt_issue_type:
  .rule.issueType // .type.typeName // "";

def lt_suggestion:
  (.replacements[0].value // "") | if length > 0 then . else empty end;

def lt_rdjsonl_message:
  [
    "[languagetool] " + lt_rule_id + ": " + (.message // "grammar/spelling issue"),
    (if lt_issue_type != "" then "Type: " + lt_issue_type else empty end),
    (if .context.text then "In text: «" + .context.text + "»" else empty end),
    (lt_suggestion as $s | if $s != "" then "Suggestion: «" + $s + "»" else empty end)
  ]
  | map(select(. != null and . != ""))
  | join(" — ");

def lt_replace_suggestion:
  lt_suggestion as $text
  | if $text == "" or $text == null then []
    else [{ "text": $text }]
    end;
