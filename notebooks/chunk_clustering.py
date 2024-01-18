# %%
import json
import os
import re

import dotenv
import numpy as np
import pandas as pd

# note extra dependencies: plotly, kaleido
import plotly.express as px
import plotly.figure_factory as ff
import scipy
from langchain.chains import LLMChain
from langchain.chat_models import ChatAnthropic
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from pyprojroot import here

# %%

chunk_folder = os.path.join(here(), "data", "dev", "chunks")
chunk_files = os.listdir(chunk_folder)

# %%
chunks = []
for file_name in chunk_files:
    with open(os.path.join(chunk_folder, file_name), "r") as f:
        chunks.append(json.load(f))

df = pd.DataFrame()
df["chunk_num"] = [chunk["index"] for chunk in chunks]
df["token_count"] = [chunk["token_count"] for chunk in chunks]
df["text"] = [chunk["text"] for chunk in chunks]
df["parent_doc"] = [chunk["parent_file"]["name"] for chunk in chunks]
df = df.sort_values(["parent_doc", "chunk_num"]).reset_index(drop=True)
df["chunk_prop"] = df.groupby("parent_doc")["chunk_num"].transform(
    lambda x: x / x.max()
)
print(df)

# %%
# histogram of chunks token counts
fig = px.histogram(df, x="token_count", color="parent_doc")
fig.update_layout(showlegend=False)
fig.show()

# %%
# chunk sizes based on place in article
fig = px.scatter(df, y="token_count", color="parent_doc")
fig.update_layout(showlegend=False)
fig.show()


# %%
# embed and look at the coordinates

embed = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
df["embed_coord"] = [embed.embed_query(text) for text in df["text"]]


# %%
df["prev_coord"] = df.groupby("parent_doc").shift(1)["embed_coord"]
df["token_add_prev"] = (
    df["token_count"] + df.groupby("parent_doc").shift(1)["token_count"]
)

dist_array = []
for i in range(len(df.index)):
    if df["prev_coord"].isna()[i]:
        dist_array.append(None)
    else:
        dist_array.append(
            scipy.spatial.distance.cosine(
                df.loc[i, "embed_coord"], df.loc[i, "prev_coord"]
            )
        )
df["prev_dist"] = dist_array

# %%
# looking for elbow in the distances histogram
fig = px.histogram(
    df, x="prev_dist", color="parent_doc", facet_col="parent_doc", facet_col_wrap=4
)
fig.update_layout(showlegend=False)
fig.show()


# %%
# for this chunking strategy to work we would like to see shape like uuuuuuuuuuuuuuuu
fig = px.scatter(df, y="prev_dist", color="parent_doc", hover_data=["token_add_prev"])
fig.update_layout(showlegend=False)
fig.show()


# %%
# visualise hierarchical clustering of the small chunks

# consider two types of distances between neighbours (cosine and sizes of merged chunks)
# i.e. make the clustering algorithm merge close/small neighbouring chunks first
# it is like putting the points on a line with spaces corresponding to chosen distance

# put some big dist between different docs (fillna)
print(max(df.groupby("parent_doc").token_count.sum()))
X_token_count = np.array([[x] for x in df["token_add_prev"].fillna(50000).cumsum()])
X_embed_dist = np.array([[x] for x in df["prev_dist"].fillna(1.3).cumsum()])


# %%
hc = {}
dendro_token_count = ff.create_dendrogram(
    X=X_token_count,
    linkagefun=lambda x: scipy.cluster.hierarchy.linkage(x, "complete"),
    # distance between two clusters is the total size of all included chunks (i.e. max)
    orientation="left",
    color_threshold=50000,
)
hc["token_count"] = scipy.cluster.hierarchy.linkage(
    scipy.spatial.distance.pdist(X_token_count), "complete"
)

dendro_embed_dist = ff.create_dendrogram(
    X=X_embed_dist,
    linkagefun=lambda x: scipy.cluster.hierarchy.linkage(x, "single"),
    # distance between two clusters is the similarty between the two neighbouring chunks (i.e. min)
    orientation="left",
    color_threshold=1.29,
)

hc["embed_dist"] = scipy.cluster.hierarchy.linkage(
    scipy.spatial.distance.pdist(X_embed_dist), "single"
)

# guess some sensible number of clusters and attach cluster labels to df
num_clusters = np.round(df["token_count"].sum() / 400)
for clust_type in ["token_count", "embed_dist"]:
    df["clusters_" + clust_type] = [
        x[0]
        for x in scipy.cluster.hierarchy.cut_tree(
            hc[clust_type], n_clusters=num_clusters
        )
    ]

# %%
# its too big to display (I want legible chunk numbers), so write down (takes ~5mins)
dendro_token_count.write_image("dendro_token_count.png", height=20000, width=50000)
dendro_embed_dist.write_image("dendro_embed_dist.png", height=20000, width=500)


# %%
# what would be the optimal cutoff for the hierachical clustering?
# how does the resulting clustering compare?  size, semantic coherence (max of the cosine dist)


# %%
# combine the distances and apply only to individual docs
def create_pdist1(df, weight_embed_dist=0.5):
    df_in = df[["token_count", "prev_dist"]].reset_index(drop=True)
    embed_dist = []
    token_dist = []
    for i in range(0, len(df_in)):
        for j in range(i + 2, len(df_in) + 1):
            embed_dist.append(df_in.loc[(i + 1) : j, "prev_dist"].max())
            token_dist.append(df_in.loc[i:j, "token_count"].sum())
    if np.std(embed_dist) > 0:
        embed_dist = embed_dist / np.std(embed_dist) * weight_embed_dist
    if np.std(embed_dist) > 0:
        token_dist = token_dist / np.std(token_dist) * (1 - weight_embed_dist)
    combined_dist = [x + y for x, y in zip(embed_dist, token_dist)]
    return combined_dist


def create_pdist2(df, weight_embed_dist=0.5):
    df_in = df[["token_count", "prev_dist"]].reset_index(drop=True)
    df_in = df.loc[df["parent_doc"] == doc, ["token_count", "prev_dist"]].reset_index(
        drop=True
    )
    embed_dist = []
    token_dist = []
    for i in range(1, len(df_in)):
        token_dist = token_dist + list(df_in.loc[(i - 1) :, "token_count"].cumsum()[1:])
        embed_dist = embed_dist + list(
            np.maximum.accumulate(df_in.loc[i:, "prev_dist"])
        )
    if np.std(embed_dist) > 0:
        embed_dist = embed_dist / np.std(embed_dist) * weight_embed_dist
    if np.std(embed_dist) > 0:
        token_dist = token_dist / np.std(token_dist) * (1 - weight_embed_dist)
    combined_dist = [x + y for x, y in zip(embed_dist, token_dist)]
    return combined_dist


def create_pdist(df, weight_embed_dist=0.2, use_log=True):
    df_in = df[["token_count", "prev_dist"]].reset_index(drop=True)
    n = len(df_in)
    embed_dims = np.tri(n, k=0) * np.array(df_in["prev_dist"])
    embed_dist = scipy.spatial.distance.pdist(embed_dims, "chebyshev")

    token_dims = np.tri(n + 1, k=0) * np.concatenate(
        [[0], np.array(df_in["token_count"])]
    )
    # drop diagonal (sizes of individual chunks)
    drop_ind = [
        y - x > 1
        for x, y in zip(np.triu_indices(n + 1, k=1)[0], np.triu_indices(n + 1, k=1)[1])
    ]
    token_dist = scipy.spatial.distance.pdist(token_dims, "cityblock")[drop_ind]
    if use_log:
        embed_dist = np.log(embed_dist + 1)
        token_dist = np.log(token_dist + 1)
    if np.std(embed_dist) > 0:
        embed_dist = embed_dist / np.std(embed_dist) * weight_embed_dist
    if np.std(embed_dist) > 0:
        token_dist = token_dist / np.std(token_dist) * (1 - weight_embed_dist)
    combined_dist = [x + y for x, y in zip(embed_dist, token_dist)]
    return combined_dist


# %%

# %timeit
# 2-loop version 1.5mins
# 1-loop version 4sec
# vectorised 0.4sec

for doc in df["parent_doc"].unique():
    print(doc)
    print(create_pdist(df[df["parent_doc"] == doc])[1:10])

# %%
# TODO make it pipeline ready
# how to test whether it has positive impact of doc retriaval performance?

# %%
weight_vals = [0.03, 0.1, 0.2, 0.3, 0.5, 0.75, 0.97]
optimal_chunk_size = 300
export_dendro = False
for weight in weight_vals:
    hc = {}
    df["clusters_combined_dist"] = None
    for doc in df["parent_doc"].unique():
        dist_triu = create_pdist(df[df["parent_doc"] == doc], weight_embed_dist=weight)
        hc[doc] = scipy.cluster.hierarchy.linkage(dist_triu, "complete")
        num_clusters = round(
            df.loc[df["parent_doc"] == doc, "token_count"].sum() / optimal_chunk_size
        )
        df.loc[df["parent_doc"] == doc, "clusters_combined_dist"] = [
            str(cl_num) + doc
            for cl_num in scipy.cluster.hierarchy.cut_tree(
                hc[doc], n_clusters=num_clusters
            )
        ]
    df["clusters_combined_dist_w" + str(weight)] = df["clusters_combined_dist"]

# %%
# plot_the_dendrograms
hc = {}
if not os.path.exists("pic"):
    os.makedirs("pic")
for doc in df["parent_doc"].unique():
    dist_triu = create_pdist(df[df["parent_doc"] == doc], weight_embed_dist=weight)
    hc[doc] = scipy.cluster.hierarchy.linkage(dist_triu, "complete")
    num_clusters = round(
        df.loc[df["parent_doc"] == doc, "token_count"].sum() / optimal_chunk_size
    )
    color_height = hc[doc][-num_clusters + 1][2]

    fig = ff.create_dendrogram(
        X=np.array([[i] for i in df[df["parent_doc"] == doc].index]),
        distfun=lambda x: dist_triu,
        linkagefun=lambda x: scipy.cluster.hierarchy.linkage(x, "complete"),
        orientation="left",
        color_threshold=color_height,
    )
    fig.write_image(
        "pic/dendro_" + doc + ".png", height=200 + sum(df["parent_doc"] == doc) * 8
    )

# %%
# visualise some characteristics of the resulting clusters
plot_df = {}
for clust_type in (
    ["token_count"]
    + ["combined_dist_w" + str(weight) for weight in weight_vals]
    + ["embed_dist"]
):
    plot_df[clust_type] = pd.DataFrame()
    plot_df[clust_type]["clust_token_count"] = df.groupby("clusters_" + clust_type)[
        "token_count"
    ].sum()
    plot_df[clust_type]["clust_semantic_dist"] = df.groupby("clusters_" + clust_type)[
        "prev_dist"
    ].agg(lambda x: 0 if len(x) == 1 else max(x[1:]))
    plot_df[clust_type]["parent_doc"] = df.groupby("clusters_" + clust_type)[
        "parent_doc"
    ].agg(lambda x: x.unique()[0])
    plot_df[clust_type]["num_chunks"] = df.groupby("clusters_" + clust_type)[
        "chunk_num"
    ].count()
    print(plot_df[clust_type].describe())
    plot_df[clust_type]["clust_type"] = clust_type

plot_df4 = pd.concat(plot_df).reset_index(drop=True)
fig = px.scatter(
    plot_df4,
    x="clust_token_count",
    y="clust_semantic_dist",
    color="parent_doc",
    hover_data=["num_chunks"],
    facet_col="clust_type",
    facet_col_wrap=2,
    title="Clusters' characteristics by distance method/weighting",
)
fig.update_layout(showlegend=False, height=600)
fig.show()


# %%
#######################################################################################
# ask claude to do it- check where the breaks are

ENV = dotenv.dotenv_values("../.env")
llm = ChatAnthropic(
    anthropic_api_key=ENV["ANTHROPIC_API_KEY"], max_tokens=4000, temperature=0
)

remove_breaks_prompt = PromptTemplate.from_template(
    """Your task is to create semantically coherent chunks of the input text by removing unnecessary breaks.
        The input text is split in smaller parts setarated by numbered breaks using tag: "<BREAKX>" for break number X.
        Return list of tags of breaks that should be removed. The resulting merged chunks should be semantically
        similar (addressing the same topic) and should be about 100-500 words long.

        ======================
        Input text:

        <document>
        <BREAK0>The domains wikipedia.com (later redirecting to wikipedia.org) and wikipedia.org were registered on January 12, 2001,[25] and January 13, 2001,[26]
        respectively. <BREAK1>Wikipedia was launched on January 15, 2001[18] as a single English-language edition at www.wikipedia.com,[27] and announced by Sanger
        on the Nupedia mailing list.[21] <BREAK2>The name originated from a blend of the words wiki and encyclopedia.[28][29] <BREAK3>Its integral policy of "neutral
        point-of-view"[30] was codified in its first few months. Otherwise, there were initially relatively few rules, and it operated <BREAK4>independently of Nupedia.[21]
        Bomis originally intended it as a business for profit.[31]<BREAK5>
        The Wikipedia home page on December 20, 2001[note 5]

        Graphs are unavailable due to technical issues.<BREAK6>
        English Wikipedia editors with >100 edits per month[32]

        Graphs are unavailable due to technical issues.
        Number of English Wikipedia articles[33]<BREAK7>

        Wikipedia gained early contributors from Nupedia, Slashdot postings, and web search engine indexing. Language editions were created beginning in March 2001, <BREAK8>
        with a total of 161 in use by the end of 2004.[34][35] Nupedia and Wikipedia coexisted until the former's servers were taken down permanently in 2003,
        and its text was incorporated into Wikipedia. <BREAK9>
        The English Wikipedia passed the mark of two million articles on September 9, 2007, making it the largest encyclopedia ever assembled,
        surpassing the Yongle Encyclopedia made during the Ming dynasty in 1408, which had held the record for almost 600 years.[36]<BREAK10>

        Citing fears of commercial advertising and lack of control, users of the Spanish Wikipedia forked from Wikipedia to create Enciclopedia Libre in February 2002.[37]
        Wales then announced that Wikipedia would not display advertisements, and changed Wikipedia's domain from wikipedia.com to wikipedia.org.[38][39]<BREAK11>

        Though the English Wikipedia reached three million articles in August 2009, the growth of the edition, in terms of the numbers of new articles and of editors,
        appears to have peaked around early 2007.[40] Around 1,800 articles were added daily to the encyclopedia in 2006; by 2013 that average was roughly 800.[41]<BREAK12>
        A team at the Palo Alto Research Center attributed this slowing of growth to the project's increasing exclusivity and resistance to change.[42] Others suggest that
        the growth is flattening naturally because articles that could be called "low-hanging fruit"—topics that clearly merit an article—have already been created and
        built up extensively.[43][44][45]
        </document>

        ======================
        List of breaks to be removed:
        <BREAK1>,<BREAK2>,<BREAK4>,<BREAK6>,<BREAK8>,<BREAK9>,<BREAK12>

        ======================
        Input text:

        <document>
        {text_with_breaks}
        </document>

        ======================
        List of breaks to be removed:
        """
)

simple_question_chain = LLMChain(
    llm=llm,
    prompt=remove_breaks_prompt,
)


def create_input_text(chunks=[]):
    text = ""
    for i, chunk in enumerate(chunks):
        text += "<BREAK" + str(i) + ">" + chunk
    return text


# %%
ans = {}
for doc in df["parent_doc"].unique():
    input_text = create_input_text(df["text"][df["parent_doc"] == doc])
    ans[doc] = simple_question_chain(
        {"text_with_breaks": input_text},
    )["text"]
print(ans)


# %%
non_breaks = {x: re.findall("<BREAK(.*?)>", ans[x]) for x in ans.keys()}
non_breaks

df["keep_breaks"] = [
    str(x) not in non_breaks[y] for x, y in zip(df["chunk_num"], df["parent_doc"])
]
df["clusters_claude"] = df["keep_breaks"].cumsum()

# %%
fig = px.scatter(df, y="prev_dist", color="keep_breaks")
fig.update_layout(showlegend=False)
fig.show()
