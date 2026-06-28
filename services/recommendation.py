import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from google.cloud.firestore_v1.base_query import FieldFilter

def extract_text(field):
    """
    Safely flattens any data type into a string for the AI.
    Handles plain strings, lists of tags, and bilingual dictionaries.
    """
    if pd.isna(field) or field is None:
        return ""
    
    # If it's a bilingual dictionary, combine both languages
    if isinstance(field, dict):
        return f"{field.get('en', '')} {field.get('ar', '')}"
    
    # If it's a list (like an array of tags), flatten it
    if isinstance(field, list):
        return " ".join([extract_text(item) for item in field])
        
    # Base case: cast anything else to a string
    return str(field)

def get_recommendations(user_interests, events_data, user_id=None, db_client=None):
    # 1. Safety check
    if not events_data:
        return []

    # Ensure user_interests is a list
    if isinstance(user_interests, str):
        user_interests = [user_interests] if user_interests else []

    # =========================================================
    # DYNAMIC FAVORITES INJECTION
    # =========================================================
    if user_id and db_client:
        try:
            interactions = db_client.collection('User_Interactions')\
                .where(filter=FieldFilter("User_Id", "==", user_id))\
                .where(filter=FieldFilter("Favorite", "==", True))\
                .stream()
            
            # Create a quick dictionary for O(1) lookups
            events_dict = {str(e.get('id', '')): e for e in events_data}
            
            for doc in interactions:
                fav_event_id = str(doc.to_dict().get('id', ''))
                if fav_event_id in events_dict:
                    fav_event = events_dict[fav_event_id]
                    cat = fav_event.get('Category', '')
                    tags = fav_event.get('tags', [])
                    
                    if isinstance(cat, dict):
                        user_interests.extend([cat.get('en', ''), cat.get('ar', '')])
                    else:
                        user_interests.append(str(cat))
                        
                    if isinstance(tags, list):
                        for t in tags:
                            if isinstance(t, dict):
                                user_interests.extend([t.get('en', ''), t.get('ar', '')])
                            else:
                                user_interests.append(str(t))
        except Exception as e:
            print(f"--- ERROR FETCHING USER FAVORITES: {str(e)} ---")

    # 2. Structure data
    df = pd.DataFrame(events_data)
    
    # 3. Combine text for NLP context (Safely handling bilingual dicts!)
    df['tags_safe'] = df.get('tags', pd.Series(dtype=str)).apply(extract_text)
    df['about_safe'] = df.get('About', pd.Series(dtype=str)).apply(extract_text)
    
    df['combined_text'] = df['tags_safe'] + " " + df['about_safe']
    
    # ---------------------------------------------------------
    # FALLBACK 1: The "Skip" Scenario
    # ---------------------------------------------------------
    if not user_interests or str(" ".join(user_interests)).strip() == "":
        top_events = df.sort_values(by='Rating', ascending=False).head(15)
        results_df = top_events.copy()
        results_df = results_df.replace([np.inf, -np.inf], np.nan).fillna(0)
        return results_df.to_dict('records')

    # 4. Prepare User String
    user_string = " ".join(user_interests)
    
    # 5. Vectorization (Words to Numbers)
    count = CountVectorizer()
    count_matrix = count.fit_transform([user_string] + df['combined_text'].tolist())
    
    # 6. Calculate Raw Text Similarity
    cosine_sim = cosine_similarity(count_matrix[0:1], count_matrix[1:])
    
    # ---------------------------------------------------------
    # HYBRID COMPOSITE SCORING
    # ---------------------------------------------------------
    hybrid_scores = []
    
    for idx, text_match_score in enumerate(cosine_sim[0]):
        rating = df.iloc[idx].get('Rating', 4.0)
        try:
            rating = float(rating)
        except (ValueError, TypeError):
            rating = 4.0
            
        norm_rating = rating / 5.0 
        
        crowd_score = df.iloc[idx].get('Live_Crowd_Score', 3.0)
        try:
            crowd_score = float(crowd_score)
        except (ValueError, TypeError):
            crowd_score = 3.0
            
        crowd_penalty = (crowd_score / 5.0) * 0.10
        
        # 70% Text Match + 30% Rating - Crowd Penalty
        final_hybrid_score = (text_match_score * 0.70) + (norm_rating * 0.30) - crowd_penalty
        
        hybrid_scores.append((idx, final_hybrid_score, text_match_score))

    hybrid_scores = sorted(hybrid_scores, key=lambda x: x[1], reverse=True)
    
    # ---------------------------------------------------------
    # FALLBACK 2: The "No Match" Scenario
    # ---------------------------------------------------------
    if hybrid_scores[0][2] == 0.0:
        top_events = df.sort_values(by='Rating', ascending=False).head(15)
        results_df = top_events.copy()
        results_df = results_df.replace([np.inf, -np.inf], np.nan).fillna(0)
        return results_df.to_dict('records')

    # 7. Success! Grab the top 15 indices
    top_indices = [i[0] for i in hybrid_scores[0:15]]
    results_df = df.iloc[top_indices].copy()

    # 8. Final Cleanup
    results_df = results_df.drop(columns=['tags_safe', 'about_safe'], errors='ignore')
    results_df = results_df.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    return results_df.to_dict('records')