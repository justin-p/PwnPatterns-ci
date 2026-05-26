# Helpers for textlint-to-rdjsonl.jq (reviewdog PR comments).
include "message-parts";

def textlint_rule_id:
  .ruleId // "textlint";

def textlint_suggestion:
  .fix.text // "";

def textlint_rdjsonl_message:
  [
    "[textlint] " + textlint_rule_id + ": " + (.message // "textlint issue"),
    (textlint_suggestion as $s | if $s != "" then "Suggested: «" + $s + "»" else empty end),
    "If intentional, add the word to allowlists and sync."
  ]
  | message_join;

