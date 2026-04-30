# ⚡ FreshHire - Job Scrapper

Real-time fresher & internship job scraper for India.

##  Features
- Scrapes jobs from Internshala, Unstop, RemoteOK, Remotive
- Last 7 days jobs only
- No duplicate records
- Exports clean CSV data
- Respects robots.txt & rate limiting

##  Tech Stack
- Python, BeautifulSoup, Pandas, Flask

##  How to Run
pip install -r requirements.txt
python scraper.py
python app.py

##  Clone Repository
git clone https://github.com/Ridhiarora1/Job---Scrapper-
cd Job---Scrapper-

##  Deploy on Render (Free)
1. Go to https://render.com
2. Sign up with GitHub
3. Click New → Web Service
4. Connect: Job---Scrapper- repository
5. Build Command: pip install -r requirements.txt
6. Start Command: python app.py
7. Click Deploy!

##  Requirements
- Python 3.10+
- Flask
- Pandas
- BeautifulSoup4
- Requests

##  Output
Visit: http://localhost:8501

##  Files
- scraper.py - Web scraper
- app.py - Flask web app
- freshjobs.csv - Scraped data
