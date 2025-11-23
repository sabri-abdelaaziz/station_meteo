# IoT Sensors +  Web – Django + AWS + AI

## Project Overview
This project is a **web dashboard for visualizing IoT sensor data** (temperature, humidity, air quality, luminosity, etc.) and **displaying AI predictions**.  
Data is collected from IoT sensors, stored in **AWS cloud**, processed by a **Django backend**, and displayed in an interactive dashboard.  
AI models provide predictions and alerts to help users make data-driven decisions in real time.

---

## Features
- Real-time and historical data visualization  
- Interactive charts and tables for each sensor  
- Alerts based on thresholds or AI predictions  
- AI/ML model integration for predicting events (e.g., air quality, risk alerts)  
- Secure storage and access through AWS cloud services  

---

## System Workflow

### Sensors
- IoT sensors measure environmental data (temperature, humidity, air quality, luminosity)  
- Data is sent periodically to the backend or directly to AWS services  

### AWS Cloud
- **S3:** Stores backups and static files  
- **RDS (PostgreSQL):** Stores structured sensor data  
- **EC2 / Elastic Beanstalk:** Hosts the Django web application  
- **CloudFront:** Delivers static content securely and efficiently  

### Django Backend
- Receives sensor data and stores it in the database  
- Provides REST API endpoints for the frontend  
- Processes data for visualization (aggregation, filtering)  

### AI Model Integration
- AI/ML models predict environmental events and trends  
- Predictions are displayed in the dashboard with alerts  
- Helps users anticipate issues before thresholds are reached  

---

## Installation

1. Clone the repo:  
```bash
git clone https://github.com/sabri-abdelaaziz/station_meteo.git
cd station_meteo
2. Create the environement: 
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
3. Install requirements from the file provided: 
pip install -r requirements.txt

4. Optional to migrate DB: 
python manage.py migrate

5. TO RUN THE APP :

python manage.py runserver

then Navigate to http://localhost:8000 to access the dashboard.


# -------------------------------
# Collaborators
# -------------------------------
# Abdelaaziz Sabri        - Web App / Django             - [https://github.com/AbdeIdsd](https://github.com/sabri-abdelaaziz/](https://github.com/sabri-abdelaaziz)
# Mohamed BAIHICH         - Sensors / connectivity       - [https://github.com/AbdeIdsd](https://github.com/sabri-abdelaaziz/](https://github.com/medbaihich)
# Akram RYAD              - Sensors / connectivity       - [https://github.com/AbdeIdsd](https://github.com/sabri-abdelaaziz/](https://github.com/akmanime)
# Brahim OUBALAOUT        - Sensors / connectivity       - [https://github.com/AbdeIdsd](https://github.com/sabri-abdelaaziz/](https://github.com/brahimoubalaout)
# Mohamed amine zinabi    - AI Model Integration         - [https://github.com/AbdeIdsd](https://github.com/sabri-abdelaaziz/](https://github.com/MohamedAmineZinabi)
# Youssef Bouaabane       - Deployment / AWS             - [https://github.com/AliceMartin](https://github.com/youssefhk-sw)



