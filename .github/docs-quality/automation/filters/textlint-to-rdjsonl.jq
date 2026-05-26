# textlint --format json -> reviewdog rdjsonl
include "paths";
include "textlint-message";

[
  .[]?
  | .filePath as $raw
  | resolve_path($raw) as $path
  | (.messages[]?
    | {
        message: textlint_rdjsonl_message,
        location: {
          path: $path,
          range: {
            start: {
              line: (.line // 1),
              column: (.column // 1)
            },
            end: {
              line: (.line // 1),
              column: ((.column // 1) + (((.fix.range[1] // .fix.range[0] // .column // 1) - (.fix.range[0] // .column // 1)) // 1))
            }
          }
        },
        suggestions: (
          (.fix.text // "") as $s
          | if $s != "" then [{text: $s}] else [] end
        ),
        severity: "ERROR"
      }
    )
]
| .[]
| @json

