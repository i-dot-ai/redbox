# Set up
import pandas as pd
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sentence_transformers import SentenceTransformer
import torch
import gensim
from gensim import corpora
from gensim.models import LdaModel
import pyLDAvis
import pyLDAvis.gensim

# Load your dataset
df = pd.read_csv('/survey_usage_analysis/user_prompts.csv')

# Filter to focus only on user messages
df_user = df.loc[df['role'] == 'user'].copy()  # Use .copy() to avoid SettingWithCopyWarning

# Preprocess text
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

def preprocess(text):
    if isinstance(text, str):  # Check if the text is a string
        tokens = word_tokenize(text.lower())
        tokens = [lemmatizer.lemmatize(word) for word in tokens if word.isalpha() and word not in stop_words]
        return ' '.join(tokens)
    else:
        return ''  # Return an empty string if text is not a string (e.g., NaN or float)

# Replace NaN values with an empty string and ensure all entries are strings
df_user.loc[:, 'text'] = df_user['text'].fillna('')
df_user.loc[:, 'text'] = df_user['text'].astype(str)

# Apply preprocessing
df_user.loc[:, 'processed_text'] = df_user['text'].apply(preprocess)

# Combine all processed text into one large string
all_processed_text = ' '.join(df_user['processed_text'])

# Tokenize the combined text
tokens = word_tokenize(all_processed_text)

# Count the frequency of each word
word_counts = Counter(tokens)

# Get the 20 most common words
most_common_words = word_counts.most_common(20)

# Display the most common words
print("Most common words:")
for word, count in most_common_words:
    print(f"{word}: {count}")

# Extract tasks using TF-IDF
vectorizer = TfidfVectorizer(ngram_range=(1, 6))
X = vectorizer.fit_transform(df_user['processed_text'])

# Clustering tasks (KMeans as an example)
kmeans = KMeans(n_clusters=10, random_state=42)
df_user.loc[:, 'task_cluster'] = kmeans.fit_predict(X)

# Summarize the most common tasks
common_tasks = df_user['task_cluster'].value_counts()

# Show the most common tasks
print(common_tasks)

# Optionally, review some examples from each cluster
for cluster in common_tasks.index:
    print(f"Cluster {cluster}:")
    print(df_user[df_user['task_cluster'] == cluster]['text'].head(5))
    print("\n")

# Load a pre-trained Sentence Transformer model to generate sentence embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embeddings for each text in the 'processed_text' column
X = model.encode(df_user['processed_text'].tolist(), convert_to_tensor=True)

# Ensure the embeddings are on the CPU and convert them to a NumPy array
if isinstance(X, torch.Tensor):
    X = X.cpu().numpy()

# Clustering tasks (KMeans as an example)
kmeans = KMeans(n_clusters=10, random_state=42)
df_user.loc[:, 'task_cluster'] = kmeans.fit_predict(X)

# Summarize the most common tasks
common_tasks = df_user['task_cluster'].value_counts()

# Show the most common tasks
print(common_tasks)

# Review some examples from each cluster
for cluster in common_tasks.index:
    print(f"Cluster {cluster}:")
    print(df_user[df_user['task_cluster'] == cluster]['text'].head(5))
    print("\n")

# Function to tokenize and prepare data for LDA
def prepare_for_lda(df, cluster_col='task_cluster', text_col='processed_text'):
    cluster_topics = {}
    for cluster in df[cluster_col].unique():
        # Get the text of the current cluster
        cluster_texts = df[df[cluster_col] == cluster][text_col].tolist()
        # Tokenize the text
        tokenized_texts = [text.split() for text in cluster_texts]
        # Create a dictionary and corpus for LDA
        dictionary = corpora.Dictionary(tokenized_texts)
        corpus = [dictionary.doc2bow(text) for text in tokenized_texts]
        # Store the prepared data for each cluster
        cluster_topics[cluster] = {
            'corpus': corpus,
            'dictionary': dictionary,
            'tokenized_texts': tokenized_texts
        }
    return cluster_topics

# Apply the LDA for each cluster
def apply_lda(cluster_data, num_topics=3, passes=10):
    cluster_models = {}
    for cluster, data in cluster_data.items():
        # Build the LDA model for the current cluster
        lda_model = LdaModel(corpus=data['corpus'],
                             id2word=data['dictionary'],
                             num_topics=num_topics,
                             passes=passes,
                             random_state=42)
        # Save the LDA model
        cluster_models[cluster] = lda_model
        print(f"\nCluster {cluster} Topics:")
        for idx, topic in lda_model.print_topics(-1):
            print(f"Topic {idx + 1}: {topic}")
    return cluster_models

# Prepare the data for LDA (tokenization and corpus creation)
cluster_data = prepare_for_lda(df_user)

# Apply LDA to each cluster to get 3 topics per cluster
cluster_models = apply_lda(cluster_data, num_topics=3, passes=15)

# Show topics for a specific cluster (e.g., cluster 0)
cluster_id = 0
lda_model = cluster_models[cluster_id]
print(f"\nTopics for Cluster {cluster_id}:")
for idx, topic in lda_model.print_topics(-1):
    print(f"Topic {idx + 1}: {topic}")

# Visualise the topics of each cluster
def visualize_lda_model(lda_model, corpus, dictionary, cluster_num):
    # Visualize the LDA model for the specified cluster
    print(f"Generating pyLDAvis for Cluster {cluster_num}")
    lda_vis_data = pyLDAvis.gensim.prepare(lda_model, corpus, dictionary)

    # Save the visualization as an HTML file
    file_name = f"cluster_{cluster_num}_lda_vis.html"
    pyLDAvis.save_html(lda_vis_data, file_name)
    print(f"Saved pyLDAvis for Cluster {cluster_num} to {file_name}")


# Loop over all clusters and generate visualizations
for cluster_id in cluster_models.keys():
    lda_model = cluster_models[cluster_id]
    cluster_corpus = cluster_data[cluster_id]['corpus']
    cluster_dictionary = cluster_data[cluster_id]['dictionary']

    # Call the function to visualize and save each cluster
    visualize_lda_model(lda_model, cluster_corpus, cluster_dictionary, cluster_id)