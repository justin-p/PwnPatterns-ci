# Helpers for lychee to-rdjsonl.jq (reviewdog PR comments).
include "message-parts";

def lychee_url($body):
  ($body.url // $body.uri // "unknown URL") | tostring;

def lychee_status($body):
  ($body.status.text // $body.status.details // "link check failed") | tostring;

def lychee_code($body):
  ($body.status.code // 0) | tostring;

def lychee_context($body):
  ($body.status.code // 0) as $code
  | if $code == 404 then
      "Link returned 404 — update URL, remove the link, or archive reference."
    elif $code == 403 then
      "Link returned 403 — may be blocked from CI; check lychee 403 filter policy."
    elif $code == 0 then
      "Request failed (timeout or connection error)."
    else
      "Verify the URL is reachable and still correct for this document."
    end;

def lychee_rdjsonl_message($body):
  [
    "[lychee] Broken link: «" + lychee_url($body) + "»",
    "Status: " + lychee_code($body) + " " + lychee_status($body),
    lychee_context($body)
  ]
  | message_join;
