from __future__ import annotations

import json
from typing import Any

from docs_dev.models import CheckReport, FileFindings, Finding, StepResult


def _finding_dict(f: Finding) -> dict[str, Any]:
    return {
        "tool": f.tool,
        "line": f.line,
        "column": f.column,
        "severity": f.severity,
        "message": f.message,
        "rule": f.rule,
        "fixable": f.fixable,
    }


def _file_dict(ff: FileFindings) -> dict[str, Any]:
    return {
        "path": ff.path,
        "findings": [_finding_dict(f) for f in ff.findings],
    }


def _step_dict(s: StepResult) -> dict[str, Any]:
    return {
        "name": s.name,
        "status": s.status.value,
        "duration_ms": s.duration_ms,
        "log_path": s.log_path,
        "detail": s.detail,
    }


def report_to_dict(report: CheckReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "command": report.command,
        "options": report.options,
        "summary": {
            "passed": report.passed,
            "steps": [_step_dict(s) for s in report.steps],
        },
        "files": [_file_dict(ff) for ff in report.files],
    }


def render_json(report: CheckReport, *, indent: int = 2) -> str:
    return json.dumps(report_to_dict(report), indent=indent)
