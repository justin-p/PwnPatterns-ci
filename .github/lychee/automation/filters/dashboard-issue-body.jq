# Build a compact GitHub issue body from lychee --format json (v0.24.x).
# Args: --arg repo <owner/name> --arg ref <branch> --arg rerun <url> --arg outcome success|failure

def md_cell:
  tostring | gsub("\\|"; "\\|") | gsub("\r?\n"; " ");

def link_url($body):
  ($body.url // $body.uri // "—") | tostring;

def status_msg($body):
  ($body.status.text // $body.status.details // "—") | tostring | md_cell;

def file_line($body):
  ($body.span.line // 1) | tostring;

def file_cell($repo; $ref; $path; $line):
  ($path | split("/") | last) as $name
  | "[\($name | md_cell)](https://github.com/\($repo)/blob/\($ref)/\($path)#L\($line))";

def rows_from_map($map):
  ($map // {})
  | to_entries[]
  | .key as $path
  | (.value | if type == "array" then .[] else . end)
  | {
      link: link_url(.) | md_cell,
      status: status_msg(.),
      file_cell: file_cell($repo; $ref; $path; file_line(.))
    };

def problem_rows:
  [rows_from_map(.error_map // .fail_map // {})]
  + [rows_from_map(.timeout_map // {})];

def summary_lines:
  [
    "| Metric | Count |",
    "| --- | ---: |",
    "| Total | \(.total) |",
    "| OK | \(.successful) |",
    "| Errors | \(.errors) |",
    "| Timeouts | \(.timeouts) |",
    "| Redirects | \(.redirects) |",
    "| Excluded | \(.excludes) |"
  ];

def error_row_line($row):
  "| \($row.file_cell) | \($row.link) | \($row.status) |";

(problem_rows | length) as $problem_count
| if $outcome == "success" and $problem_count == 0 then
    (
        if ((.datacenter_403_suppressed // 0) | tonumber) > 0 then
          [
            "",
            "_CI ignored \(.datacenter_403_suppressed) datacenter `403` on hosts in `.github/lychee/config/ci-403-hosts.txt` (other responses on those hosts still fail)._",
            ""
          ]
        else
          []
        end
      ) as $ci_403_note
    | [
      "#### All links are valid",
      "",
      "Lychee completed successfully.",
      "",
      summary_lines[],
      $ci_403_note[],
      "",
      "[Re-run link check](\($rerun))"
    ]
  elif $problem_count == 0 then
    [
      "#### Link check finished",
      "",
      "No broken links were recorded in the report (workflow outcome: \($outcome)).",
      "",
      summary_lines[],
      "",
      "[Re-run link check](\($rerun))"
    ]
  else
    (
      problem_rows
      | if length > 150 then .[:150] else . end
    ) as $rows
    | (
        if ($problem_count > 150) then
          [
            "",
            "_Showing first 150 of \($problem_count) problem(s). See the [workflow run](\($rerun)) for the full lychee report._",
            ""
          ]
        else
          []
        end
      ) as $trunc_note
    | (
        if ((.datacenter_403_suppressed // 0) | tonumber) > 0 then
          [
            "",
            "_CI ignored \(.datacenter_403_suppressed) datacenter `403` on hosts in `.github/lychee/config/ci-403-hosts.txt` (other responses on those hosts still fail)._",
            ""
          ]
        else
          []
        end
      ) as $ci_403_note
    | [
        "#### Broken links found",
        "",
        "Lychee reported **\($problem_count)** broken or unreachable link(s) in `docs/`.",
        "",
        summary_lines[],
        $ci_403_note[],
        "",
        "| File | Link | Status |",
        "| --- | --- | --- |",
        ($rows[] | error_row_line(.)),
        $trunc_note[],
        "",
        "Please fix the links above.",
        "",
        "[Re-run link check](\($rerun))"
      ]
  end
| .[]
| @text
