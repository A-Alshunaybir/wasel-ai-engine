import json
import math
from datetime import datetime, timedelta

class TourGeneratorService:
    """
    A service class responsible for generating AI-driven cultural itineraries.
    
    This service integrates with a database to fetch available events and utilizes 
    a Large Language Model (via Groq) to construct a localized, time-bound tour. 
    It specifically handles token optimization, bilingual data structures, 
    and strict time-budget enforcement.
    """

    def __init__(self, db_client, groq_client):
        """
        Initializes the TourGeneratorService with database and AI clients.
        """
        self.db = db_client 
        self.groq_client = groq_client

    def _get_bilingual_text(self, field, lang='en') -> str:
        """
        Safely extracts text for the preferred language from a bilingual dictionary.
        Defaults to English if the specific language key is missing.
        """
        if not field:
            return ""
        if isinstance(field, dict):
            # Prioritize requested language, fallback to English, then Arabic
            return field.get(lang, field.get('en', field.get('ar', '')))
        return str(field)

    def _calculate_real_travel_time(self, lat1, lon1, lat2, lon2):
        """
        Calculates the drive time between two GPS coordinates using the Haversine formula.
        Assumes an average Riyadh driving speed of 40 km/h with a 10-minute buffer.
        """
        if not all([lat1, lon1, lat2, lon2]):
            return 20 

        R = 6371.0 
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = R * c

        time_hours = distance_km / 40.0
        time_minutes = int(time_hours * 60)

        return max(15, time_minutes + 10)
    
    async def generate_tour(self, req):
        try:
            # Determine the user's preferred language (defaults to English if not provided)
            lang = getattr(req, 'language', 'en')
            
            # 1. Fetch live events from Firestore
            events_ref = self.db.collection("Events").stream()
            
            # 2. Prepare Slim Data
            slim_events = []
            
            # Get the user's preferences, split them by comma, and make them lowercase for easy matching
            raw_prefs = getattr(req, 'preferences', '')
            user_prefs_list = [p.strip().lower() for p in raw_prefs.split(',')] if raw_prefs else []

            for doc in events_ref:
                event = doc.to_dict()
                
                # Extract the raw English category to check against the filter
                raw_category = event.get("Category", "")
                if isinstance(raw_category, dict):
                    event_cat_en = str(raw_category.get('en', '')).lower()
                else:
                    event_cat_en = str(raw_category).lower()
                
                # THE FILTER
                if user_prefs_list and user_prefs_list[0] != "" and event_cat_en not in user_prefs_list:
                    continue 

                # Extract text based on the user's requested language
                title_safe = self._get_bilingual_text(event.get("Title"), lang)
                cat_safe = self._get_bilingual_text(event.get("Category"), lang)
                desc_safe = self._get_bilingual_text(event.get("About"), lang)
                
                geo_point = event.get("Location")
                if geo_point and hasattr(geo_point, 'latitude'):
                    lat_val = geo_point.latitude
                    lng_val = geo_point.longitude
                else:
                    lat_val = 0.0
                    lng_val = 0.0
                
                raw_price = event.get("Price") or 0
                price_val = 0
                if isinstance(raw_price, dict):
                    price_str = str(raw_price.get('en', '0'))
                    numeric_only = "".join(filter(lambda x: x.isdigit() or x == '.', price_str))
                    price_val = float(numeric_only) if numeric_only else 0.0
                else:
                    price_val = float(raw_price) if str(raw_price).replace('.','',1).isdigit() else 0.0
                
                slim_events.append({
                    "id": doc.id,
                    "title": title_safe,
                    "category": cat_safe,
                    "latitude": lat_val,
                    "longitude": lng_val,
                    "price": price_val, 
                    "image": event.get("Image_Url", ""),
                    "desc": desc_safe[:150] 
                })

            # 3. Construct the AI Prompt
            user_prefs = getattr(req, 'preferences', 'General Cultural')
            prompt = (
                f"You are a Riyadh cultural expert. Plan an EXACT {req.available_hours}-hour itinerary "
                f"starting at {req.start_time}. User location: {req.user_lat}, {req.user_lng}. "
                f"USER PREFERENCES: {user_prefs}. "
                f"CRITICAL RULE: You MUST EXCLUSIVELY select events that match the '{user_prefs}' categories. "
                f"Available Events: {json.dumps(slim_events)} "
                "\n\nSTRICT RULES:"
                f"1. LANGUAGE: You MUST generate all text in {'Arabic' if lang == 'ar' else 'English'}."
                "2. PRICE FORMAT: The 'price' field MUST be a numeric float."
                f"3. TOTAL TIME: The tour MUST be exactly {req.available_hours} hours."
                "4. EVENTS ONLY: You must ONLY return 'event' stops. Do NOT return any 'transit' steps. The system will calculate driving times automatically."
                "5. NO GAPS: Fill the entire duration by extending 'duration_minutes' if necessary."
            )

            # 4. Request JSON from Groq
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a travel coordinator. Return a JSON object with 'tour_title', "
                        "'total_estimated_hours', 'total_price' (numeric), and a list of 'stops' containing 'id', 'title', 'desc', 'category', "
                        "'type' ('event' or 'transit'), 'image', 'arrival_time', 'duration_minutes', 'reasoning', "
                        "'latitude', 'longitude', and 'price' (numeric float)."
                    },
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"}
            )
            
            # 5. Parse the AI's JSON
            tour_json = json.loads(chat_completion.choices[0].message.content)
            
            # =====================================================================
            # POST-PROCESSING: THE BULLETPROOF SUPERVISOR
            # =====================================================================
            raw_stops = tour_json.get("stops", [])
            final_stops = []
            
            lookup_by_id = {str(e.get("id")): e for e in slim_events}
            
            current_lat = float(req.user_lat) if req.user_lat else 24.7136
            current_lng = float(req.user_lng) if req.user_lng else 46.6753
            
            time_format = "%H:%M"
            start_time_obj = datetime.strptime(req.start_time, time_format)
            # Define the hard boundary: Start + Duration[cite: 3]
            max_end_time = start_time_obj + timedelta(hours=float(req.available_hours))
            current_time = start_time_obj

            for stop in raw_stops:
                # SUPERVISOR CHECK: If we have reached the time limit, stop adding events[cite: 3]
                if current_time >= max_end_time:
                    break

                is_event = stop.get("type") == "event" or "event" in str(stop.get("type", "")).lower()
                
                if is_event:
                    # RECOVER LOST DATA
                    ai_id = str(stop.get("id", ""))
                    ai_title = str(stop.get("title", "")).lower().strip()
                    matched_event = lookup_by_id.get(ai_id)
                    
                    if not matched_event: 
                        for e in slim_events:
                            db_title = str(e.get("title", "")).lower().strip()
                            if db_title and (db_title in ai_title or ai_title in db_title):
                                matched_event = e
                                break
                    
                    if matched_event:
                        stop.update({
                            "id": matched_event["id"], "title": matched_event["title"],
                            "desc": matched_event["desc"], "about": matched_event["desc"],
                            "image": matched_event["image"], "latitude": matched_event["latitude"],
                            "longitude": matched_event["longitude"], "price": matched_event["price"],
                            "type": "event"
                        })
                    
                    dest_lat = float(stop.get("latitude", 0))
                    dest_lng = float(stop.get("longitude", 0))

                    # INJECT TRANSIT
                    travel_mins = self._calculate_real_travel_time(current_lat, current_lng, dest_lat, dest_lng)
                    
                    # Ensure transit + a minimum 20m event stay fits the budget
                    if current_time + timedelta(minutes=travel_mins + 20) > max_end_time:
                        break

                    transit_arrival = current_time.strftime(time_format)
                    current_time += timedelta(minutes=travel_mins)
                    
                    msg = "دقائق بالسيارة" if lang == 'ar' else "min drive based on distance"
                    final_stops.append({
                        "type": "transit", "title": "Drive to " + stop.get("title", "Destination"),
                        "arrival_time": transit_arrival, "duration_minutes": travel_mins,
                        "reasoning": f"Approx. {int(travel_mins)} {msg}.", "price": 0
                    })
                    
                    # SET ACCURATE EVENT TIMELINE
                    stop["arrival_time"] = current_time.strftime(time_format)
                    
                    ai_duration = int(stop.get("duration_minutes", 60))
                    # Calculate remaining time in the budget
                    mins_left = (max_end_time - current_time).total_seconds() / 60
                    
                    # Cap the stay to ensure we don't go over time
                    actual_duration = min(ai_duration, int(mins_left))
                    
                    current_time += timedelta(minutes=actual_duration)
                    stop["duration_minutes"] = actual_duration
                    
                    current_lat, current_lng = dest_lat, dest_lng
                    final_stops.append(stop)

                elif stop.get("type") == "transit":
                    travel_mins = int(stop.get("duration_minutes", 15))
                    if current_time + timedelta(minutes=travel_mins) > max_end_time:
                        break
                    stop["arrival_time"] = current_time.strftime(time_format)
                    current_time += timedelta(minutes=travel_mins)
                    final_stops.append(stop)

            # FINAL TOUCH: Return home/Back to start card
            final_stops.append({
                "type": "transit", "title": "Back to Riyadh City Hall",
                "arrival_time": current_time.strftime(time_format),
                "duration_minutes": 0, "price": 0
            })

            tour_json["stops"] = final_stops
            return {"status": "success", "tour": tour_json}
        
        except Exception as e:
            print(f"--- TOUR SERVICE ERROR: {str(e)} ---")
            return {"status": "error", "message": str(e)}