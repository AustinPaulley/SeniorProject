import openai
import api_key

openai.api_key = api_key.api_key

#Model or engine is in reference to the four main models OpenAI has, davinci-003 being the most powerful
#Prompt is used to generate completions for the tokens
#Max_tokens is the maximum number of tokens to generate in the completion
#One token is 4 characters of text; most models have a maximum of 2048 tokens some have 4096
#Temperature refers to what sampling temperature to use. Higher values means the model will take more risks.
#OpenAI recommends .9 for more creative and 0 for well-defined answers
#An alternative to sampling with temperature, called nucleus sampling, where the model considers the results
#of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered
#OpenAI recommends altering top_p or temperature but not both.
#n is how many completions to generate for each prompt; BE CAREFUL TO NOT DO TOO MANY
#echo will echo back the prompt and the completion
#presence_penalty is a number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so
#far, increasing the model's likelihood to talk about new topics.
#frequency_penalty is a number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the
#text so far, decreasing the model's likelihood to repeat the same line verbatim.


#Simple text completion/generation example; added temperature to get the more creative completions
prompt = """Write a tagline for an ice cream shop"""

response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, temperature=.9, max_tokens=30)

print(response)



#Classification example
#prompt = """Decide whether a Tweet's sentiment is positive, neutral, or negative.

#Tweet: I love the new Batman movie!
#Sentiment:"""

#response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=30)

#print(response)


#Translation example which didn't seem to be working properly
#response = openai.Completion.create(
#  model="text-davinci-003",
#  prompt="Translate this into 1. French, 2. Spanish and 3. Japanese:\n\nHow are you?\n\n1.",
#  max_tokens=100,
#)

#print(response)



#Completion example, could need a lot of tokens as it can write a substantial amount of text
#response = openai.Completion.create(
#  model="text-davinci-001",
#  prompt="Computer science focuses on the development and",
#  temperature=0.29,
#  max_tokens=64,
#  top_p=1,
#  frequency_penalty=0,
#  presence_penalty=0
#)

#print(response)



