"""
FreshHire - Fresher & Internship Job Scraper (India Edition)
Scrapes from: Internshala, Unstop, RemoteOK, Remotive
Stores results in: freshjobs.csv
Rules: respects robots.txt, rate-limits all requests, public sources only
"""

import csv
import time
import random
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pandas as pd

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("freshhire")

# ── Config ───────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
}
DELAY_MIN = 2.0
DELAY_MAX = 4.5
CUTOFF_DAYS = 7
OUTPUT_CSV = "freshjobs.csv"

FRESHER_KEYWORDS = [
    "intern", "internship", "fresher", "fresh graduate", "entry level",
    "entry-level", "junior", "trainee", "graduate", "0-1 year",
    "no experience", "campus", "associate", "0 year", "btech", "mba",
    "bca", "mca", "b.tech", "b.e", "b.com", "bsc",
]

EXCLUDE_KEYWORDS = [
    "senior", "sr.", "lead", "manager", "director", "vp ",
    "vice president", "head of", "principal", "staff engineer",
    "5+ years", "7+ years", "10+ years",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def polite_get(url: str, retries: int = 3, extra_headers: dict = None) -> requests.Response | None:
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    h = {**HEADERS, **(extra_headers or {})}
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=h, timeout=20)
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s — %s", attempt, retries, url, exc)
            if attempt < retries:
                time.sleep(attempt * 3)
    return None


def robots_allowed(base_url: str, path: str = "/") -> bool:
    rp = RobotFileParser()
    rp.set_url(urljoin(base_url, "/robots.txt"))
    try:
        rp.read()
        return rp.can_fetch("*", urljoin(base_url, path))
    except Exception:
        return True


def is_fresher_job(title: str, description: str = "") -> bool:
    text = (title + " " + description).lower()
    has_fresher = any(kw in text for kw in FRESHER_KEYWORDS)
    has_senior  = any(kw in text for kw in EXCLUDE_KEYWORDS)
    return has_fresher and not has_senior


def within_cutoff(dt: datetime) -> bool:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)
    return dt >= cutoff


def dedup_key(title: str, company: str) -> str:
    return hashlib.md5(
        f"{title.lower().strip()}|{company.lower().strip()}".encode()
    ).hexdigest()


def detect_work_mode(text: str) -> str:
    t = text.lower()
    if "work from home" in t or "wfh" in t or "remote" in t:
        if "hybrid" in t or "office" in t:
            return "Hybrid"
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    if "onsite" in t or "on-site" in t or "office" in t or "in-office" in t:
        return "Onsite"
    return "Not Specified"


def detect_job_type(title: str, description: str = "") -> str:
    text = (title + " " + description).lower()
    if any(k in text for k in ["intern", "internship"]):
        return "Internship"
    if any(k in text for k in ["full-time", "full time", "fulltime", "permanent"]):
        return "Full-time"
    if "part-time" in text or "part time" in text:
        return "Part-time"
    if "contract" in text or "freelance" in text:
        return "Contract"
    return "Not Specified"


def parse_relative_date(text: str) -> datetime | None:
    """Parse Indian job board relative dates like '2 days ago', 'Today', etc."""
    now = datetime.now(timezone.utc)
    t = text.lower().strip()
    try:
        if "just now" in t or "today" in t or "few hours" in t or "hour" in t:
            return now
        if "yesterday" in t:
            return now - timedelta(days=1)
        if "day" in t:
            n = int(''.join(filter(str.isdigit, t)) or 1)
            return now - timedelta(days=n)
        if "week" in t:
            n = int(''.join(filter(str.isdigit, t)) or 1)
            return now - timedelta(weeks=n)
        if "month" in t:
            n = int(''.join(filter(str.isdigit, t)) or 1)
            return now - timedelta(days=n * 30)
    except Exception:
        pass
    return None


# ── SCRAPER 1: Internshala ────────────────────────────────────────────────────

def scrape_internshala() -> list[dict]:
    """
    Scrape Internshala — India's #1 internship platform.
    Public listing pages, no login required.
    """
    BASE = "https://internshala.com"
    if not robots_allowed(BASE, "/internships"):
        log.info("Internshala robots.txt disallows — skipping")
        return []

    log.info("Scraping Internshala …")
    jobs = []
    seen = set()

    endpoints = [
        "/internships/work-from-home-internships",
        "/internships/computer-science-internships",
        "/internships/web-development-internships",
        "/internships/data-science-internships",
        "/internships/python-internships",
        "/internships/marketing-internships",
        "/internships/content-writing-internships",
        "/internships/graphic-design-internships",
        "/jobs/fresher-jobs",
        "/jobs/software-development-jobs",
    ]

    for endpoint in endpoints:
        url = BASE + endpoint
        r = polite_get(url, extra_headers={"Referer": "https://internshala.com/"})
        if not r:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".individual_internship, [id^='individual_internship']")
        if not cards:
            cards = soup.select(".container-fluid.individual_internship")

        log.info("  %s → %d cards", endpoint, len(cards))

        for card in cards:
            try:
                title_el   = card.select_one(".job-internship-name, .profile, h3 a, .heading_4_5")
                company_el = card.select_one(".company_name, .company-name, p.heading_6")
                link_el    = card.select_one("a.job-title-href, a[href*='/internship/'], a[href*='/job/']")
                loc_el     = card.select_one(".location_link, .locations, .location")
                stipend_el = card.select_one(".stipend, .salary")
                date_el    = card.select_one(".posted-by-text, .status-inactive, span.status-success")

                title   = title_el.get_text(strip=True)   if title_el   else ""
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                link    = (BASE + link_el["href"]) if link_el and link_el.get("href") else url
                loc_txt = loc_el.get_text(strip=True)     if loc_el     else ""
                stipend = stipend_el.get_text(strip=True) if stipend_el else ""
                date_txt= date_el.get_text(strip=True)    if date_el    else ""

                if not title:
                    continue

                posted = parse_relative_date(date_txt) or datetime.now(timezone.utc)
                if not within_cutoff(posted):
                    continue

                desc_el = card.select_one(
                    ".internship_other_details_container, .job_other_details_container"
                )
                desc = desc_el.get_text(" ", strip=True) if desc_el else ""

                # For /jobs pages, enforce fresher filter
                if "job" in endpoint:
                    if not is_fresher_job(title, desc):
                        continue

                key = dedup_key(title, company)
                if key in seen:
                    continue
                seen.add(key)

                jobs.append({
                    "Job Title":        title,
                    "Company Name":     company,
                    "Application Link": link,
                    "Email":            "",
                    "Job Type":         "Internship" if "internship" in endpoint else detect_job_type(title, desc),
                    "Work Mode":        detect_work_mode(loc_txt + " " + desc),
                    "Job Description":  (f"Stipend: {stipend} | " + desc)[:500] if stipend else desc[:500],
                    "Key Responsibilities": "",
                    "Posted Date":      posted.strftime("%Y-%m-%d"),
                    "Source":           "Internshala",
                    "Location":         loc_txt or "India",
                })

            except Exception as exc:
                log.debug("Internshala card error: %s", exc)

    log.info("  Internshala TOTAL → %d jobs", len(jobs))
    return jobs


# ── SCRAPER 2: Unstop ────────────────────────────────────────────────────────

def scrape_unstop() -> list[dict]:
    """
    Scrape Unstop (formerly Dare2Compete) — popular Indian platform
    for fresher jobs, internships & competitions.
    """
    BASE = "https://unstop.com"
    if not robots_allowed(BASE, "/opportunities"):
        log.info("Unstop robots.txt disallows — skipping")
        return []

    log.info("Scraping Unstop …")
    jobs = []
    seen = set()

    # Public API endpoints
    api_urls = [
        "https://unstop.com/api/public/opportunity/search-result?opportunity=jobs&filters=%7B%22oppstatus%22%3A%22open%22%2C%22fresher%22%3Atrue%7D&limit=20&start=0",
        "https://unstop.com/api/public/opportunity/search-result?opportunity=internships&filters=%7B%22oppstatus%22%3A%22open%22%7D&limit=20&start=0",
    ]

    for api_url in api_urls:
        r = polite_get(api_url, extra_headers={
            "Referer": "https://unstop.com/",
            "Accept": "application/json",
        })
        if not r:
            continue
        try:
            data  = r.json()
            items = (data.get("data") or {}).get("data") or data.get("data") or []
            for item in items:
                title   = item.get("title") or item.get("name", "")
                org     = item.get("organisation") or {}
                company = org.get("name", "") or item.get("company", "Unknown")
                pub_url = item.get("public_url", "")
                link    = f"https://unstop.com/o/{pub_url}" if pub_url else BASE
                desc    = item.get("description") or item.get("eligibility") or ""
                if isinstance(desc, dict):
                    desc = str(desc)

                pub_str = item.get("published_at") or item.get("created_at") or ""
                try:
                    posted = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except Exception:
                    posted = datetime.now(timezone.utc)

                if not within_cutoff(posted):
                    continue

                location = item.get("city") or item.get("location") or "India"
                opp_type = item.get("opportunity_type", "").lower()
                job_type = "Internship" if "intern" in opp_type else detect_job_type(title, desc)

                key = dedup_key(title, company)
                if key in seen:
                    continue
                seen.add(key)

                plain_desc = BeautifulSoup(desc, "html.parser").get_text(" ", strip=True)
                jobs.append({
                    "Job Title":        title,
                    "Company Name":     company,
                    "Application Link": link,
                    "Email":            "",
                    "Job Type":         job_type,
                    "Work Mode":        detect_work_mode(plain_desc + " " + str(location)),
                    "Job Description":  plain_desc[:500],
                    "Key Responsibilities": "",
                    "Posted Date":      posted.strftime("%Y-%m-%d"),
                    "Source":           "Unstop",
                    "Location":         str(location),
                })

        except Exception as exc:
            log.error("Unstop API error: %s", exc)

    # HTML fallback if API returns nothing
    if not jobs:
        log.info("  Unstop API empty — trying HTML fallback …")
        r = polite_get("https://unstop.com/jobs", extra_headers={"Referer": "https://unstop.com/"})
        if r:
            soup = BeautifulSoup(r.text, "html.parser")
            for card in soup.select(".opportunity-card, article")[:20]:
                title_el   = card.select_one("h2, h3, .title")
                company_el = card.select_one(".company, .organisation")
                link_el    = card.select_one("a[href]")
                title   = title_el.get_text(strip=True)   if title_el   else ""
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                href    = link_el["href"] if link_el else ""
                link    = (BASE + href) if href.startswith("/") else href or BASE
                if not title:
                    continue
                key = dedup_key(title, company)
                if key in seen:
                    continue
                seen.add(key)
                jobs.append({
                    "Job Title": title, "Company Name": company,
                    "Application Link": link, "Email": "",
                    "Job Type": detect_job_type(title), "Work Mode": "Not Specified",
                    "Job Description": "", "Key Responsibilities": "",
                    "Posted Date": datetime.now().strftime("%Y-%m-%d"),
                    "Source": "Unstop", "Location": "India",
                })

    log.info("  Unstop TOTAL → %d jobs", len(jobs))
    return jobs


# ── SCRAPER 3: RemoteOK (global remote) ──────────────────────────────────────

def scrape_remoteok() -> list[dict]:
    BASE = "https://remoteok.com"
    if not robots_allowed(BASE, "/api"):
        log.info("RemoteOK robots.txt disallows — skipping")
        return []

    log.info("Scraping RemoteOK …")
    r = polite_get("https://remoteok.com/api?tags=junior,internship,entry-level")
    if not r:
        return []

    jobs = []
    try:
        for item in r.json():
            if not isinstance(item, dict) or "id" not in item:
                continue
            title   = item.get("position", "")
            company = item.get("company", "Unknown")
            tags    = item.get("tags") or []
            desc    = BeautifulSoup(item.get("description", ""), "html.parser").get_text(" ", strip=True)
            link    = item.get("url") or f"https://remoteok.com/l/{item.get('slug','')}"
            epoch   = item.get("epoch", 0)
            if not epoch:
                continue
            posted = datetime.fromtimestamp(epoch, tz=timezone.utc)
            if not within_cutoff(posted) or not is_fresher_job(title, desc):
                continue
            jobs.append({
                "Job Title": title, "Company Name": company,
                "Application Link": link, "Email": "",
                "Job Type": detect_job_type(title, desc),
                "Work Mode": "Remote",
                "Job Description": desc[:500], "Key Responsibilities": "",
                "Posted Date": posted.strftime("%Y-%m-%d"),
                "Source": "RemoteOK", "Location": "Remote / Worldwide",
            })
    except Exception as exc:
        log.error("RemoteOK parse error: %s", exc)

    log.info("  RemoteOK → %d jobs", len(jobs))
    return jobs


# ── SCRAPER 4: Remotive ───────────────────────────────────────────────────────

def scrape_remotive() -> list[dict]:
    BASE = "https://remotive.com"
    if not robots_allowed(BASE):
        log.info("Remotive robots.txt disallows — skipping")
        return []

    log.info("Scraping Remotive …")
    jobs = []
    seen = set()

    for cat in ["software-dev", "data", "design", "marketing"]:
        r = polite_get(f"https://remotive.com/api/remote-jobs?category={cat}&limit=50")
        if not r:
            continue
        try:
            for item in r.json().get("jobs", []):
                title   = item.get("title", "")
                company = item.get("company_name", "Unknown")
                desc    = BeautifulSoup(item.get("description", ""), "html.parser").get_text(" ", strip=True)
                link    = item.get("url", "")
                pub_str = item.get("publication_date", "")
                try:
                    posted = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except Exception:
                    continue
                if not within_cutoff(posted) or not is_fresher_job(title, desc):
                    continue
                key = dedup_key(title, company)
                if key in seen:
                    continue
                seen.add(key)
                jobs.append({
                    "Job Title": title, "Company Name": company,
                    "Application Link": link, "Email": "",
                    "Job Type": detect_job_type(title, desc),
                    "Work Mode": detect_work_mode(desc),
                    "Job Description": desc[:500], "Key Responsibilities": "",
                    "Posted Date": posted.strftime("%Y-%m-%d"),
                    "Source": "Remotive", "Location": "Remote / Worldwide",
                })
        except Exception:
            continue

    log.info("  Remotive → %d jobs", len(jobs))
    return jobs


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("FreshHire India Scraper — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("Sources: Internshala 🇮🇳 | Unstop 🇮🇳 | RemoteOK 🌐 | Remotive 🌐")
    log.info("=" * 60)

    all_jobs: list[dict] = []
    all_jobs += scrape_internshala()
    all_jobs += scrape_unstop()
    all_jobs += scrape_remoteok()
    all_jobs += scrape_remotive()

    # Deduplication
    seen, unique = set(), []
    for job in all_jobs:
        k = dedup_key(job["Job Title"], job["Company Name"])
        if k not in seen:
            seen.add(k)
            unique.append(job)

    log.info("Raw: %d  |  After dedup: %d", len(all_jobs), len(unique))

    if not unique:
        log.warning("No jobs found — check network / site availability")
        return

    df = pd.DataFrame(unique, columns=[
        "Job Title", "Company Name", "Application Link", "Email",
        "Job Type", "Work Mode", "Job Description",
        "Key Responsibilities", "Posted Date", "Source", "Location",
    ])
    df.sort_values(["Source", "Posted Date"], ascending=[True, False], inplace=True)
    df.to_csv(OUTPUT_CSV, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8-sig")

    log.info("✓ Saved %d jobs → %s", len(df), OUTPUT_CSV)
    log.info("By source:\n%s",    df["Source"].value_counts().to_string())
    log.info("By job type:\n%s",  df["Job Type"].value_counts().to_string())
    log.info("By work mode:\n%s", df["Work Mode"].value_counts().to_string())
    log.info("=" * 60)
    print(f"\n✅ Done! Open '{OUTPUT_CSV}' to view all scraped jobs.\n")


if __name__ == "__main__":
    main()