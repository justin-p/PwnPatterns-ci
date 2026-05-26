# Shared path resolution for reviewdog rdjsonl filters.
# Requires: --argjson path_index '{"basename.md":"docs/.../basename.md"}'
def paths_idx:
  ($path_index // {});

def resolve_path($p):
  if ($p | type) != "string" or $p == "" then
    $p
  elif ($p | contains("/")) then
    $p
  else
    paths_idx[$p] // $p
  end;
