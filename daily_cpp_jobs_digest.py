import os
from datetime import datetime
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

load_dotenv()

client = OpenAI()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

EMAIL = os.getenv("EMAIL")
TOEMAIL = os.getenv("TOEMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")

PROFILE = """
6.5+ years C++ backend developer | Telecom + Sabre
Distributed systems | Low latency | Bangalore
"""

SALARY_CONTEXT = """
Fintech / low latency → 28–45 LPA
Product company → 25–40 LPA
Service → 18–28 LPA
Telecom → 22–32 LPA
"""

# ---------- LinkedIn connections ----------
def load_connections():
    if not os.path.exists("linkedin_connections.csv"):
        return ""
    return open("linkedin_connections.csv").read()

# ---------- Similar companies ----------
def get_similar_companies():
    res = tavily.search("Companies similar to Sabre in distributed systems telecom", max_results=5)
    text = "\n".join(r["content"] for r in res["results"])

    prompt = f"Extract only company names comma separated:\n{text}"

    return client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    ).output_text.replace("\n", "").strip()

# ---------- Trending sites ----------
def get_sites():
    res = tavily.search("Top tech job sites India 2026", max_results=5)
    text = "\n".join(r["content"] for r in res["results"])

    prompt = f"Extract only job website domains comma separated:\n{text}"

    return client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    ).output_text.replace("\n", "").strip()

# ---------- Chunked job search ----------
def fetch_jobs(companies, sites):

    base_query = "C++ backend developer Bangalore 6.5+ years posted in last 7 days"

    all_results = []

    all_results += tavily.search(base_query, max_results=5)["results"]

    for company in companies.split(",")[:5]:
        try:
            all_results += tavily.search(
                f"{company.strip()} C++ jobs Bangalore",
                max_results=5,
                search_depth="basic"
            )["results"]
        except:
            pass

    for site in sites.split(",")[:5]:
        try:
            all_results += tavily.search(
                f"C++ backend jobs Bangalore site:{site.strip()}",
                max_results=5,
                search_depth="basic"
            )["results"]
        except:
            pass

    return "\n\n".join(
        f"{r['title']}\n{r['url']}\n{r['content']}"
        for r in all_results
    )

# ---------- Walkins ----------
def fetch_walkins():
    res = tavily.search("C++ developer walk-in Bangalore this weekend", max_results=5)
    return "\n".join(r["content"] for r in res["results"])

# ---------- AI summary ----------
def generate_summary(job_data, walkins, companies, connections):

    today = datetime.now().strftime("%d %b %Y")

    prompt = f"""
DATE: {today}

PROFILE:
{PROFILE}

JOB DATA:
{job_data}

STRICT RULES:

1. Ignore jobs older than 5 days
2. If exact apply link not present → remove that job
3. If salary unrealistic for 6.5+ yrs → mark as LOW PACKAGE
4. Walk-in → only upcoming dates and time with location
5. Give Apply Priority Score per job (1–100)

OUTPUT IN PURE HTML:

Each job in this card format:

<div class="job">
<b>Company – Role</b><br>
📅 Posted: ___<br>
💰 Salary: ___<br>
🎯 Priority Score: ___<br>
🤝 Referral: ___<br>
<a href="APPLY_LINK">Apply Now</a>
</div>

Use sections:

<h2>🔥 High Match</h2>
<h2>🚶 Walk-ins</h2>
<h2>📈 Market Insight</h2>

Language: Hinglish
"""
    return client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    ).output_text

# ---------- Apple style mail ----------
def send_email(summary):

    html = f"""
    <html>
    <body style="margin:0;background:#f5f5f7;
    font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial;">

    <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">

    <table width="680" style="background:white;padding:40px;border-radius:22px">

    <tr>
    <td style="font-size:34px;font-weight:700;color:#1d1d1f;">
    C++ Jobs Bangalore
    </td>
    </tr>

    <tr>
    <td style="font-size:18px;color:#6e6e73;padding-bottom:30px;">
    Daily AI Market Digest
    </td>
    </tr>

    <tr><td>

    {summary}

    </td></tr>

    </table>

    </td></tr>
    </table>

    <style>
    .job {{
        border:1px solid #e5e5e7;
        padding:18px;
        border-radius:16px;
        margin-bottom:14px;
        font-size:16px;
        line-height:1.6;
    }}

    a {{
        display:inline-block;
        margin-top:8px;
        background:#0071e3;
        color:white;
        padding:10px 16px;
        border-radius:8px;
        text-decoration:none;
        font-weight:500;
    }}
    </style>

    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = "Jobs_Hunting"
    msg["From"] = EMAIL
    msg["To"] = TOEMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, APP_PASSWORD)
        server.send_message(msg)

# ---------- MAIN ----------
def main():

    print("🔍 Similar companies...")
    companies = get_similar_companies()

    print("🌐 Trending sites...")
    sites = get_sites()

    print("📄 Jobs...")
    jobs = fetch_jobs(companies, sites)

    print("🚶 Walkins...")
    walkins = fetch_walkins()

    connections = load_connections()

    print("🧠 AI summary...")
    summary = generate_summary(jobs, walkins, companies, connections)

    print("📧 Sending mail...")
    send_email(summary)

    print("✅ DONE")

if __name__ == "__main__":
    main()
