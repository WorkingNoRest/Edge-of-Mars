import os
import shutil
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import speech_recognition as sr
from gtts import gTTS

app = FastAPI(title="NASA AI NPC Backend (Gemini Edition)")

# 1. إعدادات CORS للسماح لاتصالات Unity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. إعداد Gemini Client
# يقرأ المفتاح تلقائياً من المتغير GEMINI_API_KEY على Render
gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class QuestionRequest(BaseModel):
    player_text: str

# 3. دالة جلب البيانات من NASA Open Data API
def fetch_nasa_data(query: str) -> str:
    if not query or len(query.strip()) == 0:
        return "No specific query provided."
        
    try:
        url = f"https://images-api.nasa.gov/search?q={query}&media_type=image,video"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data.get("collection", {}).get("items", [])
            descriptions = []
            for item in items[:2]:
                data_list = item.get("data", [])
                if data_list and "description" in data_list[0]:
                    descriptions.append(data_list[0]["description"])
            
            if descriptions:
                combined = " ".join(descriptions)
                return combined[:500]
    except Exception as e:
        print(f"NASA API Error: {e}")
        
    return "No direct NASA records found for this query."

# 4. دالة تحويل الصوت إلى نص (STT) باستخدام SpeechRecognition الخفيفة جداً على الـ RAM
def transcribe_audio_file(file_path: str) -> str:
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except Exception as e:
        print(f"Speech Recognition Error: {e}")
        return ""

# 5. دالة توليد إجابة الـ NPC باستخدام Gemini 2.5 Flash
def generate_npc_response_with_gemini(question: str, nasa_context: str) -> str:
    prompt = f"""
    You are an expert Astronaut AI NPC on a space mission.
    Answer the player's question concise and naturally in-character (maximum 3 sentences).
    Use the provided NASA Open Data context to formulate your response if relevant.

    NASA Data Context: {nasa_context}
    Player Question: {question}
    """
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"Astronaut log update regarding {question}: Signal interrupted, but keep exploring space!"

# 6. Endpoint الاختبار
@app.get("/")
def home():
    return {"status": "NASA AI NPC Backend (Gemini) is online and ready!"}

# 7. Endpoint المعالجة الصوتية الكاملة
@app.post("/ask_npc_voice")
async def ask_npc_voice(file: UploadFile = File(...)):
    temp_wav = f"temp_{file.filename}"
    
    try:
        # أ) حفظ ملف الصوت القادم من Unity
        with open(temp_wav, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # ب) تحويل الصوت إلى نص (STT)
        player_text = transcribe_audio_file(temp_wav)
        print(f"🎙️ Transcribed Player Speech: '{player_text}'")
        
        if not player_text:
            player_text = "space exploration"

        # ج) جلب بيانات NASA
        nasa_info = fetch_nasa_data(player_text)
        
        # د) توليد الإجابة الذكية باستخدام Gemini API
        ai_answer = generate_npc_response_with_gemini(player_text, nasa_info)
        print(f"🤖 Gemini NPC Answer: '{ai_answer}'")
        
        # هـ) تحويل الإجابة إلى صوت MP3 عبر gTTS
        output_audio_path = "npc_response.mp3"
        tts = gTTS(text=ai_answer, lang='en')
        tts.save(output_audio_path)
        
        # و) إرجاع ملف الصوت لـ Unity
        return FileResponse(
            output_audio_path, 
            media_type="audio/mpeg", 
            filename="npc_response.mp3"
        )

    except Exception as e:
        print(f"❌ Error in ask_npc_voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # تنظيف الملف المؤقت
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
