"""Quick test of LLM API connectivity"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f'API key loaded: {"Yes" if api_key and len(api_key) > 10 else "No"}')

try:
    from google import genai
    print('google-genai imported successfully')

    os.environ['GOOGLE_API_KEY'] = api_key
    client = genai.Client()
    print('Gemini client created successfully')

    print('Testing API call...')
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents='Say hello in one word'
    )
    print(f'API response: {response.text}')
    print('SUCCESS: LLM API is working!')

except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
