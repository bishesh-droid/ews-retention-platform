# AI-Based Early Warning System (EWS) for Student Retention

## 📌 Overview
This project implements an **AI-driven Early Warning System (EWS)** that monitors student engagement across learning platforms and digital channels, predicts dropout risk using machine learning, and provides real-time decision intelligence to faculty, sales, and marketing teams.

The system is designed for **EdTech companies and digital marketing firms** to proactively identify at-risk learners and optimize retention, revenue, and learning outcomes.

---

## 🚀 Core Capabilities

### 🔍 Behavioral Monitoring
The system collects data from multiple sources:
- Learning Management Systems (logins, assignments, grades)
- Zoom / live classes (attendance, duration)
- Website and app usage (videos watched, clicks)
- WhatsApp / Email engagement
- Marketing campaigns (Meta, Ads, lead source)

---

### 🧠 Dropout Prediction Model
A supervised machine learning model predicts:
- Dropout probability per student
- Engagement score
- Retention likelihood

Each student is assigned a **risk score from 0–100%** that indicates the probability of disengagement or churn.

---

### 📊 Decision Dashboard
A web-based dashboard displays:
- Student-wise risk levels
- Engagement trends
- Batch and cohort performance
- Funnel and campaign analytics

This dashboard is used by:
- Faculty
- Sales teams
- Marketing teams

---

### 🤖 AI Recommendation Engine
Using Large Language Models (LLMs), the system generates:
- Teaching and engagement suggestions for faculty
- Retention strategies for sales teams
- Funnel and campaign optimization ideas for marketing teams

All recommendations are driven by **real-time model predictions**.

---

## 🧩 System Architecture
```
Student Activity → Feature Engineering → ML Model → Risk Scores
↓
Decision Dashboard
↓
AI Recommendation Engine
```

This creates a closed-loop **predict → act → improve** retention system.

---

## 🛠 Technology Stack

| Layer | Technology |
|------|----------|
Backend | FastAPI, Python |
Machine Learning | Scikit-learn / XGBoost |
Database | PostgreSQL |
Frontend | React |
Visualization | Chart.js / Recharts |
AI | LLM APIs (OpenAI / Gemini) |
Deployment | Docker |

---

## 📁 Project Structure

```
ews-retention-platform/
│
├── README.md
├── requirements.txt
├── .env
├── .gitignore
│
├── data/
│   ├── raw/                      # Raw LMS, Zoom, website, marketing data
│   ├── processed/               # Cleaned & feature engineered data
│   └── labels.csv               # Dropout / retention labels
│
├── models/
│   ├── train_model.py           # Train ML model
│   ├── predict.py               # Generate risk scores
│   ├── feature_engineering.py   # Convert logs → ML features
│   ├── evaluation.py            # Accuracy, ROC, AUC etc
│   └── saved_models/            # Trained model files
│
├── backend/
│   ├── main.py                  # FastAPI server
│   ├── database.py              # PostgreSQL connection
│   ├── scheduler.py             # Daily/weekly prediction jobs
│   ├── api/
│   │   ├── students.py          # Student APIs
│   │   ├── predictions.py       # ML prediction endpoints
│   │   └── recommendations.py   # AI-generated insights
│   └── services/
│       ├── ews_engine.py         # Risk scoring logic
│       ├── ai_advisor.py         # LLM recommendation engine
│       └── data_ingestion.py     # LMS, Zoom, Marketing ingestion
│
├── frontend/
│   ├── public/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── Students.jsx
│       │   └── Insights.jsx
│       ├── components/
│       │   ├── RiskTable.jsx
│       │   ├── Charts.jsx
│       │   └── Recommendations.jsx
│       └── api.js
│
├── prompts/
│   ├── faculty_advice.txt
│   ├── sales_advice.txt
│   └── marketing_advice.txt
│
└── docker/
    ├── Dockerfile
    └── docker-compose.yml
```


Each module is designed to be independent, scalable, and production-ready.

---

## 🎯 Use Cases
- Detect early signs of student disengagement  
- Predict dropout before it happens  
- Improve teaching and mentoring strategies  
- Optimize marketing campaigns  
- Increase student lifetime value  

---

## 🎓 Academic & Industry Value
This system replicates the same retention and churn prediction pipelines used by:
- EdTech companies
- Subscription platforms
- Digital marketing firms
- Online training academies

It demonstrates:
- Data engineering
- Machine learning
- AI integration
- Business intelligence and decision automation

---

## 🔮 Future Enhancements
- Personalized intervention strategies  
- Automated WhatsApp outreach  
- Predictive revenue modeling  
- Multi-language support  
- Deeper learning behavior analytics  

---

## 🤝 Contributions
Contributions, ideas, and improvements are welcome.  
Feel free to open an issue or submit a pull request.

