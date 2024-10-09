#Set up
import pandas as pd

# Specify path to data
chat_path = '/Users/morgan.frodsham/Documents/redbox_data/chat.csv' #Django chat export
message_path = '/Users/morgan.frodsham/Documents/redbox_data/message.csv' #Django chat messages export
token_path = '/Users/morgan.frodsham/Documents/redbox_data/token-use.csv' #Django chat messages export
user_path = '/Users/morgan.frodsham/Documents/redbox_data/user.csv' #Django chat messages export

# Load csv files into dataframe
chat_df = pd.read_csv(chat_path)
message_df = pd.read_csv(message_path)
token_df = pd.read_csv(token_path)
user_df = pd.read_csv(user_path)

# Tidy up the names of the columns
chat_df = chat_df.rename(columns={'id':'message_id', 'user':'user_id', 'created_at':'chat_created_at', 'chat_backend':'model'})
message_df = message_df.rename(columns={'chat':'message_id', 'created_at':'message_created_at'})
token_df = token_df.rename(columns={'id':'tokens_id','chat_message':'id', 'created_at':'tokens_created_at'})
user_df = user_df.rename(columns={'id':'user_id'})

# Remove model_name column as it's less complete that chat_backend
token_df = token_df.drop(['model_name'], axis=1)

# Check if all 'message_id' values in chat_df are in message_df
match_id_chat_df = message_df['message_id'].isin(chat_df['message_id']).all()
match_id_message_df = chat_df['message_id'].isin(message_df['message_id']).all()
message_id_columns_match = match_id_chat_df and match_id_message_df
print(message_id_columns_match) #True

# Join chat_df and message_df
joined_df = pd.merge(message_df, chat_df, on=['message_id'], how='left')

# Join joined_df and user_df
joined_df = pd.merge(joined_df, user_df, on=['user_id'], how='left')

# Join joined_df and user_df
joined_df = pd.merge(joined_df, token_df, on=['id'], how='left')

# Save the joined dataframe
joined_df.to_csv('joined_usage_data.csv', index=False)