# typos --format json (JSONL) -> reviewdog rdjsonl; input is a JSON array of typo records
include "paths";
include "typos-message";

[
  .[]?
  | select(.type == "typo")
  | resolve_path(.path // "") as $path
  | select($path != "")
  | {
      message: typos_rdjsonl_message,
      location: {
        path: $path,
        range: {
          start: {
            line: (.line_num // 1),
            column: typos_start_col
          },
          end: {
            line: (.line_num // 1),
            column: typos_end_col
          }
        }
      },
      suggestions: typos_replace_suggestion,
      severity: "ERROR"
    }
]
| .[]
| @json
