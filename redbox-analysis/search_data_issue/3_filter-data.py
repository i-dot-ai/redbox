# Set up
import pandas as pd
from datetime import datetime

# Specify path to data
user_joined_path = '/Users/morgan.frodsham/PycharmProjects/redbox-analysis/data_issue/user_joined.csv'

# Load csv files into dataframe
user_joined_df = pd.read_csv(user_joined_path)

# Convert created column to datetime
user_joined_df['created_at_x'] = pd.to_datetime(user_joined_df['created_at_x'])
print(len(user_joined_df))

# Filter by datetime
user_joined_df = user_joined_df[user_joined_df['created_at_x'] > datetime(year=2024, month=9, day=12)]
print(len(user_joined_df))

# Save the joined dataframe
user_joined_df.to_csv('user_joined_filtered.csv', index=False)