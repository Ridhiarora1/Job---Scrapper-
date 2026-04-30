#  Job Web Scraper — Fresher & Internship Focus

A Python-based web scraper that collects **fresher-level and internship job postings from the last 7 days** across multiple public job platforms.

---

##  Project Structure

```
job_scraper/
├── scraper.py          # Main scraper (run this)
├── test_scraper.py     # Unit tests (pytest)
├── requirements.txt    # Python dependencies
├── fresher_jobs.csv    # Output (generated on run)
└── scraper.log         # Log file (generated on run)
```

---

##  Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the scraper
```bash
python scraper.py
```

### 3. Run tests (Day 2)
```bash
pip install pytest
python -m pytest test_scraper.py -v
```

---

##  Output Format

The output `fresher_jobs.csv` contains these columns:

| Column | Description |
|---|---|
| `job_title` | Title of the position |
| `company_name` | Name of the hiring company |
| `application_link` | Direct link to apply |
| `contact_email` | Email address (if found in description) |
| `job_type` | `Internship` or `Full-time` |
| `work_mode` | `Remote`, `Onsite`, `Hybrid`, or `Not Specified` |
| `job_description` | Full description (up to 1000 chars) |
| `key_responsibilities` | Extracted bullet points |
| `date_posted` | Publication date (YYYY-MM-DD) |
| `source` | Which platform the job came from |

---

##  Data Sources

| Source | Method | Why Chosen |
|---|---|---|
| **RemoteOK** | Public JSON API | Structured data, easy to parse |
| **Arbeitnow** | Public RSS feed | Global English jobs, fast |
| **Himalayas** | Public RSS feed | Remote-focused, clean feeds |
| **WeWorkRemotely** | Public RSS feed | Internship + entry-level categories |

---

##  Legal & Ethical Compliance

| Practice | Implementation |
|---|---|
| `robots.txt` respected | `urllib.robotparser` checks every URL before fetch |
| Rate limiting | 2-second delay between all requests |
| No login / paywalls | Only publicly accessible sources used |
| Honest User-Agent | Bot identifies itself clearly |
| No excessive requests | RSS/API-based (not page-by-page crawling) |

---

##  Fresher Detection Logic

A job is included only if it:
1. **Contains** fresher/internship keywords: `fresher`, `entry level`, `intern`, `junior`, `trainee`, `0-1 year`, `recent graduate`, etc.
2. **Does NOT contain** senior keywords: `senior`, `manager`, `lead`, `director`, `5+ years`, etc.

---

##  Data Quality

- **Deduplication**: MD5 hash of `(title + company)` — no duplicates
- **Date filtering**: Jobs older than 7 days are excluded
- **Text cleaning**: Whitespace normalized, HTML stripped
- **UTF-8 with BOM**: CSV opens correctly in Microsoft Excel

---

##  2-Day Plan

### Day 1
- [x] Set up project structure
- [x] Implement all 4 scrapers (RemoteOK, Arbeitnow, Himalayas, WeWorkRemotely)
- [x] Fresher/internship filter logic
- [x] Date filtering (7 days)
- [x] Deduplication pipeline
- [x] CSV output with all required fields

### Day 2
- [ ] Run scraper and inspect CSV output
- [ ] Run `pytest` and verify all tests pass
- [ ] Add more sources if CSV has <20 rows (see below)
- [ ] Review and clean any bad data manually
- [ ] Final submission

---

##  Running the UI Dashboard

```bash
pip install streamlit
streamlit run app.py
```
Opens at `http://localhost:8501` in your browser.

**Features:**
-  Live stats (total jobs, internships, remote, companies)
-  Search by title or company
-  Filter by Job Type, Work Mode, Source
-  Beautiful job cards with Apply buttons
-  Download filtered CSV
-  One-click refresh to re-scrape

---

##  Deployment Steps (for README submission)

### Option 1: Streamlit Cloud (Free, Recommended)
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set main file: `app.py`
5. Click Deploy → Get public URL ✅

### Option 2: Run Locally
```bash
git clone https://github.com/YOUR_USERNAME/fresher-job-scraper
cd fresher-job-scraper
pip install -r requirements.txt
streamlit run app.py
```

---

##  Adding More Sources (Day 2 if needed)

To add more sources, add a new function following this pattern:

```python
def scrape_newsource() -> list[dict]:
    feed = feedparser.parse("https://newsource.com/jobs.rss")
    jobs = []
    for entry in feed.entries:
        title = entry.get("title", "")
        description = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ")
        date_str = entry.get("published", "")
        link = entry.get("link", "")

        if not is_recent(date_str): continue
        if not is_fresher_job(title, description): continue

        jobs.append({
            "job_title": title,
            "company_name": entry.get("author", "Unknown"),
            "application_link": link,
            "contact_email": extract_email(description) or "",
            "job_type": detect_job_type(title, description),
            "work_mode": detect_work_mode(description),
            "job_description": description[:1000],
            "key_responsibilities": extract_responsibilities(description),
            "date_posted": date_str[:10],
            "source": "NewSource",
            "_id": make_id(title, entry.get("author", "")),
        })
    return jobs
```

Then add `scrape_newsource` to the `scrapers` list in `run_pipeline()`.

---

##  Known Limitations

- Job descriptions are capped at 1,000 characters (extend by changing the `[:1000]` slice)
- Work mode detection is heuristic — may misclassify some roles
- Date parsing falls back to "include" if format is unrecognized
