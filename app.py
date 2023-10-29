import os
import re
import openai
import tiktoken
import pandas as pd
import numpy as np

from typing import List


# ------------------ Config ------------------ #
openai.api_key      = os.environ.get('OPENAI_API_KEY')
completion_model    = 'gpt-3.5-turbo'

file_name           = 'data/pages_data'
confluence_spaces   = ['SYS'] # ['DIP', 'SEL', 'SYS', 'IG', 'ITS']

# Config messages
# With gpt-3.5-turbo, we can put 4096 tokens into a message
# A message with activated memory typically looks like this:
# ------------------------------------------------------------------------------
# (1) {"role": "system", "content": system message}  150  tokens_system_message
# (2) {"role": "assistant", "content": context}     1720  max_tokens_per_context
# (3) {"role": "user", "content": query}             100
# (4) {"role": "assistant", "content": response}     300  max_tokens_response
# (5) {"role": "assistant", "content": context}     1720  max_tokens_per_context
# (6) {"role": "user", "content": query}             100
# ------------------------------------------------------------------------------
# ...                                               4090

system_message = """Du bist ein freundlicher IT Support Agent. \
Du erhältst Informationen und Anleitungen aus dem internen Wiki der Firma Simplicity.\
Nutze diese Informatioen, um die Fragen von Mitarbeiter*innen und Anwender*innen so prägnant, präzise und wahrheitsgetreu wie möglich zu beantworten.\
Liefere keine allgemeinen Erklärungen, sondern verwende für deine Antworten nur die Informationen und Anleitungen aus dem Wiki, die du in den assistant messages bereit gestellt bekommst. \
Wenn die Anwort darin nicht enthalten ist, antworte "Ich weiß es nicht." Du kannst die Mitarbeitenden formlos mit "du" ansprechen. Halte die Antworten kurz und kanpp."""

context_message = 'Informationen und Anleitungen aus dem Wiki: \n'

# Change to commented values to activate memory of previous question & answer
max_tokens_per_context = 3490   # 1700
max_messages_to_keep = 3        # 6


# ------------- Shared variables ------------- #
from module.shared import \
  max_num_tokens, \
  tokenizer_encoding_name, \
  embedding_model, \
  max_tokens_response


# ------------- Shared functions ------------- #
from module.shared import \
  get_file_name_for_space, \
  create_embeddings


# ------------- Module functions ------------- #
from module.collect_data import write_csv


# ------------------ Helper ------------------ #
def get_num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def vector_similarity(x: List[float], y:List[float]) -> float:
    return np.dot(np.array(x), np.array(y))

def parse_numbers(s: str) -> List[float]:
  return [float(x) for x in s.strip('[]').split(',')]


# ----------------- Functions ---------------- #
def initialize_memory() -> List[tuple]:
    memory = []
    memory.append({"role": "system", "content": system_message})
    return (memory)

def read_csv(confluence_spaces: List[str], file_name: str) -> pd.DataFrame:
    csv_files = []
    data_frames = []

    for space in confluence_spaces:
        file_name_space = get_file_name_for_space(file_name, space)
        csv_files.append(file_name_space)

    for file in csv_files:
        df = pd.read_csv(file, dtype = {'embeddings': object})
        data_frames.append(df)

    data_frame = pd.concat(data_frames, axis = 0)
    data_frame['embeddings'] = data_frame['embeddings'].apply(lambda x: parse_numbers(x))

    return data_frame

def ask(query: str, memory: List[tuple], pages_df: pd.DataFrame):

    # Sort pages by similarity of the embeddings with the query
    pages_df_sorted = sort_documents(query, pages_df)

    # Get context for query
    context = get_context(query, pages_df_sorted)

    # Construct the prompt
    memory = contruct_prompt(query, memory, context)

    # Debug memory
    # print('\n# Before getting response:')
    # for item in memory:
    #     print(item['role'] + ': ' + item['content'][:25] + ' ... // ' + str(get_num_tokens_from_string(item['content'], tokenizer_encoding_name)))

    # Call api to get answer
    response = openai.ChatCompletion.create(
        model = completion_model,
        messages = memory,
        max_tokens = max_tokens_response,
        temperature = 0,
        stream = True
    )

    return response

def sort_documents(query: str, pages_df: pd.DataFrame) -> pd.DataFrame:

    query_embedding = create_embeddings(query, model = embedding_model)
    pages_df['similarity'] = pages_df['embeddings'].apply(lambda x: vector_similarity(x, query_embedding))
    pages_df.sort_values(by = 'similarity', inplace = True, ascending = False)
    pages_df.reset_index(drop = True, inplace = True)

    return pages_df

def get_context(query: str, pages_df: pd.DataFrame) -> pd.DataFrame:

    chosen_pages_content = []
    sum_tokens_chosen = 0

    # Print info message
    print('\nFür die Antwort genutzte Confluence-Seiten:')
    print('-------------------------------------------')

    for i in range(len(pages_df)):

        page = pages_df.loc[i]

        # Add context until we run out of space.
        if sum_tokens_chosen + page.num_tokens > max_tokens_per_context: # max_num_tokens:
            break

        chosen_pages_content.append(page.page_content)

        sum_tokens_chosen += page.num_tokens + 4  # separator

        # Print info message
        print(page.space.ljust(4) \
          + ': ' + page.title \
          + ' -> ' + page.link \
          + ' [' + str(page.num_tokens) + ' tokens, ' + str(sum_tokens_chosen) + '] total]'\
        )

    context = context_message + '\n\n' . join(chosen_pages_content)

    return context

def contruct_prompt(query: str, memory: List[tuple], context: str) -> List[tuple]:

    memory.append({"role": "assistant", "content": context})
    memory.append({"role": "user", "content": query})

    # Keep [max_messages_to_keep] messages in memory to stay within max_tokens
    # Always keep first system messaage (i.e. delete messages 2, 3 and 4)
    if len(memory) > max_messages_to_keep:
        del memory[1:4]

    return (memory)


# ------------------- Main ------------------- #
def run_chatbot(confluence_spaces: List[str], file_name: str):

    pages_df = read_csv(confluence_spaces, file_name)
    memory = initialize_memory()

    while True:
        # Ask for user's question
        query = input('\n\033[1mFrage:\033[0m ')

        # Type "exit" to exit
        if query == 'exit':
            break

        # Get answer from AI
        response = ask(query, memory, pages_df)

        # Collect chunks of answer to add
        answer = []

        # Print answer to the user
        print('\n\033[1mAntwort:\033[0m ', end = "")
        for chunk in response:
            chunk_content = chunk.choices[0].delta.get("content", "")
            print(chunk_content, end = "", flush = True)
            answer.append(chunk_content)

        # Create whitespace before next question
        print()

        # Add answer to messages for next prompt (chatbot's "memory")
        answer = ''. join(answer)
        memory.append({"role": "assistant", "content": answer})


# ------------------- App -------------------- #
# write_csv(confluence_spaces, file_name)
# run_chatbot(confluence_spaces, file_name)

if __name__ == "__main__":
    action = os.environ.get("ACTION")

    if action == "collect-data":
        write_csv(confluence_spaces, file_name)
    elif action == "start-chatbot":
        run_chatbot(confluence_spaces, file_name)