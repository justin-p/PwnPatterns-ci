# Helpers for harper-to-rdjsonl.jq (reviewdog PR comments).
include "message-parts";

def harper_replace_text:
  (.suggestions[0] // "")
  | if test("^Replace with: ") then
      sub("^Replace with: "; "")
      | gsub("^(“|\")|(\"|”)$"; "")
    else
      .
    end;

def harper_context:
  if .rule == "MoreAdjective" then
    "Style only: Harper prefers a one-word comparative/superlative (e.g. more robust → robuster)."
  elif .rule == "InflectedVerbAfterTo" then
    "After \"to\", use the base verb (infinitive), not a conjugated form."
  elif .rule == "DidPast" then
    "After \"did\", use the base verb (e.g. \"did enable\", not \"did enabled\")."
  elif .rule == "RepeatedWords" then
    "A word appears twice in a row; remove the duplicate unless intentional."
  else
    empty
  end;

def harper_rdjsonl_message:
  [
    "[harper] " + (.rule // "?") + ": " + (.message // "lint"),
    (
      if (.matched_text // "") != "" then
        "In text: «" + .matched_text + "»"
      else
        empty
      end
    ),
    (
      harper_replace_text as $t
      | if ($t | length) > 0 then
          "Suggested replacement: «" + $t + "»"
        else
          empty
        end
    ),
    (
      harper_context as $c
      | if ($c | length) > 0 then $c else empty end
    )
  ]
  | message_join;

def harper_replace_suggestion:
  harper_replace_text as $text
  | if ($text | length) > 0 then
      [{
        range: {
          start: {
            line: (.line // 1),
            column: (.column // 1)
          },
          end: {
            line: (.line // 1),
            column: ((.column // 1) + ((.matched_text // "") | length))
          }
        },
        text: $text
      }]
    else
      []
    end;
