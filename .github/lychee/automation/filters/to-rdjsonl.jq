# lychee --format json -> reviewdog rdjsonl (one diagnostic per line).
# Pinned for lychee v0.24.x (error_map keys are file paths; values are link result arrays).
include "lychee-message";

def link_start($body):
  {
    line: ($body.span.line // 1),
    column: ($body.span.column // 1)
  };

def link_diag($path; $body):
  {
    source: {name: "lychee"},
    severity: "ERROR",
    message: lychee_rdjsonl_message($body),
    location: {
      path: $path,
      range: {start: link_start($body)}
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
