# Set up
import pandas as pd
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import seaborn as sns
from wordcloud import WordCloud
from sentence_transformers import SentenceTransformer
import torch
import os
import gensim
from gensim import corpora
from gensim.models import LdaModel
import pyLDAvis
import pyLDAvis.gensim

# Specify path to data
user_path = '/Users/morgan.frodsham/PycharmProjects/redbox-analysis/route_analysis/role_user.csv'

# Load csv files into dataframe
user_df = pd.read_csv(user_path)

## TASK 1: Proportion of use for each route
route_counts = user_df['model_route'].value_counts()
total_count = len(user_df)
route_proportions = (route_counts / total_count) * 100

colors = sns.color_palette("Paired", n_colors=len(route_proportions))

# Create bar chart
plt.figure(figsize=(10, 6))
route_proportions.plot(kind='bar', color=colors)
plt.title('Percentage of Use for Each Route', fontsize=16)
plt.xlabel('Route', fontsize=14)
plt.ylabel('Percentage', fontsize=14)
plt.xticks(rotation=45)
plt.tight_layout()

# Save the plot as a PNG file
png_file_path = '/Users/morgan.frodsham/PycharmProjects/redbox-analysis/route_analysis/route_bar_chart.png'
plt.savefig(png_file_path, format='png')

## TASK 2: Common word wordclouds by model route
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()


def preprocess(text):
    if isinstance(text, str):
        tokens = word_tokenize(text.lower())
        tokens = [lemmatizer.lemmatize(word) for word in tokens if word.isalpha() and word not in stop_words]
        return ' '.join(tokens)
    else:
        return ''


# Sanitize function
def sanitize_filename(model_route):
    return model_route.replace('/', '_')


# Loop through each 'model_route' and apply preprocessing
for model_route, group in user_df.groupby('model_route'):
    print(f"\nProcessing text for model_route: {model_route}")

    group.loc[:, 'text'] = group['text'].fillna('').astype(str)
    group.loc[:, 'processed_text'] = group['text'].apply(preprocess)

    all_processed_text = ' '.join(group['processed_text'])
    tokens = word_tokenize(all_processed_text)
    word_counts = Counter(tokens)

    wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='winter').generate_from_frequencies(
        word_counts)

    sanitized_model_route = sanitize_filename(model_route)

    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(f"Word Cloud for {model_route}")

    png_file_path = f'/Users/morgan.frodsham/PycharmProjects/redbox-analysis/route_analysis/wordcloud_{sanitized_model_route}.png'
    plt.savefig(png_file_path, format='png')
    plt.close()

    print(f"Word cloud saved as {png_file_path}")

## Task 3: Cluster and Topic Modelling
model = SentenceTransformer('all-MiniLM-L6-v2')


# Function to analyze clusters and topics for each model_route
def analyze_model_route(df_group, model, n_clusters=10):
    df_group = df_group.copy()  # Avoid modifying original DataFrame
    df_group['processed_text'] = df_group['text'].apply(preprocess)  # Ensure processed_text is created

    # Generate embeddings for 'processed_text'
    X = model.encode(df_group['processed_text'].tolist(), convert_to_tensor=True)
    if isinstance(X, torch.Tensor):
        X = X.cpu().numpy()

    # Adjust number of clusters based on the size of the group
    n_clusters = min(n_clusters, len(df_group))

    if len(df_group) < 2:
        print(f"Not enough data to cluster for {df_group['model_route'].iloc[0]}")
        return

    # Clustering (KMeans)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    df_group.loc[:, 'task_cluster'] = kmeans.fit_predict(X)

    common_tasks = df_group['task_cluster'].value_counts()
    print(f"Most common tasks for model_route {df_group['model_route'].iloc[0]}:")
    print(common_tasks)

    for cluster in common_tasks.index:
        print(f"\nCluster {cluster}:")
        print(df_group[df_group['task_cluster'] == cluster]['text'].head(5))
        print("\n")

    # Prepare and apply LDA to clusters within this model_route
    cluster_data = prepare_for_lda(df_group)  # Prepare LDA data for this route's clusters
    cluster_models = apply_lda(cluster_data, num_topics=3, passes=15)  # Apply LDA

    for cluster_id in cluster_models.keys():
        lda_model = cluster_models[cluster_id]
        cluster_corpus = cluster_data[cluster_id]['corpus']
        cluster_dictionary = cluster_data[cluster_id]['dictionary']
        visualize_lda_model(lda_model, cluster_corpus, cluster_dictionary, cluster_id, model_route)  # Pass model_route


# Prepare data for LDA for each model route's clusters
def prepare_for_lda(df, cluster_col='task_cluster', text_col='processed_text'):
    cluster_topics = {}
    for cluster in df[cluster_col].unique():
        cluster_texts = df[df[cluster_col] == cluster][text_col].tolist()
        tokenized_texts = [text.split() for text in cluster_texts]
        dictionary = corpora.Dictionary(tokenized_texts)
        corpus = [dictionary.doc2bow(text) for text in tokenized_texts]
        cluster_topics[cluster] = {'corpus': corpus, 'dictionary': dictionary, 'tokenized_texts': tokenized_texts}
    return cluster_topics


# Apply LDA for each cluster within each model_route
def apply_lda(cluster_data, num_topics=3, passes=10):
    cluster_models = {}
    for cluster, data in cluster_data.items():
        lda_model = LdaModel(corpus=data['corpus'], id2word=data['dictionary'], num_topics=num_topics, passes=passes,
                             random_state=42)
        cluster_models[cluster] = lda_model
        print(f"\nCluster {cluster} Topics:")
        for idx, topic in lda_model.print_topics(-1):
            print(f"Topic {idx + 1}: {topic}")
    return cluster_models


# Visualize LDA topics for each cluster and model route
def visualize_lda_model(lda_model, corpus, dictionary, cluster_num, model_route):
    lda_vis_data = pyLDAvis.gensim.prepare(lda_model, corpus, dictionary)
    sanitized_route = sanitize_filename(model_route)
    file_name = f"{sanitized_route}_cluster_{cluster_num}_lda_vis.html"

    # Ensure directory exists before saving
    output_dir = "/Users/morgan.frodsham/PycharmProjects/redbox-analysis/route_analysis/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file_path = os.path.join(output_dir, file_name)
    pyLDAvis.save_html(lda_vis_data, output_file_path)
    print(f"Saved pyLDAvis for Cluster {cluster_num} in {model_route} to {output_file_path}")


# Loop through model routes
for model_route, group in user_df.groupby('model_route'):
    print(f"\nAnalyzing model_route: {model_route}")
    analyze_model_route(group, model)