# Helpers for languagetool-to-rdjsonl.jq (reviewdog PR comments).

def lt_rule_id:
  .rule.id // .ruleId // "?";

def lt_issue_type:
  .rule.issueType // .type.typeName // "";

def lt_suggestion:
  (.replacements[0].value // "") | if length > 0 then . else empty end;

def lt_matched_text:
  (.context.text // "") as $t
  | (.context.offset // 0) as $o
  | (.context.length // 0) as $n
  | if $t != "" and $n > 0 then ($t[$o:$o+$n] | gsub("^\\s+|\\s+$"; "")) else ($t | gsub("^\\s+|\\s+$"; "")) end;

def lt_context_snippet:
  (.context.text // "") as $t
  | if ($t | length) > 96 then $t[0:95] + "…" else $t end;

def lt_rdjsonl_message:
  [
    "[languagetool] " + lt_rule_id + ": " + (.message // "grammar/spelling issue"),
    (if lt_issue_type != "" then "Type: " + lt_issue_type else empty end),
    (if (lt_issue_type | ascii_downcase) == "misspelling" then
      (lt_matched_text as $m | if $m != "" then "Matched: «" + $m + "»" else empty end)
     elif .context.text then "In text: «" + lt_context_snippet + "»" else empty end),
    (lt_suggestion as $s | if $s != "" then "Suggestion: «" + $s + "»" else empty end)
  ]
  | map(select(. != null and . != ""))
  | join(" — ");

def lt_replace_suggestion:
  lt_suggestion as $text
  | if $text == "" or $text == null then []
    else [{ "text": $text }]
    end;
