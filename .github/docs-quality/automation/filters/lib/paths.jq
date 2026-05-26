# Shared path resolution for reviewdog rdjsonl filters.
# Requires: --argjson path_index '{"basename.md":"docs/.../basename.md"}'
# Optional: --arg repo_root "${GITHUB_WORKSPACE}" to strip absolute CI paths.
def paths_idx:
  ($path_index // {});

def repo_root_prefix:
  ($repo_root // "")
  | if length == 0 then ""
    elif endswith("/") then .
    else . + "/"
    end;

def strip_repo_root($p):
  (repo_root_prefix) as $root
  | if ($root | length) > 0 and ($p | startswith($root)) then
      ($p | .[$root | length:] | if startswith("/") then .[1:] else . end)
    else
      $p
    end;

def resolve_path($p):
  if ($p | type) != "string" or $p == "" then
    $p
  else
    strip_repo_root($p) as $rel
    | if ($rel | contains("/")) then $rel
      else paths_idx[$rel] // $rel
      end
  end;
