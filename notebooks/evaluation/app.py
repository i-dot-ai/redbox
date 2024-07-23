import streamlit as st
from analysis_of_chat_history import ChatHistoryAnalysis

st.set_page_config(page_title="Redbox Chat Analysis", layout="centered")
st.set_option("deprecation.showPyplotGlobalUse", False)
st.title("Redbox Chat History Dashboard")

user_usage_tab, word_freq_tab, route_tab, topic_tab = st.tabs(
    [
        "Redbox User Usage",
        "Word frequency",
        "Route Analysis",
        "Topic modelling",
    ]
)

cha = ChatHistoryAnalysis()

with user_usage_tab:
    st.pyplot(cha.user_frequency_analysis())
    st.pyplot(cha.redbox_traffic_analysis())
    st.pyplot(cha.redbox_traffic_by_user())

with word_freq_tab:
    st.title("User")
    st.pyplot(cha.user_word_frequency_analysis())
    st.title("AI")
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
