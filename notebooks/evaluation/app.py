import streamlit as st
from analysis_of_chat_history import ChatHistoryAnalysis

st.set_page_config(page_title="Redbox Chat Analysis", layout="centered")
st.set_option("deprecation.showPyplotGlobalUse", False)
st.title("Redbox Chat History Dashboard")

user_usage_tab, word_freq_tab, route_tab, topic_tab, prompt_complex = st.tabs(
    [
        "Redbox User Usage",
        "Word frequency",
        "Route Analysis",
        "Topic modelling",
        "Prompt Complexity",
    ]
)

cha = ChatHistoryAnalysis()

with user_usage_tab:
    st.pyplot(cha.user_frequency_analysis())
    st.pyplot(cha.redbox_traffic_analysis())
    st.pyplot(cha.redbox_traffic_by_user())

with word_freq_tab:
    st.subheader("User")
    st.pyplot(cha.user_word_frequency_analysis())
    st.subheader("AI")
    st.pyplot(cha.ai_word_frequency_analysis())

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
    outlier = st.slider("Please use the slicer if you wish to remove outliers.", 0, max_outlier, 700)
    st.pyplot(cha.visualise_prompt_lengths(outlier_max=outlier))
    st.pyplot(cha.vis_prompt_length_vs_chat_legnth(outlier_max=outlier))
