from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True)
class Finding:
    tool: str
    path: str
    line: int
    column: int
    severity: str
    message: str
    rule: str | None = None
    fixable: bool = False

    def sort_key(self) -> tuple[str, int, int, str]:
        return (self.path, self.line, self.column, self.tool)


@dataclass
class StepResult:
    name: str
    status: StepStatus
    duration_ms: int = 0
    log_path: str | None = None
    detail: str | None = None


@dataclass
class FileFindings:
    path: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.findings)


@dataclass
class CheckReport:
    schema_version: int = 1
    command: str = "check"
    options: dict[str, Any] = field(default_factory=dict)
    steps: list[StepResult] = field(default_factory=list)
    files: list[FileFindings] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.status != StepStatus.FAIL for s in self.steps)

    @property
    def failed_steps(self) -> list[StepResult]:
        return [s for s in self.steps if s.status == StepStatus.FAIL]

    def failure_summary(self) -> str | None:
        """Short description of failed pipeline steps (for UI when findings are empty)."""
        failed = self.failed_steps
        if not failed:
            return None
        parts: list[str] = []
        for step in failed:
            if step.detail:
                parts.append(f"{step.name} ({step.detail})")
            else:
                parts.append(step.name)
        return ", ".join(parts)

    def all_findings(self) -> list[Finding]:
        out: list[Finding] = []
        for ff in self.files:
            out.extend(ff.findings)
        return out


def group_findings_by_file(findings: list[Finding]) -> list[FileFindings]:
    by_path: dict[str, list[Finding]] = {}
    for f in findings:
        by_path.setdefault(f.path, []).append(f)
    result: list[FileFindings] = []
    for path in sorted(by_path):
        items = sorted(by_path[path], key=lambda x: (x.line, x.column, x.tool))
        result.append(FileFindings(path=path, findings=items))
    result.sort(key=lambda ff: (-ff.count, ff.path))
    return result
