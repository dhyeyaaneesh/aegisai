# AegisAI — AI-Powered Scam Detection System

AegisAI is a full-stack AI-powered scam detection platform that analyzes URLs, text, emails, and voice inputs to identify potential threats. It combines machine learning, external APIs, and a user-friendly interface to provide real-time security insights.

---

## Features

* **URL Scam Detection** using Google Safe Browsing API
* **AI-based Text Analysis** using Hugging Face Transformers
* **Voice Scam Detection** via AssemblyAI
* **User Authentication System** with session handling
* **Gamification System** (XP, scans, threats blocked)
* **SQLite Database** for storing user stats

---

## Architecture

* **Frontend:** Streamlit (interactive UI)
* **Backend:** Flask API
* **Database:** SQLite
* **AI/ML:** Transformers pipeline
* **APIs Used:**

  * Google Safe Browsing API
  * AssemblyAI API

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/aegisai.git
cd aegisai
```

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file:

```env
GOOGLE_SAFE_BROWSING_KEY=your_key_here
ASSEMBLYAI_API_KEY=your_key_here
```

Run backend:

```bash
python app.py
```

---

### Frontend Setup

```bash
cd frontend
pip install streamlit
streamlit run streamlit_app.py
```

---

## Usage

1. Start backend server
2. Launch Streamlit frontend
3. Input:

   * URLs
   * Text messages
   * Audio files
4. Get scam detection results instantly

---

## Key Highlights

* Combines **multiple detection methods** (URL + text + voice)
* Real-time analysis with external APIs
* Clean UI with user tracking and gamification

---

## License

MIT License

---

## Authors

* Dhyeya Aneesh
* Riya Saju Vithayathil
* Anvi Jain
