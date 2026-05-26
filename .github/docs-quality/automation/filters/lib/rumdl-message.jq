# Helpers for rumdl-to-rdjsonl.jq (reviewdog PR comments).
include "message-parts";

def rumdl_context:
  if (.rule // "") == "MD031" then
    "Markdown: leave a blank line after closing ``` fences."
  elif (.rule // "") == "MD012" then
    "Markdown: remove consecutive blank lines between sections."
  elif (.rule // "") == "MD041" then
    "Markdown: the first line should be a single # heading."
  else
    empty
  end;

def rumdl_rdjsonl_message:
  [
    "[rumdl] " + (.rule // "rumdl") + ": " + (.message // "Markdown lint"),
    (if .fixable == true then "Auto-fixable: run rumdl check --fix locally." else empty end),
    rumdl_context
  ]
  | message_join;
