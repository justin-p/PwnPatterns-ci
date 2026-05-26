# Helpers for typos-to-rdjsonl.jq (reviewdog PR comments).
include "message-parts";

def typos_more_corrections:
  if (.corrections | length) > 1 then
    "Other options: " + (.corrections[1:] | map("«" + . + "»") | join(", "))
  else
    empty
  end;

def typos_rdjsonl_message:
  [
    "[typos] Spelling: «" + (.typo // "?") + "»",
    (
      if (.corrections | length) > 0 then
        "Suggested: «" + .corrections[0] + "»"
      else
        "No automatic correction available"
      end
    ),
    typos_more_corrections,
    "If intentional (product name, path, jargon), add to allowlists and re-run sync."
  ]
  | message_join;

def typos_start_col:
  ((.byte_offset // 0) + 1);

def typos_end_col:
  (typos_start_col + ((.typo // "") | length));

def typos_replace_suggestion:
  if (.corrections | length) > 0 then
    [{
      range: {
        start: {line: (.line_num // 1), column: typos_start_col},
        end: {line: (.line_num // 1), column: typos_end_col}
      },
      text: .corrections[0]
    }]
  else
    []
  end;
