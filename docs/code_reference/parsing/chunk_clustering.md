# Chunk Clustering

Chunk clustering is a post processing technique to clump together chunks that are similar to each other according to Semantic Similarity. This is useful when you want chunks that cut whenever the topic changes rather than at a fixed length. We used a combined approach that targets a particular chunk size (in tokens) and then also factors in semantic leap from one sentence to another.

::: redbox.parsing.chunk_clustering.cluster_chunks

::: redbox.parsing.chunk_clustering.create_pdist

::: redbox.parsing.chunk_clustering.merge_chunk_metadata