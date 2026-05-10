from src.papers.query_expansion import expand_queries


def test_expand_queries_returns_deduped_list():
    topic = "Privacy-preserving vision-based fall detection for elderly care"
    queries = expand_queries(topic, max_queries=8)
    assert isinstance(queries, list)
    assert 4 <= len(queries) <= 8
    assert len(set(q.lower() for q in queries)) == len(queries)
    assert queries[0].lower().startswith("privacy")

