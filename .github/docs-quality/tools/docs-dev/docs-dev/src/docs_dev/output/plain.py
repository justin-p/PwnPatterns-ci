from __future__ import annotations

from docs_dev.models import CheckReport, StepStatus


def render_plain(report: CheckReport) -> str:
    lines: list[str] = []
    lines.append(f"command: {report.command}")
    lines.append(f"passed: {report.passed}")
    lines.append("")
    lines.append("steps:")
    for step in report.steps:
        mark = {"pass": "ok", "fail": "FAIL", "skip": "skip"}[step.status.value]
        lines.append(f"  [{mark}] {step.name}")
    lines.append("")
    for ff in report.files:
        for f in ff.findings:
            lines.append(
                f"{f.path}:{f.line}:{f.column}:{f.tool}: {f.message}"
            )
    if not report.files:
        lines.append("(no findings)")
    return "\n".join(lines) + "\n"
