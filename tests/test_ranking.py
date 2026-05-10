from src.papers.ranking import rank_and_select_papers


def test_ranking_dedupes_by_doi():
    topic = "fall detection privacy computer vision"
    papers = [
        {"title": "A", "abstract": "fall detection", "year": 2024, "citationCount": 10, "venue": "CVPR", "externalIds": {"DOI": "10.1/abc"}, "openAccessPdf": {"url": "x"}},
        {"title": "B", "abstract": "fall detection", "year": 2024, "citationCount": 20, "venue": "CVPR", "externalIds": {"DOI": "10.1/abc"}, "openAccessPdf": {"url": "x"}},
    ]
    out = rank_and_select_papers(topic, papers, top_n=10)
    assert len(out) == 1


def test_ranking_prefers_pdf_available():
    topic = "fall detection privacy computer vision"
    papers = [
        {"title": "No PDF", "abstract": "fall detection privacy", "year": 2024, "citationCount": 10, "venue": "CVPR", "externalIds": {"DOI": "10.1/nopdf"}},
        {"title": "With PDF", "abstract": "fall detection privacy", "year": 2024, "citationCount": 10, "venue": "CVPR", "externalIds": {"DOI": "10.1/pdf"}, "openAccessPdf": {"url": "http://example.com/p.pdf"}},
    ]
    out = rank_and_select_papers(topic, papers, top_n=2)
    assert out[0]["title"] == "With PDF"

