from redbox.parsing.chunk_clustering import compute_embed_dist, compute_token_dist, create_pdist


def test_compute_embed_dist():
    pair_embed_dist = [0.1, 0.3, 0.2, 0.4]
    actual = compute_embed_dist(pair_embed_dist)
    assert list(actual) == [0.3, 0.3, 0.4, 0.2, 0.4, 0.4]


def test_compute_token_dist():
    token_counts = [10, 30, 20, 40]
    actual = compute_token_dist(token_counts)
    assert list(actual) == [40, 60, 100, 50, 90, 60]


def test_create_pdist():
    token_counts = [10, 30, 20, 40]
    pair_embed_dist = [0.1, 0.3, 0.2, 0.4]
    actual = create_pdist(token_counts, pair_embed_dist, 0.2, False)
    assert list(actual) == [32.06, 48.06, 80.08, 40.04, 72.08, 48.08]
