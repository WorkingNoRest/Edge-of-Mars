from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(title="NASA AI NPC Backend")

# السماح لـ Unity بالاتصال بالسيرفر دون مشاكل CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    player_text: str

def fetch_nasa_data(query: str) -> str:
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
            return "\n".join(descriptions) if descriptions else "No specific NASA data found."
    except Exception as e:
        print(f"NASA API Error: {e}")
    return "NASA database lookup failed."

@app.get("/")
def home():
    return {"status": "Server is running online!"}

@app.post("/ask_npc")
async def ask_npc(req: QuestionRequest):
    nasa_info = fetch_nasa_data(req.player_text)
    
    # هنا يمكنك ربط الموديل الخاص بيك (مثل Gemini / OpenAI)
    ai_answer = f"According to NASA records about '{req.player_text}': {nasa_info[:200]}..."
    
    return {
        "status": "success",
        "question": req.player_text,
        "answer": ai_answer
    }
