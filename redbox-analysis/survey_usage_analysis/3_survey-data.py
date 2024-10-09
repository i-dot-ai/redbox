# Set up
import pandas as pd

# Specify path to data
register_path = '/Users/morgan.frodsham/Documents/redbox_data/register-interest.csv' #Register Your Interest survey output
common_path = '/Users/morgan.frodsham/Documents/redbox_data/common-tasks.csv' #Common tasks survey output

# Load csv files into dataframe
register_df = pd.read_csv(register_path)
common_df = pd.read_csv(common_path)

# Display the dataframe
print(register_df)
print(common_df)

# Join the dataframes
joined_df = pd.merge(common_df, register_df, on = 'Email address', how = 'left')

# Display the new dataframe
print(joined_df)

# Check if there are any duplicate emails
email_counts = joined_df['Email address'].value_counts()
duplicate_emails = email_counts[email_counts > 1]
total_duplicates = duplicate_emails.sum() - len(duplicate_emails)
print(total_duplicates)

# Remove rows of any duplicate emails that may be there
survey_joined_df = joined_df.drop_duplicates(subset = 'Email address', keep = 'first')

# Remove empty columns
survey_joined_df = survey_joined_df.drop(['Profession', 'Business Unit', 'Is in Pilot Group?', 'UR Participant code', 'Disability or condition',
                                          'Please tell us what you give permission for, by selecting the answers you want to give:', 'Your agreement',
                                          'Invite sent to 9 Apr session?', 'Response to 9 Apr session', 'In MVP user sessions 17-May & 24-May', 'Has Access',
                                          'Preprod tester', 'Send nudge email 20240702', 'Comments', 'Yex'], axis=1)
# Tidy up the names of the columns
survey_joined_df = survey_joined_df.rename(columns={'Email address':'email', 'Timestamp_x':'common_date_time',
                                                    'Which statement best describes your level of experience with Generative AI (GenAI)?':'common_genai_use',
                                                    'At WORK, how often have you used GenAI like ChatGPT, Claude or Gemini?':'work_use',
                                                    'OUTSIDE of work, how often have you used GenAI like ChatGPT, Claude or Gemini?':'home_use',
                                                    'How useful have you found GenAI?':'usefulness',
                                                    'What is your role?':'common_role',
                                                    'TASK 1 - Please describe the task':'task_1',
                                                    'TASK 1 - How often do you do this?':'task_1_frequency',
                                                    'TASK 1 - How long does it take you to do this?':'task_1_time',
                                                    'TASK 1 - Would you consider using GenAI to assist you with this?':'task_1_genai',
                                                    'TASK 2 - Please describe the task':'task_2',
                                                    'TASK 2 - How often do you do this?':'task_2_frequency',
                                                    'TASK 2 - How long does it take you to do this?':'task_2_time',
                                                    'TASK 2 - Would you consider using GenAI to assist you with this?':'task_2_genai',
                                                    'TASK 3 - Please describe the task':'task_3',
                                                    'TASK 3 - How often do you do this?':'task_3_frequency',
                                                    'TASK 3 - How long does it take you to do this?':'task_3_time',
                                                    'TASK 3 - Would you consider using GenAI to assist you with this?':'task_3_genai',
                                                    'Please indicate how often you do the following document-focused tasks in your role [Summarise large documents (50+ pages)]':'large_doc_frequency',
                                                    'Please indicate how often you do the following document-focused tasks in your role [Condense multiple documents into one summary]':'condense_doc_frequency',
                                                    'Please indicate how often you do the following document-focused tasks in your role [Search across many documents to answer a question]':'search_doc_frequency',
                                                    'Please indicate how often you do the following document-focused tasks in your role [Compare the same information across multiple documents]':'compare_doc_frequency',
                                                    'Please indicate how often you do the following document-focused tasks in your role [Write documents in a specific template, style or format]':'template_doc_frequency',
                                                    'Please indicate how often you do the following document-focused tasks in your role [Edit draft documemnts to shorten or simplify]':'shorten_doc_frequency',
                                                    'Please indicate how often you do the following document-focused tasks in your role [Write documents to facilitate meetings (chair briefs, agendas, minutes)]':'meeting_doc_frequency',
                                                    'Please indicate how much time each of the following document tasks take [Summarise large documents (50+ pages)]': 'large_doc_time',
                                                    'Please indicate how much time each of the following document tasks take [Condense multiple documents into one summary]': 'condense_doc_time',
                                                    'Please indicate how much time each of the following document tasks take [Search across many documents to answer a question]': 'search_doc_time',
                                                    'Please indicate how much time each of the following document tasks take [Compare the same information across multiple documents]': 'compare_doc_time',
                                                    'Please indicate how much time each of the following document tasks take [Write documents in a specific template, style or format]': 'template_doc_time',
                                                    'Please indicate how much time each of the following document tasks take [Edit draft documemnts to shorten or simplify]': 'shorten_doc_time',
                                                    'Please indicate how much time each of the following document tasks take [Write documents to facilitate meetings (chair briefs, agendas, minutes)]': 'meeting_doc_time',
                                                    'Timestamp_y':'register_date_time',
                                                    'What Business Unit are you part of you? ':'business_unit',
                                                    'What Grade (or equivalent) are you?':'grade',
                                                    'What profession do you most identify with?':'profession',
                                                    "What's your role?":'role',
                                                    'Do you have any conditions or disabilities which may have an impact on your day to day life?':'disability',
                                                    "If you answered 'yes', which of the following categories would you class yourself in?":'disability_category',
                                                    'How do these conditions or disabilities affect your use of technology and/or online services?':'disability_effect_tech',
                                                    'Which statement best describes you?':'tech_confidence',
                                                    'How often have you used GenAI tools like ChatGPT, Claude or Gemini?':'register_genai_use',
                                                    'What tasks are you hoping to use Redbox for?':'desired_tasks',
                                                    'In MVP pilot group (Cohort 1)':'pilot_group',
                                                    'Next 100 users':'first_100',
                                                    'Second 100 users':'second_100',
                                                    'AskAI user':'askai_user'})

# Save the joined dataframe
survey_joined_df.to_csv('survey_joined.csv', index=False)

