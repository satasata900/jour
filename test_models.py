import google.generativeai as genai

api_key = "AIzaSyDKvd4uniZy5WyteBZQIY1xj0Bt5dbjbTs"
genai.configure(api_key=api_key)

models_to_test = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]

for model_name in models_to_test:
    print(f"Testing model: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hi")
        print(f"  Result: {response.text}")
    except Exception as e:
        print(f"  Error: {e}")
