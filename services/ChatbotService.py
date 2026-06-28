import re
from datetime import datetime, timezone
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

class ChatbotService:
    def __init__(self, db_client, recommendation_model):
        self.db = db_client
        self.recommender = recommendation_model
        
        # 1. EXACT MAP TO WASEL FLUTTER FRONTEND & FIRESTORE (Massively Expanded Bilingual Synonyms)
        self.category_mapping = {
            "Libraries": [
                "library", "libraries", "book", "books", "reading", "study", "literature", "author", "novel", "poetry", "reading room", 
                "مكتبة", "مكتبات", "كتاب", "كتب", "قراءة", "رواية", "أدب", "شعر", "دراسة", "مؤلف", "قصة", "قصص"
            ],
            "Heritage and Tradition": [
                "heritage", "tradition", "history", "historical", "traditional", "folk", "folklore", "culture", "souq", "local", "market", "crafts", "past", "ancient", 
                "تراث", "تاريخ", "تاريخي", "شعبي", "ثقافة", "سوق", "حرف", "تقليدي", "ماضي", "أثري", "قديم", "تراثي", "عادات", "تقاليد"
            ],
            "Museums": [
                "museum", "museums", "artifact", "antiquity", "exhibit", "archaeology", "national", "gallery", "collection", "sculpture", "art", "paintings", 
                "متحف", "متاحف", "آثار", "معرض", "فني", "فنون", "أثرية", "تحف", "لوحات", "نحت", "رسم"
            ],
            "Conferences and Forums": [
                "conference", "forum", "symposium", "talk", "panel", "seminar", "summit", "keynote", "meetup", "speaker", "lecture", "debate", "workshop", 
                "مؤتمر", "مؤتمرات", "منتدى", "ندوة", "لقاء", "ورشة", "قمة", "محاضرة", "نقاش", "متحدث", "حوار", "جلسة"
            ],
            "Cultural Institutions": [
                "institution", "academy", "society", "foundation", "cultural center", "council", "ministry", "association", "institute", 
                "مؤسسة", "أكاديمية", "جمعية", "معهد", "مركز ثقافي", "وزارة", "هيئة", "مجلس", "منظمة"
            ],
            "Exhibition and Convention Centre": [
                "exhibition", "convention", "expo", "fair", "trade show", "event center", "hall", "showcase", "display", "con", "festival", 
                "معرض", "مؤتمرات", "اكسبو", "مركز معارض", "صالة", "قاعة", "فعاليات", "مهرجان", "عروض"
            ]
        }
        self.system_categories = list(self.category_mapping.keys())
        
        # 2. LOCATION ALIASES (Expanded Riyadh Zones, Slang, and Arabic Equivalents)
        self.zone_mapping = {
            "diriyah": ["diriyah", "turaif", "bujairi", "الدرعية", "طريف", "البجيري", "مطل البجيري"],
            "jax": ["jax", "jax district", "جاكس", "حي جاكس"],
            "masmak": ["masmak", "deera", "batha", "murabba", "qasr", "المصمك", "الديرة", "البطحاء", "قصر", "المربع"],
            "king fahad": ["king fahad", "kfnl", "national library", "الملك فهد", "مكتبة الملك فهد"],
            "historical centre": ["historical centre", "abdul aziz", "national museum", "kacc", "المركز التاريخي", "مركز الملك عبدالعزيز"],
            "riyadh front": ["front", "riyadh front", "roshn", "واجهة الرياض", "الواجهة", "روشن", "واجهة روشن"],
            "boulevard": ["boulevard", "blvd", "city", "world", "البوليفارد", "بوليفارد", "سيتي", "وورلد"],
            "diplomatic quarter": ["dq", "diplomatic quarter", "safarat", "حي السفارات", "السفارات"],
            "olaya": ["olaya", "tahlia", "tahliya", "العليا", "التحلية"],
            "kapsarc": ["kapsarc", "مركز الملك عبدالله", "كابسارك"]
        }

    # =========================================================================
    # BILINGUAL HELPER
    # =========================================================================
    def _get_bilingual_text(self, field) -> str:
        """
        Safely extracts text from either a standard string or a bilingual dictionary.
        Formats dictionaries neatly as 'English / Arabic' for the UI and AI context.
        """
        if not field:
            return "Unknown"
        if isinstance(field, dict):
            en_text = field.get('en', '').strip()
            ar_text = field.get('ar', '').strip()
            if en_text and ar_text:
                return f"{en_text} / {ar_text}"
            return en_text or ar_text
        return str(field)

    def _extract_features(self, message: str) -> dict:
        """
        Parses natural language into a structured feature vector, casting a 
        wide net for synonyms but strictly outputting system categories.
        """
        message = message.lower()
        
        user_vector = {
            "category_weights": {cat: 0.0 for cat in self.system_categories},
            "location": None,
            "is_weekend": False
        }

        # Extract Category Intent
        for system_cat, keywords in self.category_mapping.items():
            if any(word in message for word in keywords):
                user_vector["category_weights"][system_cat] = 1.0

        # Extract Location (Alias check against standard tokens)
        for official_token, aliases in self.zone_mapping.items():
            if any(alias in message for alias in aliases):
                user_vector["location"] = official_token
                break

        # Extract Temporal Intent (Massively expanded days, times, and Arabic terms)
        time_keywords = [
            "weekend", "saturday", "friday", "tomorrow", "tonight", "today", "morning", "afternoon", "evening", 
            "sunday", "monday", "tuesday", "wednesday", "thursday", 
            "ويكند", "عطلة", "نهاية الأسبوع", "الجمعة", "السبت", "بكرة", "غدا", "اليوم", "الليلة", 
            "الصباح", "المساء", "العصر", "الظهر", "الاحد", "الاثنين", "الثلاثاء", "الاربعاء", "الخميس"
        ]
        if any(word in message for word in time_keywords):
            user_vector["is_weekend"] = True

        return user_vector
    
    def _fetch_and_rank_events(self, user_vector: dict) -> list:
        """
        Executes a highly optimized token search in Firestore, then passes 
        the results to the Content-Based Filtering algorithm for scoring.
        """
        events_ref = self.db.collection("Events")
        target_location = user_vector.get("location")
        
        if target_location:
            # OPTIMIZED O(1) QUERY: Hits the search_tokens array 
            query = events_ref.where(filter=FieldFilter("search_tokens", "array-contains", target_location)).stream()
            filtered_events = [doc.to_dict() for doc in query]
        else:
            # Fallback: Just grab a pool of active events if no specific location was requested
            query = events_ref.limit(50).stream() 
            filtered_events = [doc.to_dict() for doc in query]

        # Failsafe
        if not filtered_events:
            return []
            
        # Pass the clean, pre-filtered list to your ML recommendation model
        ranked_events = self.recommender.score_events(filtered_events, user_vector["category_weights"])
        
        return ranked_events[:3] 
    
    def get_reply(self, message: str) -> str:
        try:
            user_vector = self._extract_features(message)
            
            has_category = any(weight > 0 for weight in user_vector["category_weights"].values())
            has_location = user_vector["location"] is not None
            has_time = user_vector["is_weekend"]
            
            # 1. No intent at all (e.g., "hello" or "tell me a joke") -> Send to Gemini
            if not (has_category or has_location or has_time):
                return "ROUTE_TO_GEMINI" 

            # 2. Intent detected! Fetch events.
            best_matches = self._fetch_and_rank_events(user_vector)
            
            # 3. We knew they wanted an event, but the database is empty for that request.
            # Do NOT send to Gemini. Tell the user directly.
            if not best_matches:
                return "I couldn't find any events matching that right now! Try checking a different area or category."
                
            # 4. Success! Format the results using the Bilingual Helper!
            reply_text = "Here are my top recommendations based on what you are looking for:\n\n"
            for event in best_matches:
                title = self._get_bilingual_text(event.get('Title'))
                loc = self._get_bilingual_text(event.get('Location_Address'))
                score = event.get('match_score', 0.90) * 100 
                
                reply_text += f"• **{title}** at {loc} ({score:.0f}% match)\n"
                
            return reply_text
            
        except Exception as e:
            print(f"Chatbot Pipeline Error: {e}")
            return "I'm having a bit of trouble calculating the best events right now. Please try again!"
        
    def get_live_database_context(self) -> str:
        """Fetches a lightweight text summary of active events for the AI."""
        try:
            events_ref = self.db.collection("Events").limit(50).stream()
            context_string = "CURRENT WASEL DATABASE EVENTS:\n"
            for doc in events_ref:
                data = doc.to_dict()
                
                # Protect Llama's brain from raw JSON dictionaries!
                title = self._get_bilingual_text(data.get('Title'))
                category = self._get_bilingual_text(data.get('Category'))
                loc = self._get_bilingual_text(data.get('Location_Address'))
                
                context_string += f"- {title} (Type: {category}, Location: {loc})\n"
            return context_string
        except Exception as e:
            print(f"Context Fetch Error: {e}")
            return ""

    async def get_and_store_history(self, session_id: str, user_query: str, ai_response: str = None):
        """Manages persistent chat history in Firestore."""
        session_ref = self.db.collection("Conversations").document(session_id)
        history_ref = session_ref.collection("Messages")
        
        if ai_response is None:
            # Step A: Retrieve history for the prompt
            docs = history_ref.order_by("timestamp", direction="DESCENDING").limit(6).stream()
            history = [{"role": d.to_dict()["role"], "content": d.to_dict()["content"]} for d in reversed(list(docs))]
            return history
        else:
            # Step B: Save the exchange after AI finishes talking
            batch = self.db.batch()
            
            batch.set(session_ref, {
                "last_active": datetime.now(timezone.utc),
                "type": "temporary_session"
            }, merge=True)
            
            user_msg_ref = history_ref.document()
            batch.set(user_msg_ref, {"role": "user", "content": user_query, "timestamp": datetime.now(timezone.utc)})
            
            ai_msg_ref = history_ref.document()
            batch.set(ai_msg_ref, {"role": "assistant", "content": ai_response, "timestamp": datetime.now(timezone.utc)})
            
            batch.commit()

    async def extract_and_save_interests(self, session_id: str, user_id: str, ai_client):
        """Analyzes a finished chat and saves the user's interests to their Long-Term profile."""
        if not user_id or not session_id:
            return

        try:
            # 1. Fetch the entire chat history for this session
            history_ref = self.db.collection("Conversations").document(session_id).collection("Messages")
            docs = history_ref.order_by("timestamp", direction="ASCENDING").stream()
            transcript = "\n".join([f"{d.to_dict()['role']}: {d.to_dict()['content']}" for d in docs])

            # If the chat was too short (e.g., just "Hi"), don't bother extracting
            if len(transcript.split()) < 10:
                return

            # 2. Ask the AI to act as an Analyst
            extraction_prompt = (
                "You are an AI analyst. Read the following chat transcript between a user and a Riyadh cultural guide. "
                "Extract 1 to 3 broad cultural interests the user showed (e.g., 'Fine Dining', 'Historical Sites', 'Art Galleries'). "
                "Return ONLY a comma-separated list of these interests. Do not write anything else.\n\n"
                f"TRANSCRIPT:\n{transcript}"
            )

            response = await ai_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1 # Low temperature so it doesn't get creative
            )

            # 3. Clean up the AI's response into a Python list
            raw_output = response.choices[0].message.content
            new_interests = [interest.strip().title() for interest in raw_output.split(",") if interest.strip()]

            # 4. Save it using the method we wrote earlier!
            if new_interests:
                self.save_user_interests(user_id, new_interests)
                print(f"--- SUCCESS: Extracted {new_interests} for {user_id} ---")

        except Exception as e:
            print(f"Extraction Error: {e}")

    # =========================================================================
    # LONG-TERM MEMORY METHODS
    # =========================================================================
    def get_user_profile_context(self, user_id: str) -> str:
        """Fetches long-term interests for a logged-in user to inject into the AI's brain."""
        if not user_id:
            return ""
            
        try:
            user_ref = self.db.collection("Users").document(user_id).get()
            if user_ref.exists:
                data = user_ref.to_dict()
                interests = data.get("ai_inferred_interests", [])
                if interests:
                    return f"USER'S HISTORICAL INTERESTS: {', '.join(interests)}. Tailor your recommendations to these if relevant, even though this is a new chat session."
        except Exception as e:
            print(f"Profile Fetch Error: {e}")
            
        return ""

    def save_user_interests(self, user_id: str, new_interests: list):
        """Appends new interests to the user's profile without overwriting old ones."""
        if not user_id or not new_interests:
            return
            
        try:
            user_ref = self.db.collection("Users").document(user_id)
            # ArrayUnion ensures we don't add duplicate interests
            user_ref.set({
                "ai_inferred_interests": firestore.ArrayUnion(new_interests)
            }, merge=True)
        except Exception as e:
            print(f"Error updating user interests: {e}")