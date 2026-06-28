from datetime import datetime, timezone, timedelta
import re

def _get_safe_text(field):
    """
    Safely flattens bilingual dictionaries into a lowercase string 
    so the heuristic keyword matchers don't crash.
    """
    if not field:
        return ""
    if isinstance(field, dict):
        # Combines both languages and lowercases them for easy searching
        return f"{field.get('en', '')} {field.get('ar', '')}".lower()
    return str(field).lower()

# --- UPDATED SIGNATURE: Added attending_count=0 ---
def calculate_crowd_prediction(event, attending_count=0):
    """
    Calculates a crowd density score (0-100) based on 12 variables 
    (10 Heuristics + 1 Live User Feedback + 1 App Attendance Override), with Bilingual Support!
    """
    score = 50  # Starting Baseline
    
    # =========================================================
    # BILINGUAL SAFETY EXTRACTION
    # =========================================================
    price_str = _get_safe_text(event.get('Price', '0'))
    category = _get_safe_text(event.get('Category', ''))
    
    # Safely handle the tags list (whether it's a list of strings or dicts)
    raw_tags = event.get('tags', [])
    tags = [_get_safe_text(t) for t in raw_tags] if isinstance(raw_tags, list) else []
    
    rating = event.get('Rating', 4.0)
    live_feedback_score = event.get('Live_Crowd_Score', None) 
    
    # ---------------------------------------------------------
    # SMART CAPACITY ESTIMATOR
    # ---------------------------------------------------------
    raw_capacity = event.get('venue_capacity')
    
    if not raw_capacity or str(raw_capacity).strip() == "":
        if any(c in category for c in ["entertainment", "sports", "conferences", "festivals"]):
            capacity = 2500  
        elif any(c in category for c in ["libraries", "institutes", "arts & culture", "exhibitions"]):
            capacity = 100   
        else:
            capacity = 500   
    else:
        try:
            capacity = int(raw_capacity)
        except ValueError:
            capacity = 500  

    # ---------------------------------------------------------
    # TIMEZONE FIX: Hardcode to Riyadh Time (UTC+3)
    # ---------------------------------------------------------
    riyadh_tz = timezone(timedelta(hours=3))
    now = datetime.now(riyadh_tz)
    
    current_hour = now.hour
    current_day_of_week = now.weekday() # Monday is 0, Sunday is 6
    current_day_of_month = now.day
    current_month = now.month

    # =========================================================
    # THE GATEKEEPER: Is the venue actually open right now?
    # =========================================================
    open_hour = event.get('open_hour')
    close_hour = event.get('close_hour')

    if open_hour is not None and close_hour is not None:
        try:
            op_h = int(open_hour)
            cl_h = int(close_hour)
            
            # Scenario A: Normal hours (e.g., 9 to 22)
            if op_h < cl_h:
                is_open = op_h <= current_hour < cl_h
            
            # Scenario B: Riyadh late-night hours crossing midnight (e.g., 20 to 2)
            else:
                is_open = current_hour >= op_h or current_hour < cl_h
                
            if not is_open:
                return {
                    "score_value": 0,
                    "crowd_status": "CLOSED"
                }
        except (ValueError, TypeError):
            pass 

    # ---------------------------------------------------------
    # 1. Temporal Weight (W_time)
    # ---------------------------------------------------------
    is_weekend = current_day_of_week in [4, 5] or (current_day_of_week == 3 and current_hour >= 17)
    is_evening = 17 <= current_hour <= 23
    is_working_hours = current_day_of_week in [6, 0, 1, 2, 3] and (8 <= current_hour <= 16)

    if is_weekend: score += 25
    elif is_evening: score += 15
    elif is_working_hours: score -= 20

    # ---------------------------------------------------------
    # 2. Financial Accessibility Weight (W_price)
    # ---------------------------------------------------------
    price_numbers = re.findall(r'\d+', price_str)
    price_val = int(price_numbers[0]) if price_numbers else 0

    if price_val == 0 or "free" in price_str: score += 20
    elif 1 <= price_val <= 50: score += 10
    elif price_val >= 150: score -= 10

    # ---------------------------------------------------------
    # 3. Categorical Nature Weight (W_category)
    # ---------------------------------------------------------
    high_energy = ["entertainment", "sports", "conferences", "festivals"]
    quiet_focused = ["libraries", "institutes", "arts & culture", "exhibitions"]

    if any(c in category for c in high_energy): score += 15
    elif any(c in category for c in quiet_focused): score -= 15

    # ---------------------------------------------------------
    # 4. Spatial Capacity Weight (W_capacity)
    # ---------------------------------------------------------
    if capacity < 200: score += 10
    elif capacity > 2000: score -= 10

    # ---------------------------------------------------------
    # 5. Popularity Weight (W_rating)
    # ---------------------------------------------------------
    try:
        rating_val = float(rating)
    except (ValueError, TypeError):
        rating_val = 4.0

    if rating_val >= 4.6: score += 10
    elif rating_val < 3.5: score -= 15

    # ---------------------------------------------------------
    # 6. The Salary Deposit Effect (W_payday)
    # ---------------------------------------------------------
    if current_day_of_month >= 27 or current_day_of_month <= 5:
        score += 15

    # ---------------------------------------------------------
    # 7. Environmental Impact Weight (W_environment)
    # ---------------------------------------------------------
    if any("outdoors" in t for t in tags):
        if current_hour < 17: score -= 20
        elif current_hour >= 18: score += 10

    # ---------------------------------------------------------
    # 8. Urgency & Duration Weight (W_urgency)
    # ---------------------------------------------------------
    start_time = event.get('start_time')
    end_time = event.get('end_time')
    
    if start_time and end_time:
        try:
            duration = (end_time - start_time).days
            if duration <= 3: score += 15
            elif duration > 30: score -= 10
        except:
            pass 

    # ---------------------------------------------------------
    # 9. Demographic Multiplier (W_demographic)
    # ---------------------------------------------------------
    if any(t in ["family", "kids"] for t in tags): score += 10
    elif any(t in tags for t in ["quiet", "solo", "luxury"]): score -= 10

    # ---------------------------------------------------------
    # 10. Macro-Seasonality Weight (W_season)
    # ---------------------------------------------------------
    if current_month in [10, 11, 12, 1, 2, 3]: score += 10
    elif current_month in [5, 6, 7, 8]: score -= 15

    # ---------------------------------------------------------
    # 11. Live User Feedback Override (W_live)
    # ---------------------------------------------------------
    if live_feedback_score is not None:
        try:
            feedback_modifier = (float(live_feedback_score) - 3) * 20
            score += feedback_modifier
        except (ValueError, TypeError):
            pass

    # ---------------------------------------------------------
    # 12. App User Attendance Override (W_attending)
    # ---------------------------------------------------------
    # Reduced significance: +3 points per user attending, max impact of +20
    try:
        count_val = int(attending_count)
        if count_val > 0:
            score += min(count_val * 3, 20)
    except (ValueError, TypeError):
        pass
    
    # ---------------------------------------------------------
    # Final Output Formatting
    # ---------------------------------------------------------
    final_score = max(0, min(100, int(score)))

    if final_score <= 35: status = "LOW"
    elif final_score <= 75: status = "MEDIUM"
    else: status = "HIGH"

    return {
        "score_value": final_score,
        "crowd_status": status
    }