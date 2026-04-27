"""Persist screenshots and raw page text for later debugging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import settings


class EvidenceService:
    """Manage per-scan evidence folders on disk."""

    def __init__(self, evidence_root: Path | None = None) -> None:
        """Choose the evidence directory root."""
        self.evidence_root = evidence_root or settings.evidence_dir
        self.evidence_root.mkdir(parents=True, exist_ok=True)

    def build_workspace_dir(self, account_id: str, run_id: str, workspace_slug: str) -> Path:
        """Create and return a deterministic evidence directory for one workspace."""
        safe_slug = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in workspace_slug)
        target = self.evidence_root / account_id / run_id / safe_slug
        target.mkdir(parents=True, exist_ok=True)
        return target

    def write_text(self, target_dir: Path, filename: str, content: str) -> str:
        """Write a UTF-8 text artifact and return its path."""
        path = target_dir / filename
        path.write_text(content, encoding="utf-8")
        return str(path)

    def write_json(self, target_dir: Path, filename: str, payload: dict[str, Any]) -> str:
        """Write JSON evidence and return its path."""
        path = target_dir / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
