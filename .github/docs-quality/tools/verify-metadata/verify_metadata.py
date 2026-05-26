import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


# Constants
class MetadataConfig:
    BASE_REQUIRED_FIELDS: Set[str] = {
        "metadata_version",
        "pattern_template_version",
        "title",
        "id",
        "category",
        "type",
        "tags",
        "severity",
        "created",
        "updated",
        "author",
        "status",
    }

    V002_ADDITIONAL_FIELDS: Set[str] = {
        "pattern_revision",
        "language",
        "translations",
    }

    VALID_LANGUAGES: Set[str] = {"en", "nl"}
    VALID_SEVERITIES: Set[str] = {"critical", "high", "medium", "low", "info", "n.a."}
    VALID_STATUSES: Set[str] = {"draft", "published", "archived"}

    DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    VERSION_REGEX = re.compile(r"^\d+\.\d+\.\d+$")

    @classmethod
    def get_required_fields(cls, version: str) -> Set[str]:
        """Get required fields based on metadata version."""
        if version == "0.0.2":
            return cls.BASE_REQUIRED_FIELDS | cls.V002_ADDITIONAL_FIELDS
        return cls.BASE_REQUIRED_FIELDS


class MetadataError(Exception):
    """Custom exception for metadata validation errors."""

    pass


def repo_root() -> Path:
    """Consumer repository root (pattern docs live here, not under pwnpatterns-ci/)."""
    if env := os.environ.get("REPO_ROOT"):
        return Path(env).resolve()
    here = Path(__file__).resolve()
    root = here.parents[4]
    if root.name == "pwnpatterns-ci":
        return here.parents[5]
    return root


class MetadataValidator:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.repo_root = repo_root()
        self.full_path = self.repo_root / file_path
        self.metadata: Dict = {}

    def validate(self) -> Dict:
        """Main validation method."""
        self._check_file_exists()
        self._extract_metadata_raw()
        self._validate_required_fields()
        self._process_metadata()
        self._validate_fields()
        return self.metadata

    def _check_file_exists(self) -> None:
        """Check if the file exists."""
        if not self.full_path.exists():
            raise MetadataError(f"File not found: {self.full_path}")

    def _extract_metadata_raw(self) -> None:
        """Extract raw metadata from markdown file without processing."""
        content = self.full_path.read_text(encoding="utf-8")
        metadata_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)

        if not metadata_match:
            raise MetadataError(
                'No metadata section found (must start with "---" and end with "---")'
            )

        # Only do basic extraction without processing
        frontmatter = metadata_match.group(1)
        for line in frontmatter.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue

            key, *value_parts = line.split(":", 1)
            key = key.strip()
            value = ":".join(value_parts).strip()

            self.metadata[key] = value.strip("\"'")

    def _process_metadata(self) -> None:
        """Process and transform metadata after validation."""
        # Process special fields after required fields are validated
        processed_metadata = {}
        for key, value in self.metadata.items():
            if key == "tags":
                processed_metadata[key] = self._process_tags(value)
            elif self._is_translation_id(key):
                # Skip translation IDs - they'll be handled separately
                continue
            else:
                processed_metadata[key] = value

        self.metadata = processed_metadata
        self._process_translations()

    def _process_translations(self) -> None:
        """Process translation IDs after main metadata is processed."""
        if "translations" not in self.metadata:
            self.metadata["translations"] = {"translatedIds": {}}

    def _validate_required_fields(self) -> None:
        """Validate required fields are present."""
        version = self.metadata.get("metadata_version", "0.0.1")
        required_fields = MetadataConfig.get_required_fields(version)
        missing_fields = required_fields - set(self.metadata.keys())

        if missing_fields:
            raise MetadataError(f'Missing fields: {", ".join(sorted(missing_fields))}')

    def _validate_fields(self) -> None:
        """Validate field values."""
        self._validate_version_format("metadata_version")
        self._validate_version_format("pattern_template_version")
        self._validate_version_format("pattern_revision")
        self._validate_status()
        for field in ["created", "updated"]:
            if field in self.metadata:
                self._validate_date(field)

        if self.metadata.get("metadata_version") == "0.0.2":
            self._validate_language()

    def _validate_version_format(self, field: str) -> None:
        """Validate version format for a field."""
        if not MetadataConfig.VERSION_REGEX.match(self.metadata[field]):
            raise MetadataError(
                f'Invalid {field} format: "{self.metadata[field]}" '
                "(must be semver format x.y.z)"
            )

    def _validate_date(self, field: str) -> None:
        """Validate a date field."""
        date_str = self.metadata[field]
        if not MetadataConfig.DATE_REGEX.match(date_str):
            raise MetadataError(
                f'Invalid {field} date: "{date_str}" (must be in YYYY-MM-DD format)'
            )
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise MetadataError(f'Invalid {field} date: "{date_str}"')

    def _validate_dates(self) -> None:
        """Validate date fields."""
        for field in ["created", "updated"]:
            self._validate_date(field)

    def _validate_severity(self) -> None:
        """Validate severity field."""
        if self.metadata["severity"] not in MetadataConfig.VALID_SEVERITIES:
            raise MetadataError(
                f'Invalid severity value: "{self.metadata["severity"]}" '
                f'(must be one of: {", ".join(MetadataConfig.VALID_SEVERITIES)})'
            )

    def _validate_status(self) -> None:
        """Validate status field."""
        if self.metadata["status"] not in MetadataConfig.VALID_STATUSES:
            raise MetadataError(
                f'Invalid status value: "{self.metadata["status"]}" '
                f'(must be one of: {", ".join(MetadataConfig.VALID_STATUSES)})'
            )

    def _validate_language(self) -> None:
        """Validate language field."""
        if self.metadata["language"] not in MetadataConfig.VALID_LANGUAGES:
            raise MetadataError(
                f'Invalid language value: "{self.metadata["language"]}" '
                f'(must be one of: {", ".join(MetadataConfig.VALID_LANGUAGES)})'
            )

    def _process_tags(self, value: str) -> List:
        """Process tags field."""
        try:
            tags = json.loads(value.replace("'", '"'))
            if not isinstance(tags, list):
                raise MetadataError("Tags must be an array")
            return tags
        except json.JSONDecodeError as e:
            raise MetadataError(f"Invalid tags format: {str(e)}")

    def _is_translation_id(self, key: str) -> bool:
        """Check if key is a translation ID."""
        return (
            key.startswith('"')
            and key.endswith('"')
            and self.metadata.get("metadata_version") == "0.0.2"
        )


def get_all_markdown_files() -> List[str]:
    """Get all markdown files in the docs directory."""
    try:
        root = repo_root()
        docs_dir = root / "docs"

        if not docs_dir.exists():
            print(f"Error: Docs directory not found at {docs_dir}", file=sys.stderr)
            return []

        return sorted(str(p.relative_to(root)) for p in docs_dir.rglob("*.md"))
    except Exception as e:
        print(f"Error finding markdown files: {e}", file=sys.stderr)
        return []


def _progress(message: str) -> None:
    if os.environ.get("DOCS_DEV_PROGRESS"):
        print(message, file=sys.stderr, flush=True)


def check_duplicate_ids(files: List[str]) -> List[str]:
    """Check for duplicate IDs across all pattern docs (single pass)."""
    errors: List[str] = []
    id_map: Dict[str, str] = {}
    targets = set(files)
    all_md = get_all_markdown_files()
    to_scan = sorted(targets | (set(all_md) - targets))
    total = len(to_scan)
    if total:
        _progress(f"Checking duplicate IDs across {total} doc(s)…")

    for index, file in enumerate(to_scan, start=1):
        if index == 1 or index % 25 == 0 or index == total:
            _progress(f"metadata duplicate IDs {index}/{total}")
        try:
            metadata = MetadataValidator(file).validate()
        except Exception:
            continue
        doc_id = metadata.get("id")
        if not doc_id:
            continue
        if doc_id in id_map:
            errors.append(
                f'❌ Duplicate ID found: "{doc_id}" in files:\n'
                f"   - {id_map[doc_id]}\n"
                f"   - {file}"
            )
        else:
            id_map[doc_id] = file

    return errors


def rdjsonl_message(summary: str, *, path: str = "", hint: str = "") -> str:
    """Format a reviewdog comment with optional file context and fix guidance."""
    parts = [f"[metadata] {summary}"]
    if path:
        parts.append(f"File: {path}")
    if hint:
        parts.append(hint)
    return " — ".join(parts)


def diagnostics_from_error(error: str) -> list[dict]:
    """Turn a human-readable error into reviewdog rdjsonl diagnostics."""
    lines = [ln for ln in error.strip().splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("❌ "):
        return []

    first = lines[0][2:].strip()
    if first.startswith("Duplicate ID"):
        summary = first
        hint = "Assign a unique pattern id in frontmatter; see other files listed below."
        diags = []
        for line in lines[1:]:
            path = line.strip().lstrip("-").strip()
            if path.startswith("docs/") and path.endswith(".md"):
                diags.append(
                    {
                        "message": rdjsonl_message(summary, path=path, hint=hint),
                        "location": {
                            "path": path,
                            "range": {"start": {"line": 1, "column": 1}},
                        },
                        "severity": "ERROR",
                    }
                )
        return diags

    if ": " in first:
        path, detail = first.split(": ", 1)
        return [
            {
                "message": rdjsonl_message(
                    detail,
                    path=path,
                    hint="Fix YAML frontmatter at the top of this pattern file.",
                ),
                "location": {
                    "path": path,
                    "range": {"start": {"line": 1, "column": 1}},
                },
                "severity": "ERROR",
            }
        ]

    return []


def emit_rdjsonl(errors: list[str]) -> None:
    for error in errors:
        for diag in diagnostics_from_error(error):
            print(json.dumps(diag), flush=True)


def main() -> int:
    """Main function to validate metadata and check for duplicate IDs."""
    parser = argparse.ArgumentParser(description="Validate pattern document metadata")
    parser.add_argument(
        "--rdjsonl",
        action="store_true",
        help="Print reviewdog rdjsonl diagnostics to stdout (human errors on stderr)",
    )
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    files = [f for f in args.files if f.startswith("docs/") and f.endswith(".md")]
    if not files:
        return 0

    errors = []

    total = len(files)
    for index, file in enumerate(files, start=1):
        if index == 1 or index % 10 == 0 or index == total:
            _progress(f"metadata validate {index}/{total}: {file}")
        try:
            MetadataValidator(file).validate()
        except MetadataError as e:
            errors.append(f"❌ {file}: {str(e)}")
        except Exception as e:
            errors.append(f"❌ {file}: Unexpected error: {str(e)}")

    errors.extend(check_duplicate_ids(files))

    if errors:
        if args.rdjsonl:
            emit_rdjsonl(errors)
        print("\nValidation Errors:", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
