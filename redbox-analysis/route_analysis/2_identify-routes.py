# Set up
import pandas as pd
from datetime import datetime

# Specify path to data
joined_path = '/Users/morgan.frodsham/PycharmProjects/redbox-analysis/route_analysis/joined_usage_data.csv'

# Load csv files into dataframe
joined_df = pd.read_csv(joined_path)
print(len(joined_df))

# Convert message_created_at and chat_created_at columns to datetime
joined_df['message_created_at'] = pd.to_datetime(joined_df['message_created_at'])
joined_df['chat_created_at'] = pd.to_datetime(joined_df['chat_created_at'])
print(len(joined_df))

# Sort dataframe by message_created_at
sorted_df = joined_df.sort_values(by='message_created_at')

# Create a new column to store the updated route for users
sorted_df['user_route'] = sorted_df['route'].shift(-1)

# Replace blank values in 'route' and 'user_route'
sorted_df['route'] = sorted_df['route'].replace('', pd.NA)  # Convert empty strings to NaN
sorted_df['user_route'] = sorted_df['user_route'].replace('', pd.NA)  # Convert empty strings to NaN

# Fill blank values in 'route' with values from 'user_route' and vice versa
sorted_df['route'] = sorted_df['route'].combine_first(sorted_df['user_route'])
sorted_df['user_route'] = sorted_df['user_route'].combine_first(sorted_df['route'])

# Join the two columns into a new column
sorted_df['model_route'] = sorted_df.apply(
    lambda x: f"{x['route']}" if x['role'] == 'user' else x['route'], axis=1)

# Drop the original 'route' and 'user_route' columns
sorted_df.drop(columns=['route', 'user_route'], inplace=True)

# Save the sorted dataframe
sorted_df.to_csv('sorted_usage_data.csv', index=False)