# Set up
import pandas as pd

# Specify path to data
chat_path = '/Users/morgan.frodsham/Documents/redbox_data/chat.csv'
message_path = '/Users/morgan.frodsham/Documents/redbox_data/message.csv'


# Load csv files into dataframe
chat_df = pd.read_csv(chat_path)
message_df = pd.read_csv(message_path)

# Display the dataframe
print(chat_df)
print(message_df)

# Tidy up the names of the columns
chat_df = chat_df.rename(columns={'id':'message_id', 'user':'user_id'})
message_df = message_df.rename(columns={'chat':'message_id'})

# Check if all 'message_id' values in chat_df are in message_df
match_id_chat_df = message_df['message_id'].isin(chat_df['message_id']).all()
match_id_message_df = chat_df['message_id'].isin(message_df['message_id']).all()
message_id_columns_match = match_id_chat_df and match_id_message_df
print(message_id_columns_match)

# Join chat_df and message_df
chat_joined_df = pd.merge(message_df, chat_df, on=['message_id'], how='left')

# Check joining worked
print(chat_joined_df)

chat_joined_df.drop('text', axis=1, inplace=True)

# Save the joined dataframe
chat_joined_df.to_csv('chat_joined.csv', index=False)