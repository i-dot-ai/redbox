# Set up
import pandas as pd

# Specify path to data
user_path = '/Users/morgan.frodsham/Documents/redbox_data/user.csv' #Django users export
chat_joined_path = '/Users/morgan.frodsham/PycharmProjects/redbox-analysis/survey_usage_analysis/chat_joined.csv'

# Load csv files into dataframe
user_df = pd.read_csv(user_path)
chat_joined_df = pd.read_csv(chat_joined_path)

# Display the dataframe
print(user_df)
print(chat_joined_df)

# Tidy up the names of the columns
user_df = user_df.rename(columns={'id':'user_id'})

# Check if all 'user_id' values in chat_df are in user_df
match_user_chat_df = user_df['user_id'].isin(chat_joined_df['user_id'].unique()).all()
match_user_user_df = chat_joined_df['user_id'].isin(user_df['user_id'].unique()).all()
user_columns_match = match_user_chat_df and match_user_user_df
print(user_columns_match)

# Check for duplicate user_ids
if chat_joined_df['user_id'].duplicated().any() or user_df['user_id'].duplicated().any():
    print("Duplicate user_ids found in one or both DataFrames")

# Join chat_joined_df and user_df
user_joined_df = pd.merge(chat_joined_df, user_df, on=['user_id'], how='left')

# Check joining worked
print(user_joined_df)

# Tidy up the names of the columns
user_joined_df = user_joined_df.rename(columns={'name_x':'chat_name', 'name_y':'user_name'})

# Save the joined dataframe
user_joined_df.to_csv('user_joined.csv', index=False)
