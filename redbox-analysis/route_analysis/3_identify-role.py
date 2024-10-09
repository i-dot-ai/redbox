# Set up
import pandas as pd

# Specify path to data
sorted_path = '/Users/morgan.frodsham/PycharmProjects/redbox-analysis/route_analysis/sorted_usage_data.csv'

# Load csv files into dataframe
sorted_df = pd.read_csv(sorted_path)

# Split the DataFrame into two based on 'role'
user_df = sorted_df[sorted_df['role'] == 'user']
ai_df = sorted_df[sorted_df['role'] == 'ai']

# Display the resulting DataFrames
print("User DataFrame:")
print(user_df)
print("\nAI DataFrame:")
print(ai_df)

# Save new dataframes
user_df.to_csv('role_user.csv', index=False)
ai_df.to_csv('role_ai.csv', index=False)