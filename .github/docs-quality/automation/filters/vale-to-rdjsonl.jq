# vale --output=JSON -> reviewdog rdjsonl (error-level alerts only; matches CI fail policy)
# Vale Span[0] is 1-based start column; Span[1] is exclusive 0-based end index on the line.
include "paths";
include "vale-message";

def span_start_col: (.Span[0] // 1);
def span_end_col: ((.Span[1] // 0) + 1);

def replace_suggestion:
  if ((.Action.Name // "") | ascii_downcase) == "replace"
     and ((.Action.Params // []) | length) > 0
  then [{
    range: {
      start: {line: (.Line // 1), column: span_start_col},
      end: {line: (.Line // 1), column: span_end_col}
    },
    text: .Action.Params[0]
  }]
  else []
  end;

[
  to_entries[]
  | .key as $raw
  | resolve_path($raw) as $path
  | .value[]?
  | select((.Severity // "") | ascii_downcase == "error")
  | {
      message: vale_rdjsonl_message,
      location: {
        path: $path,
        range: {
          start: {line: (.Line // 1), column: span_start_col},
          end: {line: (.Line // 1), column: span_end_col}
        }
      },
      suggestions: replace_suggestion,
      severity: "ERROR"
    }
]
| .[]
| @json
