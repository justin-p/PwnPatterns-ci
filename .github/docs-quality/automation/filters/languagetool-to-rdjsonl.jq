# languagetool.json (batch output) -> reviewdog rdjsonl
include "paths";
include "languagetool-message";

[
  .[]?
  | .file as $raw
  | resolve_path($raw) as $path
  | (.matches[]?
    | {
        message: lt_rdjsonl_message,
        location: {
          path: $path,
          range: {
            start: {
              line: (.line // 1),
              column: (.column // 1)
            },
            end: {
              line: (.end_line // .line // 1),
              column: (.end_column // ((.column // 1) + (.length // 0)))
            }
          }
        },
        suggestions: lt_replace_suggestion,
        severity: (
          (.rule.issueType // "" | ascii_downcase) as $t
          | if $t == "misspelling" or $t == "grammar" then "ERROR" else "WARNING" end
        )
      }
    )
]
| .[]
| @json
