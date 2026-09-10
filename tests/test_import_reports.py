import hashlib
import json

import pytest

from webapp.import_reports import import_reports
from webapp.service import JobStore


def test_local_import_preserves_bytes_and_deduplicates(tmp_path):
    folder = tmp_path / "reports" / "ABCL_20260909_233053"
    (folder / "5_portfolio").mkdir(parents=True)
    original = "# 분석 원문\r\nTotal tokens: 336,687\r\n".encode()
    (folder / "complete_report.md").write_bytes(original)
    (folder / "5_portfolio/decision.md").write_text("Rating: Hold", encoding="utf-8")
    store = JobStore(tmp_path / "store")
    try:
        assert import_reports(store, folders=[folder]) == 1
        job = store.list()[0]
        assert job["config"]["date"] == "2026-09-09"
        assert job["config"]["provider"] == "Local reports"
        assert job["status"] == "imported"
        assert job["signal"] == "Hold"
        assert job["revision"] is None
        assert job["source"] == str(folder / "complete_report.md")
        capture = store.root / job["id"] / "source"
        assert (capture / "complete_report.md").read_bytes() == original
        provenance = json.loads((capture / "provenance.json").read_text())
        assert provenance["sha256"]["complete_report.md"] == hashlib.sha256(original).hexdigest()
        assert import_reports(store, folders=[folder]) == 0
        (folder / "complete_report.md").write_bytes(original + b"Updated\n")
        assert import_reports(store, folders=[folder]) == 1
        assert len(store.list()) == 2
        assert (capture / "complete_report.md").read_bytes() == original
        store.delete_report(job["id"])
        with pytest.raises(KeyError):
            store.get(job["id"])
        archived = json.loads(store.db.execute(
            "SELECT body FROM trashed_jobs WHERE id=?", (job["id"],)
        ).fetchone()[0])
        assert archived == job
        assert (capture / "complete_report.md").read_bytes() == original
        store.save({"id": "running", "status": "running"})
        with pytest.raises(ValueError, match="가져온 보고서"):
            store.delete_report("running")
    finally:
        store.close()


def test_local_import_validates_all_paths_before_writing(tmp_path):
    folder = tmp_path / "ORCL_20260826"
    folder.mkdir()
    (folder / "complete_report.md").write_text("Original", encoding="utf-8")
    store = JobStore(tmp_path / "store")
    try:
        with pytest.raises(ValueError, match="Missing report"):
            import_reports(store, folders=[folder, tmp_path / "missing"])
        assert store.list() == []
    finally:
        store.close()
