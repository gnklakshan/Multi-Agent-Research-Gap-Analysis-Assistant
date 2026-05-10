from pathlib import Path

import pytest

from src.papers.pdf_downloader import download_pdfs


class _Resp:
    def __init__(self, status_code=200, content_type="application/pdf"):
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def iter_content(self, chunk_size=1024):
        yield b"%PDF-1.4 test"


def test_failed_download_does_not_crash(monkeypatch, tmp_path: Path):
    def fake_get(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("requests.get", fake_get)

    papers = [
        {"title": "With PDF", "paperId": "x", "externalIds": {"DOI": "10.1/pdf"}, "openAccessPdf": {"url": "http://example.com/p.pdf"}},
    ]

    out = download_pdfs(papers, papers_dir=str(tmp_path / "papers"), metadata_path=str(tmp_path / "meta.json"))
    assert out[0]["downloaded"] is False
    assert out[0]["download_error"]


def test_success_download_writes_pdf(monkeypatch, tmp_path: Path):
    def fake_get(*args, **kwargs):
        return _Resp()

    monkeypatch.setattr("requests.get", fake_get)
    papers = [
        {"title": "With PDF", "paperId": "x", "externalIds": {"DOI": "10.1/pdf"}, "openAccessPdf": {"url": "http://example.com/p.pdf"}},
    ]
    out = download_pdfs(papers, papers_dir=str(tmp_path / "papers"), metadata_path=str(tmp_path / "meta.json"))
    assert out[0]["downloaded"] is True
    assert Path(out[0]["local_pdf_path"]).exists()

