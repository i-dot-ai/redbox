# Set up
import pandas as pd

# Specify path to data
user_path = '/survey_usage_analysis/user_joined.csv'
cost_path = '/Users/morgan.frodsham/Documents/redbox-user-research/user_cost.csv'

# Load csv file into dataframe
user_df = pd.read_csv(user_path)
cost_df = pd.read_csv(cost_path)

# Display the first few rows of user_df to check the 'route' column
print("user_df - first rows:")
print(user_df[['email', 'route']].head())  # Check if 'route' has values before the merge

# Join the two dataframes together, keeping the 'route' column
user_cost_joined = pd.merge(user_df, cost_df[['history_user', 'total_cost', 'mean_cost', 'max_cost']],
                            left_on='email',
                            right_on='history_user',
                            how='left')

# Drop the 'history_user' column as it is no longer needed
user_cost_joined = user_cost_joined.drop(columns=['history_user'])

# Display the first few rows after the merge to inspect the 'route' column
print("\nuser_cost_joined - after merge:")
print(user_cost_joined[['email', 'route', 'total_cost']].head())

# Filter the dataframe to remove rows where 'role' is 'ai'
user_cost_joined = user_cost_joined[user_cost_joined['role'] != 'ai']

### TASK 1: Frequency of messages and unique routes

# Custom function to collect unique routes for each user
def collect_routes(routes):
    return list(routes.dropna().unique())

# Part 1: Count how many messages each user has sent (message count)
message_counts = user_cost_joined.groupby('email')['email'].count().reset_index(name='message_count')

# Part 2: Collect all unique routes per user using groupby().apply()
route_aggregation = user_cost_joined.groupby('email')['route'].apply(collect_routes).reset_index(name='unique_routes')

# Merge message counts and route aggregation
user_counts = pd.merge(message_counts, route_aggregation, on='email')

# Display the results
print("\nMerged message counts and routes:")
print(user_counts[['email', 'message_count', 'unique_routes']].head())

# Rank the users based on the message count (frequency) in descending order
user_counts['message_rank'] = user_counts['message_count'].rank(method='dense', ascending=False)

# Sort the dataframe by the message count to see the ranking
user_counts = user_counts.sort_values(by='message_count', ascending=False)

# Get the top 10
top_10 = user_counts.head(10)

# Get the bottom 10
bottom_10 = user_counts.tail(10)

# Get 10 rows from the middle
middle_index = len(user_counts) // 2  # Find the middle index
middle_10 = user_counts.iloc[middle_index-5:middle_index+5]  # Select 5 before and 5 after the middle

# Display the results
print("Top 10 by message count:")
print(top_10)

print("\nMiddle 10 by message count:")
print(middle_10)

print("\nBottom 10 by message count:")
print(bottom_10)

### TASK 2: Highest spending users

# Remove rows where 'total_cost' is NaN
user_cost_joined_filtered = user_cost_joined.dropna(subset=['total_cost']).copy()

# Group by 'email' and take the first value for each user
user_cost_joined_filtered = user_cost_joined_filtered.groupby('email').first().reset_index()

# Rank users based on 'total_cost' in descending order
user_cost_joined_filtered['cost_rank'] = user_cost_joined_filtered['total_cost'].rank(method='dense', ascending=False)

# Sort the dataframe by 'total_cost' in descending order
user_cost_joined_filtered_sorted = user_cost_joined_filtered.sort_values(by='total_cost', ascending=False).reset_index(drop=True)

# Get the top 10 users by 'total_cost'
top_10_cost = user_cost_joined_filtered_sorted[['email', 'total_cost', 'cost_rank']].head(10)

# Get the bottom 10 users by 'total_cost'
bottom_10_cost = user_cost_joined_filtered_sorted[['email', 'total_cost', 'cost_rank']].tail(10)

# Get 10 users from the middle by 'total_cost'
middle_index_cost = len(user_cost_joined_filtered_sorted) // 2  # Find the middle index
middle_10_cost = user_cost_joined_filtered_sorted[['email', 'total_cost', 'cost_rank']].iloc[middle_index_cost-5:middle_index_cost+5]  # Select 5 before and 5 after the middle

# Display the results
print("Top 10 users by cost:")
print(top_10_cost)

print("\nMiddle 10 users by cost:")
print(middle_10_cost)

print("\nBottom 10 users by cost:")
print(bottom_10_cost)

### TASK 3: User spend and frequency with routes

# Merge the frequency and route data with the total cost data
email_analysis = pd.merge(user_counts, user_cost_joined_filtered, on='email')

# Sort the dataframe by 'total_cost' to get top, middle, and bottom users
email_analysis = email_analysis.sort_values(by='total_cost', ascending=False).reset_index(drop=True)

# Step 6: Get the top 10 users by 'total_cost'
top_10_users = email_analysis[['email', 'message_count', 'unique_routes', 'total_cost', 'cost_rank']].head(10)

# Step 7: Get the bottom 10 users by 'total_cost'
bottom_10_users = email_analysis[['email', 'message_count', 'unique_routes', 'total_cost', 'cost_rank']].tail(10)

# Step 8: Get 10 users from the middle by 'total_cost'
middle_index = len(email_analysis) // 2
middle_10_users = email_analysis[['email', 'message_count', 'unique_routes', 'total_cost', 'cost_rank']].iloc[middle_index-5:middle_index+5]

# Step 9: Display the results
print("Top 10 spending users and their frequency of use (with routes):")
print(top_10_users)

print("\nMiddle 10 spending users and their frequency of use (with routes):")
print(middle_10_users)

print("\nBottom 10 spending users and their frequency of use (with routes):")
print(bottom_10_users)

### SAVE ANALYSIS

# Remove unneeded columns
email_analysis = email_analysis.drop(columns=['id', 'created_at_y', 'modified_at_y', 'message_id', 'text', 'role', 'last_token_sent_at', 'selected_files', 'source_files', 'created_at_x', 'modified_at_x', 'name', 'is_staff', 'is_active'])

# Save the email_analysis dataframe with route details included
email_analysis.to_csv('user_cost_frequency_routes_detailed.csv', index=False)
