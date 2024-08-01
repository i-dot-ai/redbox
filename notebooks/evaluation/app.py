import streamlit as st
from analysis_of_chat_history import ChatHistoryAnalysis

cha = ChatHistoryAnalysis()

st.set_page_config(page_title="Redbox Chat Analysis", layout="centered")
st.set_option("deprecation.showPyplotGlobalUse", False)
st.title("Redbox Chat History Dashboard")

on = st.toggle("Anonymise Users")
if on:
    cha.anonymise_users()

user_usage_tab, word_freq_tab, route_tab, topic_tab, prompt_complex = st.tabs(
    [
        "Redbox User Usage",
        "Word frequency",
        "Route Analysis",
        "Topic modelling",
        "Prompt Complexity",
    ]
)

with user_usage_tab:
    st.pyplot(cha.plot_user_frequency())
    st.pyplot(cha.plot_redbox_traffic())
    st.pyplot(cha.plot_redbox_traffic_by_user())

with word_freq_tab:
    st.subheader("User")
    st.pyplot(cha.plot_user_wordcloud())
    st.pyplot(cha.plot_top_user_word_frequency())
    st.subheader("AI")
    st.pyplot(cha.plot_ai_wordcloud())
    st.pyplot(cha.plot_top_ai_word_frequency())

with route_tab:
    st.pyplot(cha.route_analysis())
    st.pyplot(cha.route_transitions())

with topic_tab:
    with st.spinner("Fitting topic model..."):
        cha.get_topics()

    st.plotly_chart(cha.visualise_topics())
    st.plotly_chart(cha.visualise_topics_over_time())
    st.plotly_chart(cha.visualise_barchart())
    st.plotly_chart(cha.visualise_hierarchy())

with prompt_complex:
    # Adding slider for prompt legnth
    max_outlier = cha.get_prompt_lengths()["no_input_words"].max() + 10
    outlier = st.slider("Please use the slicer if you wish to remove outliers.", 0, max_outlier, max_outlier)
    st.pyplot(cha.visualise_prompt_lengths(outlier_max=outlier))
    st.pyplot(cha.vis_prompt_length_vs_chat_legnth(outlier_max=outlier))
