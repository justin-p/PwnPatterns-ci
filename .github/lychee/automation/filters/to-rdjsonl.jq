# lychee --format json -> reviewdog rdjsonl (one diagnostic per line).
# Pinned for lychee v0.24.x (error_map keys are file paths; values are link result arrays).
include "lychee-message";

def link_range($body):
  ($body.span.line // 1) as $line
  | ($body.span.column // 1) as $col
  | (($body.url // $body.uri // "") | length) as $len
  | {
      start: {line: $line, column: $col},
      end: {
        line: $line,
        column: ($col + (if $len > 0 then $len else 1 end))
      }
    };

def link_diag($path; $body):
  {
    source: {name: "lychee"},
    severity: "ERROR",
    message: lychee_rdjsonl_message($body),
    location: {
      path: $path,
      range: link_range($body)
    }
  };

def map_diags($map):
  ($map // {})
  | to_entries[]
  | .key as $path
  | (.value | if type == "array" then .[] else . end)
  | link_diag($path; .);

[
  .error_map // .fail_map // {},
  .timeout_map // {}
]
| .[]
| map_diags(.)
| @json
