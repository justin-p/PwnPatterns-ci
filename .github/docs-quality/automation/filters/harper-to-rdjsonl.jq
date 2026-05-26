# harper-cli lint --format json -> reviewdog rdjsonl (blocking lints only; full paths)
include "paths";
include "harper-message";

($blocking // 127 | if type == "string" then tonumber else . end) as $min_prio
| [
    .[]?
    | .file as $base
    | resolve_path($base) as $path
    | (.lints[]?
        | select((.priority // 0) >= $min_prio)
        | {
            message: harper_rdjsonl_message,
            location: {
              path: $path,
              range: {
                start: {
                  line: (.line // 1),
                  column: (.column // 1)
                },
                end: {
                  line: (.line // 1),
                  column: ((.column // 1) + ((.matched_text // "") | length))
                }
              }
            },
            suggestions: harper_replace_suggestion,
            severity: "ERROR"
          }
      )
  ]
| .[]
| @json
