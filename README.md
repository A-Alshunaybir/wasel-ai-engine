# Wasel AI Engine & Backend

> 📱 **Note:** This repository contains the FastAPI backend and AI logic. The cross-platform Flutter mobile application can be found here: [Insert Link to wasel-app].

The Wasel AI Engine is a standalone backend API built to power a smart cultural event discovery platform in Riyadh. It handles machine learning models, natural language processing, and live data manipulation to provide users with a personalized and dynamic experience.

## 🧠 Core Architecture & Technologies
* **Framework:** FastAPI (Python)
* **Database Integration:** Firebase Firestore (handling live event data, user comments, and attendance tracking)
* **Deployment:** Containerized via Docker for scalable cloud deployment (Hugging Face Spaces)

## ✨ AI & Machine Learning Features
* **Smart Event Recommendations:** A content-based recommendation engine built with `scikit-learn` utilizing cosine similarity. It factors in user interests, ratings, crowd scores, tags, and live Firestore data.
* **Bilingual Conversational AI:** Integrates Groq LLMs to provide a retrieval-augmented generation (RAG) chatbot. It features session memory, intent detection, and is grounded directly in the live event database for accurate Riyadh cultural guidance.
* **Live Crowd Prediction:** A custom predictive system that analyzes time, seasonality, price, category, venue capacity, and live attendance tracking to estimate event crowds.
* **Intelligent Itinerary Generation:** AI-generated tour planning that factors in GPS-based travel time estimations, budgeted tour durations, and user preferences to output bilingual itineraries.

## 👥 The Team
The Wasel platform was developed collaboratively by **Alanoud Alshunaybir, Wjoud Albahli, Norah Almoajil, and Yara Alkhalifah**. All team members actively collaborated across the full lifecycle of the project, including the implementation of the mobile application, AI backend, comprehensive testing, and project documentation.
