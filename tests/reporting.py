"""Write LLM prompt test reports to timestamped files under tests/results/."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class LlmCallResult:
    user_message: str
    prompt: str
    raw_response: str

    def parsed_json(self, today=None) -> dict:
        from llm_parse import parse_llm_json

        return parse_llm_json(self.raw_response, today=today)


def _separator(char: str = "=", width: int = 72) -> str:
    return char * width


def format_case_report(
    case_id: str,
    result: LlmCallResult,
    *,
    passed: bool,
    run_at: datetime,
    errors: Optional[List[str]] = None,
    routing_summary: Optional[str] = None,
) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "",
        _separator(),
        f"CASE: {case_id}  [{status}]",
        f"RUN AT: {run_at.strftime('%Y-%m-%d %H:%M:%S')}",
        _separator(),
        "USER MESSAGE:",
        result.user_message,
        "",
        "PROMPT SENT TO LLM:",
        _separator("-"),
        result.prompt,
        _separator("-"),
        "",
        "LLM RAW RESPONSE:",
        _separator("-"),
        result.raw_response,
        _separator("-"),
        "",
    ]

    try:
        parsed = result.parsed_json()
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
        lines.extend(["PARSED JSON:", pretty, ""])
    except json.JSONDecodeError:
        lines.append("PARSED JSON: <invalid — could not parse>")
        lines.append("")

    if routing_summary:
        lines.extend(["ROUTING:", routing_summary, ""])

    if errors:
        lines.append("FAILURES:")
        lines.extend(f"  - {err}" for err in errors)

    lines.append(_separator())
    lines.append("")

    return "\n".join(lines)


class ResultsWriter:
    """One timestamped report file per test session."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.path: Optional[Path] = None
        self.started_at: Optional[datetime] = None

    def _ensure_initialized(self) -> None:
        if self.path is not None:
            return
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.started_at = datetime.now()
        stamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        self.path = self.results_dir / f"prompt-test_{stamp}.txt"
        header = "\n".join(
            [
                _separator(),
                "INTEX PROMPT REGRESSION TEST REPORT",
                f"STARTED: {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"FILE: {self.path.name}",
                _separator(),
                "",
            ]
        )
        self.path.write_text(header, encoding="utf-8")

    def append_case(
        self,
        case_id: str,
        result: LlmCallResult,
        *,
        passed: bool,
        errors: Optional[List[str]] = None,
        routing_summary: Optional[str] = None,
    ) -> None:
        self._ensure_initialized()
        run_at = datetime.now()
        body = format_case_report(
            case_id,
            result,
            passed=passed,
            run_at=run_at,
            errors=errors,
            routing_summary=routing_summary,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(body)

    def terminal_line(self, case_id: str, passed: bool) -> str:
        self._ensure_initialized()
        status = "PASSED" if passed else "FAILED"
        return f"{status} {case_id}  (details → {self.path})"
