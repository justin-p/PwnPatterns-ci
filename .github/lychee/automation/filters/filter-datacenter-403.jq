# Filter lychee JSON: drop errors that are HTTP 403 on configured CI hosts only.
# Args: --slurpfile hosts <json array of hostnames>
# Recalculates .errors and sets .datacenter_403_suppressed.

def url_host:
  (.url // .uri // "")
  | if test("^https?://") then
      capture("^https?://(?<h>[^/?#]+)") | .h | ascii_downcase
    else
      null
    end;

def status_is_403:
  ((.status.code? // 0) == 403)
  or ((.status.text? // "") | test("403"));

def suppressible_403($hosts):
  url_host as $h
  | $h != null
  and (any($hosts[]; . == $h))
  and status_is_403;

def map_links($map):
  ($map // {})
  | [to_entries[] | .value | if type == "array" then .[] else . end];

def count_suppressed($map; $hosts):
  map_links($map) | map(select(suppressible_403($hosts))) | length;

def filter_link_map($map; $hosts):
  ($map // {})
  | with_entries(
      .value |= (
        if type == "array" then
          [ .[] | select(suppressible_403($hosts) | not) ]
        else
          [ . | select(suppressible_403($hosts) | not) ]
        end
      )
    )
  | with_entries(select(.value | length > 0));

def count_errors($map):
  map_links($map) | length;

($hosts[0] // []) as $hostlist
| (count_suppressed(.error_map; $hostlist)
   + count_suppressed(.fail_map; $hostlist)) as $suppressed
| .error_map = filter_link_map(.error_map; $hostlist)
| .fail_map = filter_link_map(.fail_map; $hostlist)
| .errors = (count_errors(.error_map) + count_errors(.timeout_map))
| .datacenter_403_suppressed = $suppressed
