import inspect
import os
import re
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from bertopic import BERTopic
from django.db.models import F, Prefetch
from wordcloud import STOPWORDS, WordCloud

# packages = [
#     "django-environ",
#     "django-use-email-as-username",
#     "psycopg2-binary",
#     "django-magic-link",
#     "django-single-session",
#     "django-compressor",
#     "django-import-export",
#     "django-storages",
#     "daphne",
#     "django-allauth",
# ]
# import pip

# for package in packages:
# pip.main(["install", package])


# django.setup()

# from redbox_app.redbox_core.models import ChatHistory, ChatMessage


class ChatHistoryAnalysis:
    def __init__(self) -> None:
        root = Path(__file__).parents[2]
        self.evaluation_dir = root / "notebooks/evaluation"
        results_dir = f"{self.evaluation_dir}/results"
        self.visualisation_dir = f"{results_dir}/visualisations/"
        self.table_dir = f"{results_dir}/table/"
        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(self.visualisation_dir, exist_ok=True)
        os.makedirs(self.table_dir, exist_ok=True)

        # Commenting out this whilst testing with just data dump

        # self.chat_logs = self.fetch_chat_history()
        self.chat_logs = pd.read_csv("notebooks/evaluation/data/chat_histories/chathistory.csv")
        # This column dictionary will change keys depending on names given in data frame structure
        COLUMNS_DICT = {
            "modified_at": "created_at",
            "id": "message_id",
            "users": "user_email",
            "role": "role",
            "text": "text",
        }

        TEAM_EMAILS = ["alfie.dennen@trade.gov.uk", "isobel.daley@trade.gov.uk"]

        # TODO: Add row to map column headings to new streamlined ones

        # Select specific columns and converting to readable timestamp
        self.chat_logs = self.chat_logs[list(COLUMNS_DICT.keys())]
        # Note I tried the following with .rename() and it did not work.
        self.chat_logs.columns = [COLUMNS_DICT[col] if col in COLUMNS_DICT else col for col in self.chat_logs.columns]

        # self.chat_logs = self.chat_logs[['created_at', 'users_id', 'user_email', 'chat_history', 'text', 'role', 'message_id']]
        self.chat_logs["created_at"] = pd.to_datetime(self.chat_logs["created_at"])
        # Remove users that are redbox team
        self.chat_logs = self.chat_logs[~self.chat_logs["user_email"].isin(TEAM_EMAILS)]

        self.ai_responses = self.chat_logs[self.chat_logs["role"] == "ai"]
        self.user_responses = self.chat_logs[self.chat_logs["role"] == "user"]

        self.chat_logs["tokens"] = self.chat_logs["text"].apply(self.preprocess_text)
        self.ai_responses["tokens"] = self.ai_responses["text"].apply(self.preprocess_text)
        self.user_responses["tokens"] = self.user_responses["text"].apply(self.preprocess_text)

        self.user_responses["route"] = self.user_responses["text"].apply(
            lambda row: "summarise"
            if row.startswith("@summarise")
            else ("chat" if row.startswith("@chat") else "no_route")
        )

        self.topic_model = None
        self.topic_model_over_time = None

        self.figsize = (10, 5)
        mpl.rcParams.update({"font.size": 10})
        mpl.rcParams.update({"font.family": "Arial"})

    def anonymise_users(self):
        """
        If toggle switched in streamlit app then users are anonymised.
        """
        chat_log_users = self.chat_logs["user_email"].unique()
        n_users = len(chat_log_users)
        anon_users = []
        for i in range(1, n_users + 1):
            anon_users.append(f"User {i}")
        anon_user_dict = dict(zip(chat_log_users, anon_users, strict=False))
        self.chat_logs["user_email"] = self.chat_logs["user_email"].map(anon_user_dict)
        self.ai_responses["user_email"] = self.ai_responses["user_email"].map(anon_user_dict)
        self.user_responses["user_email"] = self.user_responses["user_email"].map(anon_user_dict)

    def fetch_chat_history(self, limit=100):
        chat_messages = ChatMessage.objects.all()
        chat_history_objects = (
            ChatHistory.objects.prefetch_related(Prefetch("messages", queryset=chat_messages))
            .annotate(user_email=F("users__email"))
            .values(
                "created_at",
                "users_id",
                "user_email",
                chat_history=F("id"),
            )[:limit]
        )

        results = []
        for chat_history in chat_history_objects:
            messages = ChatMessage.objects.filter(chat_history=chat_history["chat_history"]).values(
                "text", "role", "id"
            )
            for message in messages:
                result = {
                    "created_at": chat_history["created_at"],
                    "users_id": chat_history["users_id"],
                    "user_email": chat_history["user_email"],
                    "chat_history": chat_history["chat_history"],
                    "text": message["text"],
                    "role": message["role"],
                    "message_id": message["id"],
                }
                results.append(result)

        df = pd.DataFrame(results)
        return df

    def preprocess_text(self, text):
        tokens = text.split()
        tokens = [word.lower() for word in tokens if word.isalpha()]
        return tokens

    def process_user_names(self, user_names_column: pd.Series) -> pd.Series:
        # TODO: Use this function across the board when displaying User Names. Decide whether surname is needed.
        """
        Takes a pandas column and returns a dictionary of key value pairs for the tidy name.
        This function tidies user names instead of their emails.
        At a later date we could add an option for anonymyty (especially useful when presenting).
        """
        unique_user_email = user_names_column.unique()
        unique_user_names = [user_email.split("@")[0].replace(".", " ").title() for user_email in unique_user_email]
        user_name_dict = dict(zip(unique_user_email, unique_user_names, strict=False))
        new_user_names_column = user_names_column.map(user_name_dict)
        print(type(new_user_names_column))
        return new_user_names_column

    def get_user_frequency(self) -> pd.DataFrame:
        """
        Creates a data frame of total inputs by user.
        """
        user_counts = self.user_responses["user_email"].value_counts().reset_index(name="values")
        user_counts["user_email"] = self.process_user_names(user_counts.user_email)
        return user_counts

    def plot_user_frequency(self):
        """
        Generates a bar plot of total inputs per user.
        """
        user_counts = self.get_user_frequency()
        plt.figure(figsize=self.figsize)
        sns.barplot(data=user_counts, x="user_email", y="values", palette="viridis")
        plt.title("Unique Users by Total Number of Messages")
        xlabels = user_counts.user_email
        xlabels_new = ["\n".join(textwrap.wrap(name, width=10)) for name in xlabels]
        plt.xticks(range(len(xlabels_new)), xlabels_new)
        plt.xlabel("Users")
        plt.ylabel("Total No. of Prompts")

    def get_redbox_traffic(self) -> pd.DataFrame:
        """
        Returns a dataframe of redbox usage by time.
        """
        redbox_traffic_df = (
            self.user_responses["created_at"].groupby(by=self.user_responses["created_at"].dt.date).count()
        )

        return redbox_traffic_df

    def plot_redbox_traffic(self):
        """
        Generates a line plot of redbox usage over time
        """
        redbox_traffic_df = self.get_redbox_traffic()
        plt.figure(figsize=self.figsize)
        redbox_traffic_df.plot(kind="line")
        plt.title("Usage of Redbox AI Over Time")
        plt.xlabel("Date")
        plt.ylabel("Number of Prompts")

    def get_redbox_traffic_by_user(self) -> pd.DataFrame:
        """
        Returns a dataframe of redbox usage by user over time.
        """
        user_responses = self.user_responses
        user_responses["user_email"] = self.process_user_names(user_responses["user_email"])
        redbox_traffic_by_user_df = (
            user_responses.groupby([user_responses["created_at"].dt.date, "user_email"]).size().unstack(fill_value=0)
        )

        return redbox_traffic_by_user_df

    def plot_redbox_traffic_by_user(self):
        """
        Generates a plot of redbox usage by user over time
        """
        redbox_traffic_by_user_df = self.get_redbox_traffic_by_user()
        plt.figure(figsize=self.figsize)
        fig = sns.lineplot(data=redbox_traffic_by_user_df, markers=True)
        fig.set_xlabel("Date")
        fig.set_ylabel("No. of Prompts")
        fig.set_title("Usage of Redbox by User over Time")
        sns.move_legend(fig, "upper left", bbox_to_anchor=(1, 1), title="Users")

    def get_user_word_frequency(self) -> pd.DataFrame:
        """
        Returns a dataframe with word frequency, removing stopwords.
        """
        all_tokens = [token for tokens in self.user_responses["tokens"] for token in tokens]
        stopwords_removed_from_all_tokens = [word for word in all_tokens if word not in STOPWORDS]
        word_freq = Counter(stopwords_removed_from_all_tokens)

        return word_freq

    def get_ai_word_frequency(self) -> pd.DataFrame:
        """
        Returns a dataframe with word frequency, removing stopwords.
        """
        ai_word_freq = Counter(
            [token for tokens in self.ai_responses["tokens"] for token in tokens if token not in STOPWORDS]
        )
        return ai_word_freq

    def plot_user_wordcloud(self):
        """
        Creates wordcloud of user prompts.
        """
        word_freq = self.get_user_word_frequency()

        # TODO: assess value
        wordcloud = WordCloud(width=800, height=400, background_color="white").generate_from_frequencies(word_freq)
        plt.figure(figsize=self.figsize)
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.title("Most Frequent Words")

    def plot_top_user_word_frequency(self):
        """
        Creates bar plot of most common user words.
        """
        word_freq = self.get_user_word_frequency()
        most_common_words = word_freq.most_common(
            20  # TODO - determine how many common words we want and the right vis. for this
        )
        words, counts = zip(*most_common_words, strict=False)
        plt.figure(figsize=self.figsize)
        sns.barplot(x=list(counts), y=list(words), palette="viridis")
        plt.title("Top 20 Most Frequent Words")
        plt.xlabel("Frequency")
        plt.ylabel("Words")

    def plot_ai_wordcloud(self):
        """
        Creates wordcloud of AI outputs.
        """
        ai_word_freq = self.get_ai_word_frequency()
        # TODO - assess value
        ai_wordcloud = WordCloud(width=800, height=400, background_color="white").generate_from_frequencies(
            ai_word_freq
        )
        plt.figure(figsize=self.figsize)
        plt.imshow(ai_wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.title("Most Frequent Words in AI Responses")

    def plot_top_ai_word_frequency(self):
        """
        Creates bar plot of most common user words.
        """
        ai_word_freq = self.get_ai_word_frequency()

        most_common_words = ai_word_freq.most_common(
            20
        )  # TODO - determine how many common words we want and the right vis. for this

        words, counts = zip(*most_common_words, strict=False)
        plt.figure(figsize=self.figsize)
        sns.barplot(x=list(counts), y=list(words), palette="viridis")
        plt.title("Top 20 Most Frequent Words")
        plt.xlabel("Frequency")
        plt.ylabel("Words")

    # 5) Is there a clear pattern behind AI responses?
    def ai_response_pattern_analysis(self):
        def clean_text(
            text,
        ):  # was including asterisks giving useless info to the graph I'm still not entirely convinced on the benefit of this analysis
            return re.sub("[!@#$*]", "", text).strip()

        self.ai_responses["clean_text"] = self.ai_responses["text"].apply(clean_text)
        ai_response_patterns = (
            self.ai_responses["clean_text"].apply(lambda x: " ".join(x.split()[:2])).value_counts().head(10)
        )

        # Table
        words, counts = zip(
            *self.ai_responses["clean_text"].apply(lambda x: " ".join(x.split()[:2])).value_counts(), strict=False
        )
        table_data = {"Word": words, "Frequency": counts}
        table_dataframe = pd.DataFrame(data=table_data)
        table_dataframe.to_csv(f"{self.table_dir}common_ai_patterns.csv", index=False)

        # Barplot
        plt.figure(figsize=self.figsize)
        sns.barplot(x=ai_response_patterns.values, y=ai_response_patterns.index, palette="magma")
        plt.title("Common Patterns in AI Responses")
        plt.xlabel("Frequency")
        plt.ylabel("Patterns")
        ai_patterns_path = os.path.join(self.visualisation_dir, "common_ai_patterns.png")
        plt.savefig(ai_patterns_path)

    # What routes are people using?
    def route_analysis(self):
        df = self.user_responses.copy()

        # # Some users repeat the same message several times (drop?)
        # df = df.drop_duplicates(['text'])

        # User names
        user_name = [user_email.split("@")[0].replace(".", " ").title() for user_email in df.user_email]
        wrapped_user_name = ["\n".join(textwrap.wrap(name, width=10)) for name in user_name]
        df["user_name"] = wrapped_user_name

        # Groupby routes
        df_grouped = df.groupby(["user_name"])["route"].value_counts().unstack()

        # Plot
        plt.figure(figsize=self.figsize)
        df_grouped.plot(
            kind="bar", color={"chat": "teal", "no_route": "yellowgreen", "summarise": "gold"}, figsize=self.figsize
        )
        plt.xticks(rotation=0)
        plt.xlabel("Users")
        plt.ylabel("Number of routes taken")
        plt.title("Routes taken per user")
        routes_count_path = os.path.join(self.visualisation_dir, "routes_per_user.png")
        plt.savefig(routes_count_path)

    def get_route_transitions(self, df):
        # TODO Check this works with the groupby ID and time order of events
        df["next_route"] = df["route"].shift(1)

        df["transition"] = df.apply(
            lambda row: f"{row['route']} to {row['next_route']}" if pd.notna(row["next_route"]) else None, axis=1
        )

        return df

    # In what way are users switching between routes?
    def route_transitions(self):
        # Get route transitions and counts per user session (is 'id' appropriate?)
        df_transitions = (
            self.user_responses.groupby("message_id").apply(self.get_route_transitions).reset_index(drop=True)
        )

        transition_counts = df_transitions["transition"].value_counts().reset_index()

        # Plot
        sns.barplot(x=transition_counts["transition"], y=transition_counts["count"], palette="viridis")
        plt.xticks(rotation=45, ha="right")
        plt.title("Number of different route transitions")
        plt.xlabel("Route transition")
        plt.ylabel("Number of route transitions")

    # Are users asking about common topics?
    def get_topics(self):
        STOPWORDS.add("@chat")
        STOPWORDS.add("@summarise")

        # Remove stopwords and fit (simple) topic model
        text_without_stopwords = self.user_responses["text"].apply(
            lambda row: " ".join([word for word in row.split() if word not in (STOPWORDS)])
        )
        created_at = self.user_responses["created_at"].to_list()

        topic_model = BERTopic(verbose=True)
        topic_model.fit_transform(text_without_stopwords)
        topics_over_time = topic_model.topics_over_time(text_without_stopwords, created_at)

        self.topic_model = topic_model
        self.topics_over_time = topics_over_time

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
        return self.topic_model.visualize_topics_over_time(
            self.topics_over_time, top_n_topics=5, normalize_frequency=True
        )

    def get_prompt_lengths(self):
        """
        Adds the prompt lengths to the user prompt column
        """
        user_responses_df = self.user_responses
        user_responses_df["no_input_words"] = user_responses_df["text"].apply(lambda n: len(n.split()))
        return user_responses_df

    def filter_prompt_lengths(self, outlier_max: int):
        """
        Creates option to filter for outliers
        """
        user_responses_df = self.get_prompt_lengths()
        user_responses_df = user_responses_df[user_responses_df["no_input_words"] < outlier_max]
        return user_responses_df

    def visualise_prompt_lengths(self, outlier_max: int):
        """
        How does prompt length vary?
        """
        user_responses_df = self.filter_prompt_lengths(outlier_max)
        fig = sns.displot(user_responses_df["no_input_words"])
        fig.set_axis_labels(x_var="No. of words in prompt", y_var="Count")

    def get_prompt_length_vs_chat_length(self, outlier_max: int):
        """
        Compares average prompt length with chat length.
        """
        user_responses_df = self.filter_prompt_lengths(outlier_max)
        mean_inputs_df = (
            user_responses_df[["message_id", "user_email", "no_input_words"]]
            .groupby(by=["message_id", "user_email"])
            .agg({"no_input_words": "mean"})
            .rename(columns={"no_input_words": "mean_input_words"})
            .reset_index()
        )
        no_inputs_df = (
            user_responses_df[["message_id", "user_email"]]
            .groupby("message_id")
            .value_counts()
            .reset_index(name="no_inputs")
        )
        compare_inputs_words_df = no_inputs_df.merge(
            mean_inputs_df, left_on=["message_id", "user_email"], right_on=["message_id", "user_email"]
        )

        return compare_inputs_words_df

    def vis_prompt_length_vs_chat_legnth(self, outlier_max: int):
        compare_inputs_words_df = self.get_prompt_length_vs_chat_length(outlier_max=outlier_max)
        compare_inputs_words_df["user_email"] = self.process_user_names(compare_inputs_words_df.user_email)
        fig = sns.scatterplot(data=compare_inputs_words_df, x="no_inputs", y="mean_input_words", hue="user_email")
        fig.set_xlabel("No. of prompts")
        fig.set_ylabel("Mean length of prompt")
        fig.set_title("Scatter plot comparing number of prompts with the length of prompt for each user session")
        sns.move_legend(fig, "upper left", bbox_to_anchor=(1, 1))


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
