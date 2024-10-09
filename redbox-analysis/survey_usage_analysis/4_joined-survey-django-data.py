# Set up
import pandas as pd

# Specify path to data
user_joined_path = '/survey_usage_analysis/user_joined.csv'
survey_joined_path = '/survey_usage_analysis/survey_joined.csv'

# Load csv files into dataframe
user_df = pd.read_csv(user_joined_path)
survey_df = pd.read_csv(survey_joined_path)

# Display the dataframe
print(user_df)
print(survey_df)

# Get unique users from user_df (as we have more survey submissions than current users)
unique_users = user_df['email'].unique()

# Filter survey_df by unique users in user_df
filtered_survey_df = survey_df[survey_df['email'].isin(unique_users)]

# Check the filter worked
print(filtered_survey_df)

# Get unique users from filtered_survey_df (as some current users have not completed the survey)
unique_users_survey = filtered_survey_df['email'].unique()

# Filter user_df by unique users filtered_survey_df
filtered_user_df = user_df[user_df['email'].isin(unique_users_survey)]

# Join user_df and survey_filtered_df
filtered_joined_data_df = pd.merge(filtered_user_df, filtered_survey_df, on='email', how='left')

# Check the joining worked
print(filtered_joined_data_df)

# Tidy up the names of the columns
filtered_joined_data_df = filtered_joined_data_df.rename(columns={'grade_x':'grade_profile', 'grade_y':'grade_survey', 'profession_x':'profession_profile', 'profession_y':'profession_survey'})

# Save the joined dataframe
filtered_joined_data_df.to_csv('filtered_joined_data.csv', index=False)

