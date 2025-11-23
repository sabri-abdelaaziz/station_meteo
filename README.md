# IoT Web Dashboard – Django + AWS + AI

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
1. Clone the repository:  
```bash
git clone https://github.com/yourusername/iot-dashboard.git
cd iot-dashboard


## Installation
1. Clone the repo:  
```bash
git clone https://github.com/sabri-abdelaaziz/station_meteo.git
cd station_meteo

python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

pip install -r requirements.txt


python manage.py migrate

TO RUN THE APP :

python manage.py runserver

then Navigate to http://localhost:8000 to access the dashboard.


