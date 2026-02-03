import google.generativeai as genai
import os
import time

# Use the key provided by the user
api_key = "AIzaSyBIYjKhxHt34OninXZaO8Vdm6Hcu0IvW2s" 

genai.configure(api_key=api_key)

models_to_test = [
    "gemini-flash-lite-latest",
]

print(f"Testing models with NEW API Key: {api_key[:10]}...")

for model_name in models_to_test:
    print("\n" + "="*40)
    print(f"Testing: {model_name}")
    print("="*40)
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hi, are you working? Please reply with YES")
        print(f"✅ Success! Response: {response.text}")
    except Exception as e:
        print(f"❌ Failed. Error: {e}")
    
    time.sleep(1) # Brief pause
