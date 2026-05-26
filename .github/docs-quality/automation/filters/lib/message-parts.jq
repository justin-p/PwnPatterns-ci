# Shared reviewdog message formatting: join non-empty parts with " — ".
def message_join:
  map(select(. != null and (type == "string") and length > 0))
  | join(" — ");
