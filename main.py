import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from google import genai
from groq import AsyncGroq 
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import Increment

# Import your custom AI logic
from services.recommendation import get_recommendations 
from services.crowd_predictor import calculate_crowd_prediction
from services.ChatbotService import ChatbotService
from services.tour_service import TourGeneratorService 

from models.schemas import UserComment, TourRequest

load_dotenv()

# 1. INITIALIZE FASTAPI FIRST
app = FastAPI()

# 2. ADD MIDDLEWARE IMMEDIATELY
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. FIREBASE SETUP
firebase_json = os.getenv("FIREBASE_CREDENTIALS")
if firebase_json:
    print("--- INFO: Found FIREBASE_CREDENTIALS in environment ---")
    cred_dict = json.loads(firebase_json)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("serviceAccountKey.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# --- RECOMMENDER ADAPTER ---
class RecommenderAdapter:
    """
    The Adapter Pattern:
    Bridges the ChatbotService (Natural Language) with the Recommendation 
    Engine (ML/NLP scoring). It translates weighted category intents into 
    ranked event lists.
    """
    def score_events(self, events, category_weights):
        # Intent Isolation: 
        # Identify which system categories (e.g., 'Museums') the AI detected.
        interests = [cat for cat, weight in category_weights.items() if weight > 0.0]
        
        # ML Execution: 
        # If the user has a clear preference, run the Content-Based Filtering logic.
        if interests:
            return get_recommendations(interests, events)
        
        # Default State: 
        # If no specific intent is found, provide the raw event pool (Fallback).
        return events
    
# 4. INITIALIZE THE AI PIPELINES
chatbot = ChatbotService(db_client=db, recommendation_model=RecommenderAdapter())
tour_service = TourGeneratorService(db_client=db, groq_client=groq_client) 


# =========================================================================
# CHAT ENDPOINTS
# =========================================================================
@app.get("/chat")
async def chat_with_wasel(user_query: str, session_id: str = "default_user"):
    # 1. Local Database Check
    local_reply = chatbot.get_reply(user_query)
    
    # --- THE FIX: Feed the database hits to the LLM, don't return them directly! ---
    if local_reply != "ROUTE_TO_GEMINI":
        db_context = f"MANDATORY EVENTS TO INCLUDE: {local_reply}. Weave these events naturally into your response based on what the user asked (e.g., if they asked for a day plan, schedule them out)."
    else:
        db_context = chatbot.get_live_database_context()
        
    # 2. Prepare AI Brain (RAG + Memory)
    history = await chatbot.get_and_store_history(session_id, user_query)
    
    system_instruction = (
        "You are Wasel, a friendly and official cultural guide for Riyadh. "
        "Strictly discuss Riyadh's culture, heritage, and events. "
        "Never break character or mention you are an AI. "
        "STRICT BILINGUAL RULE: You MUST detect the language of the user's message and reply ONLY in that same language. "
        "If the user speaks English, you MUST reply in English. "
        "If the user speaks Arabic, you MUST reply strictly in elegant, professional Modern Standard Arabic (اللغة العربية الفصحى). "
        "ARABIC GENERATION RULES: Keep Arabic responses concise, natural, and grammatically correct. Avoid long, rambling sentences. "
        "If you do not have specific information (like an event date or time), simply and politely state that the information is currently unavailable. Do not invent awkward filler text or make up details. "
        "When inserting English event names into Arabic text, maintain clean formatting without adding random symbols or letters. "
        f"Prioritize these live events: {db_context}"
    )

    # 3. Stream from Groq
    async def generate_ai():
        full_response = ""
        try:
            stream = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_instruction}] + history + [{"role": "user", "content": user_query}],
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    yield content
            
            # 4. Save history once complete
            await chatbot.get_and_store_history(session_id, user_query, full_response)
            
        except Exception as e:
            yield "I'm having a bit of trouble connecting. Try asking about Diriyah!"

    return StreamingResponse(generate_ai(), media_type="text/plain")

@app.post("/end-session")
async def end_chat_session(session_id: str, user_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(chatbot.extract_and_save_interests, session_id, user_id, groq_client)
    return {"status": "Session ended. Brain analysis running in background."}

# =========================================================================
# STANDARD API ENDPOINTS
# =========================================================================

@app.get("/")
def home():
    return {"status": "Wasel AI is Online", "database": "Connected", "chatbot": "Local NLP Active"}

# 1. The Comment & Crowd Feedback Endpoint
@app.post("/add-comment")
def add_comment(comment: UserComment):
    riyadh_tz = timezone(timedelta(hours=3))
    now = datetime.now(riyadh_tz)
    
    event_ref = db.collection("Events").document(comment.Event_Id)
    comments_ref = db.collection("Comments")
    
    new_comment = comment.dict()
    new_comment["Date"] = now
    comments_ref.add(new_comment)

    all_comments = comments_ref.where(filter=FieldFilter("Event_Id", "==", comment.Event_Id)).stream()
    
    total_rating = 0
    rating_count = 0
    weighted_crowd_sum = 0
    total_crowd_weight = 0
    two_hours_ago = now - timedelta(hours=2)

    for doc in all_comments:
        data = doc.to_dict()
        total_rating += data.get("Rating", 0)
        rating_count += 1
        
        c_date = data.get("Date")
        if c_date and c_date >= two_hours_ago:
            c_score = data.get("crowd_report", 3)
            age_mins = (now - c_date).total_seconds() / 60
            weight = max(1, 120 - age_mins)
            weighted_crowd_sum += (c_score * weight)
            total_crowd_weight += weight

    update_data = {
        "Rating": round(total_rating / rating_count, 1) if rating_count > 0 else comment.Rating,
    }
    
    if total_crowd_weight > 0:
        update_data["Live_Crowd_Score"] = round(weighted_crowd_sum / total_crowd_weight, 1)

    event_ref.update(update_data)
    return {"status": "success", "updated_fields": update_data}

# 2. Recommendation Endpoint
@app.get("/recommend")
def recommend_events(interest: str):
    docs = db.collection('Events').stream()
    events_data = [doc.to_dict() for doc in docs]
    
    best_matches = get_recommendations([interest], events_data)
    
    for event in best_matches:
        prediction_result = calculate_crowd_prediction(event)
        event["Live_Crowd_Status"] = prediction_result["crowd_status"] 
        event["Live_Crowd_Score_Prediction"] = prediction_result["score_value"]   

    return {"recommendations": best_matches}

# 3. Category Endpoint (The Universal Bilingual Fix)
@app.get("/category/{category_id}")
def get_events_by_category_id(category_id: str):
    try:
        # 1. THE UNIVERSAL TRANSLATOR DICTIONARY
        # Maps IDs, English names, and Arabic names to a single "Master Key"
        category_map = {
            # Libraries
            "LIB": "libraries",
            "LIBRARIES": "libraries",
            "مكتبات": "libraries",
            "المكتبات": "libraries",
            
            # Heritage
            "HER": "heritage",
            "HERITAGE AND TRADITION": "heritage",
            "تراث وتقاليد": "heritage",
            "التراث والتقاليد": "heritage",
            
            # Museums
            "MUS": "museums",
            "MUSEUMS": "museums",
            "متاحف": "museums",
            "المتاحف": "museums",
            
            # Conferences
            "CONF": "conferences",
            "CONFERENCES AND FORUMS": "conferences",
            "مؤتمرات ومنتديات": "conferences",
            "المؤتمرات والمنتديات": "conferences",
            
            # Institutions
            "INST": "institutions",
            "CULTURAL INSTITUTIONS": "institutions",
            "مؤسسات ثقافية": "institutions",
            "المؤسسات الثقافية": "institutions",
            
            # Exhibitions
            "EXH": "exhibition",
            "EXHIBITION AND CONVENTION CENTRE": "exhibition",
            "معارض ومؤتمرات": "exhibition",
            "المعارض والمؤتمرات": "exhibition"
        }
        
        # 2. Normalize the incoming ID and resolve to the Master Key
        search_key = category_id.strip().upper()
        master_category = category_map.get(search_key, category_id.lower().strip())
        
        events_ref = db.collection("Events").stream()
        events_list = []
        
        for doc in events_ref:
            event = doc.to_dict()
            cat = event.get("Category", "")
            
            is_match = False
            
            # 3. SOFT MATCHING LOGIC
            # We check if the master_category (e.g., "museums") exists anywhere in the DB string.
            # This prevents crashes if the DB says "Museums and Heritage" but we search "Museums".
            if isinstance(cat, dict):
                db_en = cat.get('en', '').lower()
                db_ar = cat.get('ar', '').lower()
                
                if master_category in db_en or master_category in db_ar:
                    is_match = True
            elif isinstance(cat, str):
                if master_category in cat.lower():
                    is_match = True
                    
            if is_match:
                prediction_result = calculate_crowd_prediction(event) 
                event["Live_Crowd_Status"] = prediction_result["crowd_status"]
                event["Live_Crowd_Score_Prediction"] = prediction_result["score_value"]
                events_list.append(event)
                
        return {"events": events_list}
    except Exception as e:
        print(f"--- DEBUG ERROR: {str(e)} ---")
        return {"error": str(e)}
# 4. Fetch Single Event by ID
@app.get("/event/{event_id}")
def get_event_by_id(event_id: str):
    try:
        doc_ref = db.collection("Events").document(event_id)
        doc = doc_ref.get()
        
        if doc.exists:
            event_data = doc.to_dict()
            prediction_result = calculate_crowd_prediction(event_data)
            event_data["Live_Crowd_Status"] = prediction_result["crowd_status"]
            event_data["Live_Crowd_Score_Prediction"] = prediction_result["score_value"]
            return {"status": "success", "event": event_data}
        else:
            return {"status": "error", "message": "Event not found in the database."}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
# 5. Trending / Happening Now Endpoint
@app.get("/trending")
def get_trending_events():
    try:
        events_ref = db.collection("Events").stream()
        events_list = [doc.to_dict() for doc in events_ref]
        
        trending_events = []
        
        for event in events_list:
            prediction_result = calculate_crowd_prediction(event)
            event["Live_Crowd_Status"] = prediction_result["crowd_status"]
            event["Live_Crowd_Score_Prediction"] = prediction_result["score_value"]
            
            raw_rating = event.get("Rating", 4.0)
            try:
                rating = float(raw_rating)
            except (ValueError, TypeError):
                rating = 4.0 
                
            crowd = prediction_result["score_value"]
            viral_score = (rating * 0.5) + (crowd * 0.5)
            
            trending_events.append((event, viral_score))
            
        trending_events = sorted(trending_events, key=lambda x: x[1], reverse=True)
        top_3_events = [item[0] for item in trending_events[:3]]
        
        return {"events": top_3_events}
        
    except Exception as e:
        print(f"--- DEBUG ERROR: {str(e)} ---")
        return {"error": str(e)}
    
# 6. Search Endpoint (Bilingual Fix Applied!)
@app.get("/search")
def search_events(q: str):
    """
    Multilingual Search Engine:
    Performs a case-insensitive partial match against Title and Category fields.
    
    Processing Steps:
    1. Fetches a stream of active events from Firestore.
    2. Normalizes bilingual dictionaries into a unified searchable string.
    3. Executes a sub-string comparison ('q' in 'text').
    4. Enriches results with a real-time 'Live Crowd Prediction' before returning.
    """
    try:
        events_ref = db.collection("Events").stream()
        events_list = [doc.to_dict() for doc in events_ref]
        
        search_results = []
        query_lower = q.lower()
        
        for event in events_list:
            title_raw = event.get("Title", "")
            category_raw = event.get("Category", "")
            
            # Data Unwrapping:
            # We combine English and Arabic values so a user can find an event
            # regardless of which language they type in.
            title = f"{title_raw.get('en', '')} {title_raw.get('ar', '')}".lower() \
                    if isinstance(title_raw, dict) else str(title_raw).lower()
            
            category = f"{category_raw.get('en', '')} {category_raw.get('ar', '')}".lower() \
                       if isinstance(category_raw, dict) else str(category_raw).lower()
            
            # Hit Detection
            if query_lower in title or query_lower in category:
                # Dynamic Enrichment: Calculate live density for this specific result
                prediction = calculate_crowd_prediction(event)
                event["Live_Crowd_Status"] = prediction["crowd_status"]
                event["Live_Crowd_Score_Prediction"] = prediction["score_value"]
                
                search_results.append(event)
                
        return {"results": search_results}
        
    except Exception as e:
        # Standardized Error Logging for Hugging Face/Uvicorn console
        print(f"--- DATABASE SEARCH ERROR: {str(e)} ---")
        return {"error": "Internal search failure"}  
# 7. Search Suggestions Endpoint (Bilingual Fix Applied!)
@app.get("/suggestions")
def get_search_suggestions():
    try:
        events_ref = db.collection("Events").stream()
        suggestions = set()
        
        for doc in events_ref:
            event = doc.to_dict()
            category_raw = event.get("Category")
            
            # Extract the English category for the system chip
            if isinstance(category_raw, dict):
                cat_str = category_raw.get("en", "").strip()
            else:
                cat_str = str(category_raw or "").strip()
                
            if cat_str and cat_str != "None":
                suggestions.add(cat_str)
                
        return {"suggestions": list(suggestions)[:6]}
        
    except Exception as e:
        print(f"--- DEBUG ERROR: {str(e)} ---")
        return {"error": str(e)}

# 8. AI Tour Generator Endpoint
@app.post("/generate-tour")
async def generate_tour_endpoint(req: TourRequest):
    return await tour_service.generate_tour(req)

# 9. Attendance Toggle Endpoint (Real-Time Counter Update with Interaction Logging)
@app.post("/attend/{event_id}")
def toggle_attendance(event_id: str, user_id: str, is_attending: bool):
    """
    Triggers when a user clicks 'I'm Attending'.
    Updates the live counter on the event and logs the interaction.
    """
    try:
        # 1. Update the Event document counter atomically
        event_ref = db.collection("Events").document(event_id)
        
        # Add 1 if attending, subtract 1 if canceling
        increment_val = 1 if is_attending else -1
        
        event_ref.set({
            "attending_count": Increment(increment_val)
        }, merge=True)
        
        # 2. Log the specific user interaction
        # Using a composite document ID prevents duplicate attendance clicks
        interaction_ref = db.collection("User_Interactions").document(f"{user_id}_{event_id}_attend")
        interaction_ref.set({
            "User_Id": user_id,
            "id": event_id,
            "Is_Attending": is_attending,
            "Timestamp": firestore.SERVER_TIMESTAMP
        }, merge=True)

        return {"status": "success", "message": f"Counter updated by {increment_val}"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    