import google.generativeai as genai
import os

api_key = "AIzaSyDKvd4uniZy5WyteBZQIY1xj0Bt5dbjbTs"
genai.configure(api_key=api_key)

print(f"Checking models for key: {api_key[:10]}...")
try:
    for m in genai.list_models():
        print(f"Name: {m.name}, Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"An error occurred: {e}")
