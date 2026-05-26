# rumdl check --output json -> reviewdog rdjsonl (one diagnostic per line)
include "paths";
include "rumdl-message";

[
  .[]?
  | resolve_path(.file // "") as $path
  | select($path != "")
  | {
      message: rumdl_rdjsonl_message,
      location: {
        path: $path,
        range: {
          start: {
            line: (.line // 1),
            column: (.column // 1)
          }
        }
      },
      severity: (if .severity == "error" then "ERROR" else "WARNING" end)
    }
]
| .[]
| @json
