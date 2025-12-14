import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env
load_dotenv()

def verify_gemini():
    print("=== Verifying Google Gemini API ===")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY is incomplete in .env")
        return

    try:
        genai.configure(api_key=api_key)
        
        print("Listing available models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
        
        model = genai.GenerativeModel("gemini-pro")
        
        print("Sending prompt: 'Explain the offside rule in soccer in one sentence.'")
        response = model.generate_content("Explain the offside rule in soccer in one sentence.")
        
        print(f"[SUCCESS] Response received:")
        print(f"          {response.text}")

    except Exception as e:
        print(f"[ERROR] Generation failed: {e}")

if __name__ == "__main__":
    verify_gemini()
