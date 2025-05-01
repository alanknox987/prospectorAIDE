from utils import call_bedrock_llm

prompt = "What is the capital of France?"
response = call_bedrock_llm(prompt)
print(response)