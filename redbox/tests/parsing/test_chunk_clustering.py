from redbox.parsing.chunk_clustering import compute_embed_dist, create_pdist


def test_compute_embed_dist():
    pair_embed_dist = [-1, -0.5, 0, +0.5, 1]
    actual = compute_embed_dist(pair_embed_dist)
    assert list(actual) == [0.5, 0.5, 0.5, 1.0, 0.0, 0.5, 1.0, 0.5, 1.0, 1.0]


def test_create_pdist():
    token_counts = [10, 10, 10, 10, 10]
    pair_embed_dist = [-1, -0.5, 0, +0.5, 1]
    actual = create_pdist(token_counts, pair_embed_dist, 0.2, False)
    assert list(actual) == [16.1, 24.1, 32.1, 40.2, 16.0, 24.1, 32.2, 16.1, 24.2, 16.2]
