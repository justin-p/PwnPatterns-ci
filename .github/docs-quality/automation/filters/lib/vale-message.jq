# Helpers for vale-to-rdjsonl.jq (reviewdog PR comments).
include "message-parts";

def vale_context:
  if (.Check // "") | test("Contractions") then
    "Expand contractions in prose (e.g. wasn't → was not). YAML [list] blocks are checked separately."
  elif (.Check // "") | test("Terms") then
    "Use allowlisted spelling/casing, or add the term via sync-allowlists."
  elif (.Check // "") | test("Spelling") then
    "Add domain terms to allowlists if the spelling is intentional."
  else
    empty
  end;

def vale_rdjsonl_message:
  [
    "[vale] " + (.Check // "vale") + ": " + (.Message // ""),
    (
      if ((.Action.Name // "") | ascii_downcase) == "replace"
        and ((.Action.Params // []) | length) > 0
      then
        "Suggested replacement: «" + .Action.Params[0] + "»"
      else
        empty
      end
    ),
    vale_context
  ]
  | message_join;
