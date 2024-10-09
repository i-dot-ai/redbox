# Set up
import pandas as pd
import plotly.express as px

# Specify path to data
joined_path = '/survey_usage_analysis/joined_data.csv'
filtered_joined_path = '/survey_usage_analysis/filtered_joined_data.csv'

# Load csv file into dataframe
joined_df = pd.read_csv(joined_path)
filtered_joined_df = pd.read_csv(filtered_joined_path)

# Display the dataframe
print(joined_df)
print(filtered_joined_df)

# Get number unique users
unique_users = joined_df['email'].nunique()
print("Number of unique users:", unique_users) #122

# Get number of unique users who are staff
staff_users = joined_df[joined_df['is_staff'] == True]['email'].nunique()
print("Number of unique staff users:", staff_users) #10 - has access to the admin

# Filter out staff members
non_staff_df = filtered_joined_df[filtered_joined_df['is_staff'] == False]
print(non_staff_df)

# Check it worked
print(len(non_staff_df[non_staff_df['is_staff'] == False].email.unique())) #87

# How many messages are sent by each user?
message_counts_per_user = non_staff_df.groupby('email')['message_id'].count()
message_counts_per_user = message_counts_per_user.sort_values(ascending=False)
print(message_counts_per_user.head(10))

# How many files are sent by each user?
file_counts_per_user = non_staff_df.groupby('email')['selected_files'].count()
file_counts_per_user = file_counts_per_user.sort_values(ascending=False)
print(file_counts_per_user.head(10))

# How many users have a disability?
print(len(non_staff_df[non_staff_df['disability'] == 'Yes'].email.unique())) #17

# How many users have each disability type?
no_duplicates = non_staff_df.drop_duplicates(subset='email')
disability_counts_by_email = no_duplicates['disability_category'].value_counts()
print(disability_counts_by_email)

# How many users are there in each profession?
profession_counts_survey = no_duplicates['profession_survey'].value_counts()
print(profession_counts_survey)

profession_counts_profile = no_duplicates['profession_profile'].value_counts()
print(profession_counts_profile)

# How many users are there in each grade?
grade_counts_survey = no_duplicates['grade_survey'].value_counts()
print(grade_counts_survey)

grade_counts_profile = no_duplicates['grade_profile'].value_counts()
print(grade_counts_profile)

# What is the technology confidence of our users?
tech_confidence_counts = no_duplicates['tech_confidence'].value_counts()
print(tech_confidence_counts)

# What is the genai use of our users?
genai_use_counts_register = no_duplicates['register_genai_use'].value_counts()
print(genai_use_counts_register)

genai_use_counts_survey= no_duplicates['common_genai_use'].value_counts()
print(genai_use_counts_survey)

# What is the genai use of our users at work?
genai_use_counts_work = no_duplicates['work_use'].value_counts()
print(genai_use_counts_work)

# What is the genai use of our users at home?
genai_use_counts_home = no_duplicates['home_use'].value_counts()
print(genai_use_counts_home)

# What is the genai usefulness for our users?
genai_usefulness_counts = no_duplicates['usefulness'].value_counts()
print(genai_usefulness_counts)

# How often do they summarise large documents?
large_doc_freq_counts = no_duplicates['large_doc_frequency'].value_counts()
print(large_doc_freq_counts)

# How long does it take to summarise large documents?
large_doc_time_counts = no_duplicates['large_doc_time'].value_counts()
print(large_doc_time_counts)

# How often do they condense multiple documents?
condense_doc_freq_counts = no_duplicates['condense_doc_frequency'].value_counts()
print(condense_doc_freq_counts)

# How long does it take to condense multiple documents?
condense_doc_time_counts = no_duplicates['condense_doc_time'].value_counts()
print(condense_doc_time_counts)

# How often do they search documents?
search_doc_freq_counts = no_duplicates['search_doc_frequency'].value_counts()
print(search_doc_freq_counts)

# How long does it take to search documents?
search_doc_time_counts = no_duplicates['search_doc_time'].value_counts()
print(search_doc_time_counts)

# How often do they compare documents?
compare_doc_freq_counts = no_duplicates['compare_doc_frequency'].value_counts()
print(compare_doc_freq_counts)

# How long does it take to compare documents?
compare_doc_time_counts = no_duplicates['compare_doc_time'].value_counts()
print(compare_doc_time_counts)

# How often do they create template documents?
template_doc_freq_counts = no_duplicates['template_doc_frequency'].value_counts()
print(template_doc_freq_counts)

# How long does it take to create template documents?
template_doc_time_counts = no_duplicates['template_doc_time'].value_counts()
print(template_doc_time_counts)

# How often do they shorten documents?
shorten_doc_freq_counts = no_duplicates['shorten_doc_frequency'].value_counts()
print(shorten_doc_freq_counts)

# How long does it take to shorten documents?
shorten_doc_time_counts = no_duplicates['shorten_doc_time'].value_counts()
print(shorten_doc_time_counts)

# How often do they create meeting documents?
meeting_doc_freq_counts = no_duplicates['meeting_doc_frequency'].value_counts()
print(meeting_doc_freq_counts)

# How long does it take to create meeting documents?
meeting_doc_time_counts = no_duplicates['meeting_doc_time'].value_counts()
print(meeting_doc_time_counts)