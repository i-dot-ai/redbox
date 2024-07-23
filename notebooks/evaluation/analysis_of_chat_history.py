import glob
import inspect
import os
import re
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
import seaborn as sns
import numpy as np
from regex import D
from wordcloud import STOPWORDS, WordCloud
from bertopic import BERTopic

class ChatHistoryAnalysis():
    def __init__(self) -> None:
        root = Path(__file__).parents[2]
        self.evaluation_dir = root / "notebooks/evaluation"
        results_dir = f'{self.evaluation_dir}/results'
        self.visualisation_dir = f'{results_dir}/visualisations/'
        self.table_dir = f'{results_dir}/table/'
        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(self.visualisation_dir, exist_ok=True)
        os.makedirs(self.table_dir, exist_ok=True)

        # IMPORTANT - For this to work you must save your chat history CSV dump in notebooks/evaluation/data/chat_histories 
        file_path = self.latest_chat_history_file()
        self.chat_logs = pd.read_csv(file_path)

        # Select specific columns and converting to readable timestamp
        self.chat_logs = self.chat_logs[['created_at', 'users', 'chat_history', 'text', 'role', 'id']]
        self.chat_logs['created_at'] = pd.to_datetime(self.chat_logs['created_at'])

        self.ai_responses = self.chat_logs[self.chat_logs['role'] == 'ai']
        self.user_responses = self.chat_logs[self.chat_logs['role'] == 'user']

        self.chat_logs['tokens'] = self.chat_logs['text'].apply(self.preprocess_text)
        self.ai_responses['tokens'] = self.ai_responses['text'].apply(self.preprocess_text)
        self.user_responses['tokens'] = self.user_responses['text'].apply(self.preprocess_text)

        self.user_responses['route'] = self.user_responses['text'].apply(lambda row: 'summarise' if row.startswith('@summarise') else ('chat' if row.startswith('@chat') else 'no_route'))

        self.topic_model = None
        self.topic_model_over_time = None

        self.figsize = (10, 5)
        mpl.rcParams.update({'font.size': 10})
        mpl.rcParams.update({'font.family': 'Arial'})

    def latest_chat_history_file(self):
        chat_history_folder = glob.glob(f'{self.evaluation_dir}/data/chat_histories/*')
        latest_file = max(chat_history_folder, key=os.path.getctime)
        return latest_file

    def preprocess_text(self, text):
        tokens = text.split()
        tokens = [word.lower() for word in tokens if word.isalpha()]
        return tokens

    # 1) Who uses Redbox the most?
    def user_frequency_analysis(self):
        user_counts = self.chat_logs['users'].value_counts()

        user_name = [user_email.split('@')[0].replace('.', ' ').title() for user_email in user_counts.index]
        wrapped_user_name = ['\n'.join(textwrap.wrap(name, width=10)) for name in user_name]

        # Table
        table_data = {'Name': user_name, 'Email': user_counts.index, 'Number of times used': user_counts.values}
        table_dataframe = pd.DataFrame(data=table_data, index=user_name)
        table_dataframe.to_csv(f'{self.table_dir}top_users.csv', index=False)

        # Barplot
        plt.figure(figsize=self.figsize)
        sns.barplot(x=wrapped_user_name, y=user_counts.values, palette='viridis')

        plt.xticks(ha='right', size=9)
        plt.title('Unique Users by Total Number of Messages')
        plt.xlabel('Users')
        plt.ylabel('Total No. of Messages')
        top_users_path = os.path.join(self.visualisation_dir, 'top_users.png')
        plt.savefig(top_users_path)

    # 2) Redbox traffic analysis
    def redbox_traffic_analysis(self):
        # think about GA integration?
        self.chat_logs['date'] = self.chat_logs['created_at'].dt.date
        date_counts = self.chat_logs['date'].value_counts().sort_index()

        # Table
        table_data = {'Date': date_counts.index, 'Usage': date_counts.values}
        table_dataframe = pd.DataFrame(data=table_data)
        table_dataframe.to_csv(f'{self.table_dir}usage_of_redbox_ai_over_time.csv', index=False)

        # Line graph
        plt.figure(figsize=self.figsize)
        date_counts.plot(kind='line')
        plt.title('Usage of Redbox AI Over Time')
        plt.xlabel('Date')
        plt.ylabel('Number of Conversations')
        conversation_frequency_path = os.path.join(self.visualisation_dir, 'usage_of_redbox_ai_over_time.png')
        plt.savefig(conversation_frequency_path)

    # 3) Which words are used the most frequently by USERS?
    def user_word_frequency_analysis(self):
        all_tokens = [token for tokens in self.user_responses['tokens'] for token in tokens]

        # far too many stopwords and wordcloud has a lovely constant attached to resolve this
        stopwords_removed_from_all_tokens = [word for word in all_tokens if word not in STOPWORDS]

        word_freq = Counter(stopwords_removed_from_all_tokens)

        most_common_words = word_freq.most_common(20)  #TODO - determine how many common words we want and the right vis. for this
        words, counts = zip(*most_common_words)

        # Table
        table_data = {'Word': list(word_freq.keys()), 'Frequency': list(word_freq.values())}
        table_dataframe = pd.DataFrame(data=table_data).sort_values('Frequency', ascending=False)
        table_dataframe.to_csv(f'{self.table_dir}user_most_frequent_words_table.csv', index=False)

        # Barplot
        plt.figure(figsize=self.figsize)
        sns.barplot(x=list(counts), y=list(words), palette='viridis')
        plt.title('Top 20 Most Frequent Words')
        plt.xlabel('Frequency')
        plt.ylabel('Words')
        barplot_path = os.path.join(self.visualisation_dir, 'user_most_frequent_words_barplot.png')
        plt.savefig(barplot_path)

        # Wordcloud - TODO - assess value
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(word_freq)
        plt.figure(figsize=self.figsize)
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('Most Frequent Words')
        wordcloud_path = os.path.join(self.visualisation_dir, 'user_most_frequent_words.png')
        plt.savefig(wordcloud_path)

    # 4) Which words are used the most frequently by AI?
    def ai_word_frequency_analysis(self):
        ai_word_freq = Counter([token for tokens in self.ai_responses['tokens'] for token in tokens if token not in STOPWORDS])
        most_common_words = ai_word_freq.most_common(20)  #TODO - determine how many common words we want and the right vis. for this
        words, counts = zip(*most_common_words)

        # Table
        table_data = {'Word': list(ai_word_freq.keys()), 'Frequency': list(ai_word_freq.values())}
        table_dataframe = pd.DataFrame(data=table_data).sort_values('Frequency', ascending=False)
        table_dataframe.to_csv(f'{self.table_dir}ai_most_frequent_words_table.csv', index=False)

        # Barplot
        plt.figure(figsize=self.figsize)
        sns.barplot(x=list(counts), y=list(words), palette='viridis')
        plt.title('Top 20 Most Frequent Words')
        plt.xlabel('Frequency')
        plt.ylabel('Words')
        barplot_path = os.path.join(self.visualisation_dir, 'ai_most_frequent_words_barplot.png')
        plt.savefig(barplot_path)
        
        # Wordcloud - TODO - assess value
        ai_wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(ai_word_freq)
        plt.figure(figsize=self.figsize)
        plt.imshow(ai_wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('Most Frequent Words in AI Responses')
        ai_wordcloud_path = os.path.join(self.visualisation_dir, 'ai_most_frequent_words.png')
        plt.savefig(ai_wordcloud_path)

    # 5) Is there a clear pattern behind AI responses?
    def ai_response_pattern_analysis(self):
        def clean_text(text): # was including asterisks giving useless info to the graph I'm still not entirely convinced on the benefit of this analysis
            return re.sub('[!@#$*]', '', text).strip()

        self.ai_responses['clean_text'] = self.ai_responses['text'].apply(clean_text)
        ai_response_patterns = self.ai_responses['clean_text'].apply(lambda x: ' '.join(x.split()[:2])).value_counts().head(10)
        
        # Table
        words, counts = zip(*self.ai_responses['clean_text'].apply(lambda x: ' '.join(x.split()[:2])).value_counts())
        table_data = {'Word': words, 'Frequency': counts}
        table_dataframe = pd.DataFrame(data=table_data)
        table_dataframe.to_csv(f'{self.table_dir}common_ai_patterns.csv', index=False)

        # Barplot
        plt.figure(figsize=self.figsize)
        sns.barplot(x=ai_response_patterns.values, y=ai_response_patterns.index, palette='magma')
        plt.title('Common Patterns in AI Responses')
        plt.xlabel('Frequency')
        plt.ylabel('Patterns')
        ai_patterns_path = os.path.join(self.visualisation_dir, 'common_ai_patterns.png')
        plt.savefig(ai_patterns_path)

    # What routes are people using?
    def route_analysis(self):

        df = self.user_responses.copy()
        
        # # Some users repeat the same message several times (drop?)
        # df = df.drop_duplicates(['text'])

        # User names
        user_name = [user_email.split('@')[0].replace('.', ' ').title() for user_email in df.users]
        wrapped_user_name = ['\n'.join(textwrap.wrap(name, width=10)) for name in user_name]
        df['user_name'] = wrapped_user_name

        # Groupby routes
        df_grouped = df.groupby(['user_name'])['route'].value_counts().unstack()

        # Plot
        plt.figure(figsize=self.figsize)
        df_grouped.plot(kind='bar',
                        color={"chat": "teal", 
                               "no_route": "yellowgreen",
                               "summarise": "gold"},
                        figsize=self.figsize)
        plt.xticks(rotation=0)
        plt.xlabel('Users')
        plt.ylabel('Number of routes taken')
        plt.title('Routes taken per user')
        routes_count_path = os.path.join(self.visualisation_dir, 'routes_per_user.png')
        plt.savefig(routes_count_path)

    def get_route_transitions(self, df):

        # TODO Check this works with the groupby ID and time order of events
        df['next_route'] = df['route'].shift(1)

        df['transition'] = df.apply(lambda row: f"{row['route']} to {row['next_route']}"
                                        if pd.notna(row['next_route']) else None, axis=1)
            
        return df

    # In what way are users switching between routes?
    def route_transitions(self):

        # Get route transitions and counts per user session (is 'id' appropriate?)
        df_transitions = self.user_responses.groupby('id').apply(self.get_route_transitions).reset_index(drop=True)

        transition_counts = df_transitions['transition'].value_counts().reset_index()

        # Plot
        sns.barplot(x=transition_counts['transition'], y=transition_counts['count'],
                    palette='viridis')
        plt.xticks(rotation=45, ha='right')
        plt.title('Number of different route transitions')
        plt.xlabel('Route transition')
        plt.ylabel('Number of route transitions')

    # Are users asking about common topics?
    def get_topics(self):
            
        STOPWORDS.add('@chat')
        STOPWORDS.add('@summarise')

        # Remove stopwords and fit (simple) topic model
        text_without_stopwords = self.user_responses['text'].apply(lambda row: ' '.join([word for word in row.split() if word not in (STOPWORDS)]))
        created_at = self.user_responses['created_at'].to_list()
        
        topic_model = BERTopic(verbose=True)
        topic_model.fit_transform(text_without_stopwords)
        topics_over_time = topic_model.topics_over_time(text_without_stopwords, created_at)
        
        self.topic_model = topic_model
        self.topics_over_time  = topics_over_time

    def visualise_topics(self):
        # Plot
        return self.topic_model.visualize_topics(width=800, height=500)
    
    def visualise_hierarchy(self):
        # Plot
        return self.topic_model.visualize_hierarchy(width=800, height=400)
    
    def visualise_barchart(self):
        # Plot
        return self.topic_model.visualize_barchart(width=800, height=400)
    
    def visualise_topics_over_time(self):
        # Plot
        return self.topic_model.visualize_topics_over_time(self.topics_over_time,
                                                           top_n_topics = 5,
                                                           normalize_frequency=True)

def main():
    chat_history_analysis = ChatHistoryAnalysis()
    attrs = (getattr(chat_history_analysis, name) for name in dir(chat_history_analysis))
    methods = filter(inspect.ismethod, attrs)
    for method in methods:
        try:
            method()
        except TypeError:
            pass


if __name__ == "__main__":
    main()
