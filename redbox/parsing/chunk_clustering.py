from collections.abc import Sequence
from functools import reduce
from itertools import compress

import numpy as np
import scipy
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from redbox.models.file import Chunk, Metadata


def cluster_chunks(
    chunks: Sequence[Chunk],
    embedding_model: SentenceTransformer,
    desired_chunk_size: int = 300,
    dist_weight_split: float = 0.2,
    dist_use_log: bool = True,
) -> Sequence[Chunk]:
    """Merge together adjacent chunks based on their semantic similarity (distance after sentence embedding)
    and length(token count)

    Args:
            chunks (List[File]): List of raw (small) chunks extracted from document.
            embedding_model (SentenceTransformer): name of the sentence embedding model used to compare chunk similarity
            desired_chunk_size (int): Average size of the output chunks. Defaults to 300,
            dist_weight_split (float): Expects value between 0 and 1.
                When calculating the combined distance metric this is the relative weight (importance)
                of the semantic similarity vs the token counts. Defaults to .2.
            dist_use_log (bool): When calculating the combined distance metric should the input values
                be scaled by log. Defaults to True.

    Returns:
            List[Chunk]: A list of all the (merged) chunks extracted from the given file.
    """
    # filter out empty chunks
    chunks = [chunk for chunk in chunks if chunk.token_count > 0]  # type: ignore
    if len(chunks) < 2:
        out_chunks = chunks
    else:
        token_counts = [chunk.token_count for chunk in chunks]  # type: ignore
        # calculate simple vector embedding and distances between adjacent chunks

        chunk_embedding = embedding_model.encode([chunk.text for chunk in chunks])

        pair_embed_dist = [0] + [
            scipy.spatial.distance.cosine(chunk_embedding[i], chunk_embedding[i + 1]) for i in range(len(chunks) - 1)
        ]
        # create distance vector (upper triangular) by combining the token counts with embedding distance
        dist_triu = create_pdist(
            token_counts=token_counts,
            pair_embed_dist=pair_embed_dist,
            weight_embed_dist=dist_weight_split,
            use_log=dist_use_log,
        )

        # cluster the small chunks and cut tree based on desired chunk size
        # Distance approach is Farthest Point Algorithm (complete linkage) which
        # gets the maximum distance between all the points in the cluster
        hc = scipy.cluster.hierarchy.linkage(dist_triu, "complete")
        num_clusters = round(np.sum(token_counts) / desired_chunk_size)  # type: ignore
        out_clusters = [lab[0] for lab in scipy.cluster.hierarchy.cut_tree(hc, n_clusters=num_clusters)]
        # merge clusters and create output chunks
        out_chunks = []
        for i, clust in enumerate(np.unique(out_clusters)):
            chunks_in = list(compress(chunks, out_clusters == clust))
            # if there is only one chunk in the cluster, just use it
            if len(chunks_in) == 1:
                new_chunk = chunks_in[0]
                new_chunk.index = i
            else:
                # if there are multiple chunks in the cluster, merge them
                new_chunk = Chunk(
                    parent_file_uuid=chunks_in[0].parent_file_uuid,
                    index=i,
                    text=" ".join([chunk.text for chunk in chunks_in]),
                    metadata=reduce(Metadata.merge, [chunk.metadata for chunk in chunks_in]),
                    creator_user_uuid=chunks_in[0].creator_user_uuid,
                )
            out_chunks.append(new_chunk)
    return out_chunks


def compute_embed_dist(pair_embed_dist: list[float]) -> NDArray[np.float64]:
    n = len(pair_embed_dist)
    # embedding distance between chunk i and j is taken as MAXIMUM of the pairwise embedding
    # distance of all the adjacent pairs between them

    embed_dims = np.tri(n, k=0) * np.array(pair_embed_dist)

    # Chebyshev distance is used to make sure that the distance between i and j is always
    # smaller than the distance between i and k and j and k for any k
    #
    # example:
    # suppose we have:
    #   pair_embed_dist = [.1, .3, .2, .4]
    #
    # we convert this into triangular matrix, called `embed_dims`:
    #   .1 .  .  .
    #   .1 .3 .  .
    #   .1 .3 .2 .
    #   .1 .3 .2 .4
    #
    # We now compute the Chebyshev Distance, d(i, j), between all rows of
    # `embed_dims` where i, j are the indices of the rows:
    #
    #   d(0, 1) d(0, 2) d(0, 3)
    #           d(1, 2) d(1, 3)
    #                   d(2, 3)
    #
    # The Chebyshev Distance function is (in pure python):
    # def d(i, j):
    #     result = max(abs(a-b) for a, b in zip(embed_dims[i], embed_dims[j]))
    #
    # So the embedding distances are:
    #        .3      .3      .4
    #                .2      .4
    #                        .4
    #
    # This is rewritten from left-to-bottom (to save space in memory)
    # [.3, .3, .4, .2, .4, .4]

    return scipy.spatial.distance.pdist(embed_dims, "chebyshev")


def compute_token_dist(token_counts: list[int]) -> NDArray[np.float64]:
    n = len(token_counts)

    # the token count distance between junk and i and j is the size of minimal text segment
    # containing them, i.e. sum of token counts of all the intermediate chunks
    token_dims = np.tri(n + 1, k=0) * np.array([0, *token_counts])

    # drop diagonal (sizes of individual chunks)
    a, b = np.triu_indices(n + 1, k=1)
    drop_ind = b - a > 1

    # calculate the token count distance between chunk i and j
    #
    # example:
    # suppose we have:
    #   token_counts = [10, 30, 20, 40]
    #
    # we convert this into triangular matrix, called `token_dims`:
    #   0,  0,  0,  0,  0
    #   0, 10,  0,  0,  0
    #   0, 10, 30,  0,  0
    #   0, 10, 30, 20,  0
    #   0, 10, 30, 20, 40
    #
    # We now compute the City-Block Distance, d(i, j), between all rows of
    # `token_dims` where i, j are the indices of the rows:
    #
    #   d(0, 1) d(0, 2) d(0, 3) d(0, 4)
    #           d(1, 2) d(1, 3) d(1, 4)
    #                   d(2, 3) d(2, 4)
    #                           d(3, 4)
    #
    # The City-Block Distance function is (in pure python):
    # def d(i, j):
    #     result = sum(abs(a-b) for a, b in zip(token_dims[i], token_dims[j]))
    #
    # So the token distances are:
    #        10      40      60     100
    #                30      50      90
    #                        20      60
    #                                40
    #
    # We now exclude the diagonal terms:
    #         .      40      60     100
    #                 .      50      90
    #                         .      60
    #                                 .
    #
    # And rewrite from left-to-bottom (to save space in memory)
    # [ 40,  60, 100,  50,  90,  60]
    #
    # N.B. This is equivalent but slower:
    # [sum(token_counts[i:j+1]) for i in range(n) for j in range(i+1, n)]

    return scipy.spatial.distance.pdist(token_dims, "cityblock")[drop_ind]


def create_pdist(
    token_counts: list[int], pair_embed_dist: list[float], weight_embed_dist: float = 0.2, use_log: bool = True
) -> NDArray[np.float64]:
    """
    Creates a distance (upper) matrix for the chunk merging.
    It combines embedding distance with token counts metric for adjacent chunks.
    Distance between neighbours is always smaller than further away pair -> enforcing
    the hierarchical clustering to merge only adjacent blocks in each step.
    """

    if len(pair_embed_dist) != len(pair_embed_dist):
        message = "distances do not have the same length"
        raise ValueError(message)

    # Phase 1: Calculate the two forms of distance between adjacent chunks

    embed_dist = compute_embed_dist(pair_embed_dist)
    token_dist = compute_token_dist(token_counts)

    # scale the distances by log to make them more comparable
    if use_log:
        embed_dist = np.log(embed_dist + 1)
        token_dist = np.log(token_dist + 1)

    # make the two distances comparable and then scale them using input weight parameter
    # smaller weight means more importance of the token count distance
    # bigger weight means more importance of the embedding distance
    if embed_dist_std := np.std(embed_dist) > 0:
        embed_dist = embed_dist / embed_dist_std * weight_embed_dist
    if token_dist_std := np.std(token_dist) > 0:
        token_dist = token_dist / token_dist_std * (1 - weight_embed_dist)

    # Phase 2: Combine the two distances into one
    # the two above distance are combined either using sum or product (i.e. use_log=T)
    return embed_dist + token_dist
