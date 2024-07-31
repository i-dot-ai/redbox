from analysis_of_chat_history import ChatHistoryAnalysis
import streamlit as st

st.set_page_config(page_title = 'Redbox Chat Analysis', layout = 'centered')
st.set_option('deprecation.showPyplotGlobalUse', False)
st.title('Redbox Chat History Dashboard')

user_freq_tab, traffic_tab, word_freq_tab, ai_word_freq_tab, route_tab, transitions_tab, topic_tab = st.tabs(['User frequency',
                                                                                                            'Redbox traffic',
                                                                                                            'Word frequency',
                                                                                                            'AI word frequency',
                                                                                                            'Route analysis',
                                                                                                            'Route transitions',
                                                                                                            'Topic modelling'])

cha = ChatHistoryAnalysis()

with user_freq_tab:
    st.pyplot(cha.user_frequency_analysis())

with traffic_tab:
    st.pyplot(cha.redbox_traffic_analysis())

with word_freq_tab:
    st.pyplot(cha.user_word_frequency_analysis())

with ai_word_freq_tab:
    st.pyplot(cha.ai_word_frequency_analysis())

with route_tab:
    st.pyplot(cha.route_analysis())

with transitions_tab:
    st.pyplot(cha.route_transitions())

with topic_tab:
    with st.spinner('Fitting topic model...'):
        cha.get_topics()
    
    st.plotly_chart(cha.visualise_topics())
    st.plotly_chart(cha.visualise_topics_over_time())
    st.plotly_chart(cha.visualise_barchart())
    st.plotly_chart(cha.visualise_hierarchy())
