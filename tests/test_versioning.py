from src.papers.versioning import classify_version


def test_arxiv_labeled_preprint():
    p = {"title": "Test", "venue": "arXiv", "url": "https://arxiv.org/abs/1234.5678", "externalIds": {}}
    v, _ = classify_version(p)
    assert v == "preprint"


def test_doi_and_venue_likely_published():
    p = {"title": "Test", "venue": "CVPR", "url": "https://example.com", "externalIds": {"DOI": "10.1000/test"}}
    v, _ = classify_version(p)
    assert v in {"published", "conference", "journal"}

