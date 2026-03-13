import os
import json
import time
import re
import smtplib
import dns.resolver
import webbrowser
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors

# Load environment variables
load_dotenv()

class JobHunter3000:
    def __init__(self):
        """Initialize all clients and configurations"""
        # API Clients
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        
        # Email config
        self.email = os.getenv("EMAIL")  # anilkruz@gmail.com
        self.app_password = os.getenv("APP_PASSWORD")
        self.phone = "+91-9557846156"
        
        # Profile
        self.profile = {
            "name": "Anil Kumar",
            "email": "anilkruz@gmail.com",
            "phone": "+91-9557846156",
            "experience": "6.5+ years",
            "current_ctc": "24 LPA",
            "target_ctc": "35-50 LPA",
            "location": "Bangalore",
            "skills": [
                "Modern C++ (11/14/17/20)", "Multithreading", "Distributed Systems",
                "Linux", "GDB", "Performance Optimization", "STL", "IPC"
            ],
            "domains": ["Telecom (Amdocs)", "Travel (Sabre/Coforge)"],
            "current_role": "Technical Lead at Coforge (Sabre)"
        }
        
        # Files
        self.base_resume_path = "Anil_Kumar_Resume.pdf"
        self.applied_jobs_file = "applied_jobs.json"
        self.responses_file = "responses.json"
        self.follow_ups_file = "follow_ups.json"
        self.connections_file = "linkedin_connections.json"
        self.interviews_file = "interviews.json"
        self.auto_apply_log_file = "auto_apply_log.json"
        
        # Daily limit
        self.daily_apply_limit = 5
        
        # Load all data
        self.applied_jobs = self._load_json(self.applied_jobs_file, [])
        self.responses = self._load_json(self.responses_file, {})
        self.follow_ups = self._load_json(self.follow_ups_file, [])
        self.connections = self._load_json(self.connections_file, [])
        self.interviews = self._load_json(self.interviews_file, [])
        self.auto_apply_log = self._load_json(self.auto_apply_log_file, [])
        
        # Fake domains to skip
        self.fake_domains = ['unknown.com', 'example.com', 'company.com', 'domain.com', 'test.com']
        
        # Known valid HR email patterns
        self.known_hr_emails = {
            'cisco': 'careers@cisco.com',
            'google': 'careers@google.com',
            'microsoft': 'resume@microsoft.com',
            'amazon': 'jobs@amazon.com',
            'goldmansachs': 'careers@gs.com',
            'jpmorgan': 'jobs@jpmchase.com',
            'uber': 'jobs@uber.com',
            'salesforce': 'careers@salesforce.com',
            'oracle': 'jobs@oracle.com',
            'dell': 'careers@dell.com',
            'emc': 'jobs@emc.com',
            'netapp': 'jobs@netapp.com',
            'nutanix': 'careers@nutanix.com',
            'cohesity': 'jobs@cohesity.com',
            'clickhouse': 'careers@clickhouse.com',
            'striim': 'jobs@striim.com',
            'ringcentral': 'careers@ringcentral.com'
        }
        
        # LinkedIn profile URLs for recruiters
        self.linkedin_recruiters = {
            'cisco': 'https://www.linkedin.com/company/cisco/people/',
            'google': 'https://www.linkedin.com/company/google/people/',
            'microsoft': 'https://www.linkedin.com/company/microsoft/people/',
            'uber': 'https://www.linkedin.com/company/uber-com/people/',
            'dell': 'https://www.linkedin.com/company/delltechnologies/people/'
        }
    
    def _load_json(self, file_path, default):
        """Load JSON file with error handling"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_json(self, file_path, data):
        """Save JSON file"""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_ai_response(self, prompt: str, model: str = "gpt-4") -> str:
        """Get response from OpenAI with error handling"""
        try:
            response = self.openai.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ AI Error: {e}")
            return ""
    
    def validate_email_domain(self, email: str) -> bool:
        """Check if email domain exists and accepts mail"""
        if not email or '@' not in email:
            return False
        
        domain = email.split('@')[1]
        
        if any(fake in domain for fake in self.fake_domains) or 'unknown' in domain.lower():
            return False
        
        if domain == 'cisco.com':
            return True
        
        try:
            dns.resolver.resolve(domain, 'MX')
            return True
        except:
            try:
                dns.resolver.resolve(domain, 'A')
                return True
            except:
                return False
    
    def extract_job_title(self, content: str, url: str) -> Optional[str]:
        """Extract specific job title from posting"""
        if url and "linkedin.com" in url:
            patterns = [
                r'linkedin\.com/jobs/view/([^/]+)',
                r'linkedin\.com/jobs/([^/]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    title = match.group(1).replace('-', ' ').title()
                    return title
        
        prompt = f"""Extract the SPECIFIC job title from this posting.
        Return ONLY the job title, nothing else.
        Text: {content[:500]}"""
        
        title = self._get_ai_response(prompt, "gpt-3.5-turbo")
        if title and len(title) < 100 and ("developer" in title.lower() or "engineer" in title.lower()):
            return title.strip()
        
        return None
    
    def extract_company_name(self, content: str, url: str) -> Optional[str]:
        """Extract company name from job posting"""
        content_lower = content.lower()
        for known_company in self.known_hr_emails.keys():
            if known_company in content_lower:
                return known_company.title()
        
        if url and "linkedin.com" in url:
            patterns = [
                r'linkedin\.com/company/([^/?#]+)',
                r'linkedin\.com/jobs/view/[^/]+-at-([^-]+)-'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    company = match.group(1).replace('-', ' ').title()
                    return company
        
        prompt = f"""Extract ONLY the company name from this job posting.
        Return ONLY the company name, nothing else.
        Text: {content[:500]}"""
        
        company = self._get_ai_response(prompt, "gpt-3.5-turbo")
        if company and company != "Unknown" and len(company) < 50:
            return company.strip()
        
        return None
    
    def get_recent_jobs(self, days: int = 2) -> List[Dict]:
        """Get jobs posted in last 'days' days"""
        print(f"🔍 Searching jobs from last {days} days...")
        
        queries = [
            "site:linkedin.com/jobs C++ backend Bangalore 2026",
            "site:linkedin.com/jobs distributed systems Bangalore",
            "site:linkedin.com/jobs low latency C++ Bangalore",
            "site:linkedin.com/jobs Senior C++ Developer Bangalore"
        ]
        
        all_jobs = []
        
        for query in queries:
            try:
                results = self.tavily.search(
                    query=query,
                    max_results=5,
                    search_depth="advanced"
                )
                
                for r in results.get("results", []):
                    title = self.extract_job_title(r.get("content", ""), r.get("url", ""))
                    company = self.extract_company_name(r.get("content", ""), r.get("url", ""))
                    
                    if not title or not company:
                        continue
                    
                    match_score = self._calculate_match_score(r.get("content", ""))
                    
                    if match_score >= 60:
                        job = {
                            "title": title,
                            "company": company,
                            "url": r.get("url", ""),
                            "content": r.get("content", ""),
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "source": "linkedin",
                            "match_score": match_score
                        }
                        all_jobs.append(job)
                        
            except Exception as e:
                print(f"⚠️ Search error: {e}")
        
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)
        
        unique_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        print(f"✅ Found {len(unique_jobs)} matching jobs")
        return unique_jobs[:self.daily_apply_limit * 2]
    
    def _calculate_match_score(self, content: str) -> int:
        """Calculate how well job matches profile"""
        score = 50
        content_lower = content.lower()
        
        if any(skill.lower() in content_lower for skill in ["c++17", "c++20", "modern c++"]):
            score += 15
        if "distributed system" in content_lower:
            score += 15
        if "multithreading" in content_lower or "concurrency" in content_lower:
            score += 10
        if "linux" in content_lower:
            score += 5
        if "performance optimization" in content_lower or "low latency" in content_lower:
            score += 10
        if any(domain in content_lower for domain in ["fintech", "trading", "hft"]):
            score += 15
        if "telecom" in content_lower or "5g" in content_lower:
            score += 5
        if "travel" in content_lower or "airline" in content_lower:
            score += 10
        
        return min(score, 100)
    
    def find_hr_email(self, company: str) -> Optional[str]:
        """Find HR email for company"""
        if not company:
            return None
        
        company_lower = company.lower()
        for key, email in self.known_hr_emails.items():
            if key in company_lower:
                return email
        
        company_clean = re.sub(r'[^a-zA-Z0-9]', '', company_lower)
        return f"careers@{company_clean}.com"
    
    # ============= FEATURE 1: LINKEDIN CONNECTION REQUESTS =============
    def send_linkedin_connection(self, company: str, job_title: str):
        """Save LinkedIn connection request for manual action"""
        
        profile_url = self.linkedin_recruiters.get(company.lower(), f"https://www.linkedin.com/company/{company.lower()}/people/")
        
        connection = {
            "company": company,
            "job_title": job_title,
            "profile_url": profile_url,
            "message": f"Hi Team {company}, I've applied for the {job_title} position. Would love to connect!",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending"
        }
        
        self.connections.append(connection)
        self._save_json(self.connections_file, self.connections)
        
        print(f"✅ LinkedIn connection request saved for {company}")
        print(f"   🔗 Please connect manually: {profile_url}")
        return True
    
    # ============= FEATURE 2: FOLLOW-UP SYSTEM =============
    def schedule_follow_up(self, job: Dict, days: int = 7):
        """Schedule follow-up email after X days"""
        
        follow_up_date = datetime.now() + timedelta(days=days)
        
        follow_up = {
            "company": job["company"],
            "job_title": job["title"],
            "sent_date": datetime.now().strftime("%Y-%m-%d"),
            "follow_up_date": follow_up_date.strftime("%Y-%m-%d"),
            "hr_email": self.find_hr_email(job["company"]),
            "status": "scheduled",
            "job_url": job.get("url", "")
        }
        
        self.follow_ups.append(follow_up)
        self._save_json(self.follow_ups_file, self.follow_ups)
        
        print(f"📅 Follow-up scheduled for {follow_up_date.strftime('%Y-%m-%d')}")
        return True
    
    def send_follow_up_emails(self):
        """Check and send scheduled follow-ups"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        follow_ups_sent = 0
        
        for fu in self.follow_ups:
            if fu["status"] == "scheduled" and fu["follow_up_date"] <= today:
                prompt = f"""
                Write a polite follow-up email for job application:
                
                Company: {fu['company']}
                Position: {fu['job_title']}
                Original Application Date: {fu['sent_date']}
                
                Keep it short (3-4 sentences), professional, and not desperate.
                Express continued interest and ask for update.
                """
                
                follow_up_email = self._get_ai_response(prompt, "gpt-3.5-turbo")
                
                # Send email
                msg = MIMEMultipart()
                msg["From"] = self.email
                msg["To"] = fu["hr_email"]
                msg["Subject"] = f"Follow-up: {fu['job_title']} application - Anil Kumar"
                
                html_body = f"""
                <html>
                <body style="font-family: Arial; line-height: 1.5;">
                    {follow_up_email.replace(chr(10), '<br><br>')}
                </body>
                </html>
                """
                
                msg.attach(MIMEText(html_body, "html"))
                
                try:
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                        server.login(self.email, self.app_password)
                        server.send_message(msg)
                    
                    fu["status"] = "follow_up_sent"
                    fu["follow_up_sent_date"] = today
                    follow_ups_sent += 1
                    print(f"✅ Follow-up sent to {fu['company']}")
                except Exception as e:
                    print(f"❌ Follow-up failed for {fu['company']}: {e}")
        
        self._save_json(self.follow_ups_file, self.follow_ups)
        return follow_ups_sent
    
    # ============= FEATURE 3: AUTO-APPLY ON COMPANY CAREER PAGES =============
    def auto_apply_company(self, company: str, job_title: str, job_url: str = ""):
        """Open company career page for manual application"""
        
        career_urls = {
            "cisco": "https://jobs.cisco.com",
            "google": "https://careers.google.com",
            "microsoft": "https://careers.microsoft.com",
            "amazon": "https://amazon.jobs",
            "uber": "https://www.uber.com/careers",
            "dell": "https://jobs.dell.com",
            "goldmansachs": "https://www.goldmansachs.com/careers",
            "jpmorgan": "https://careers.jpmorgan.com",
            "salesforce": "https://salesforce.wd1.myworkdayjobs.com/External_Career_Site",
            "oracle": "https://oracle.taleo.net/careers"
        }
        
        company_lower = company.lower()
        url_to_open = job_url if job_url else career_urls.get(company_lower, f"https://www.{company_lower}.com/careers")
        
        print(f"🌐 Opening {url_to_open} for {job_title} at {company}")
        webbrowser.open(url_to_open)
        
        # Log for tracking
        self.auto_apply_log.append({
            "company": company,
            "job_title": job_title,
            "url": url_to_open,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "opened_for_manual_apply"
        })
        self._save_json(self.auto_apply_log_file, self.auto_apply_log)
        
        return True
    
    # ============= FEATURE 4: SMART JOB MATCHING WITH AI =============
    def smart_job_matching(self, job: Dict) -> Dict:
        """Use AI to deeply analyze job match"""
        
        prompt = f"""
        Analyze this job posting and candidate profile for match percentage.
        
        JOB:
        Title: {job['title']}
        Description: {job['content'][:1000]}
        
        CANDIDATE:
        {json.dumps(self.profile, indent=2)}
        
        Return JSON with:
        1. match_score (0-100)
        2. missing_skills (list)
        3. matching_skills (list)
        4. recommendations (string)
        
        Format: {{"match_score": 85, "missing_skills": ["Python"], "matching_skills": ["C++", "Linux"], "recommendations": "Highlight distributed systems experience"}}
        """
        
        result = self._get_ai_response(prompt, "gpt-4")
        
        try:
            # Try to parse JSON from response
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
        
        return {
            "match_score": job.get("match_score", 50),
            "missing_skills": [],
            "matching_skills": self.profile["skills"],
            "recommendations": "Manual review recommended"
        }
    
    # ============= FEATURE 5: INTERVIEW SCHEDULER =============
    def schedule_interview(self, company: str, job_title: str, date: str, time: str, meeting_link: str = ""):
        """Schedule interview and send reminder"""
        
        interview = {
            "company": company,
            "job_title": job_title,
            "date": date,
            "time": time,
            "meeting_link": meeting_link,
            "reminder_sent": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.interviews.append(interview)
        self._save_json(self.interviews_file, self.interviews)
        
        # Send confirmation email to self
        html = f"""
        <html>
        <body style="font-family: Arial;">
            <h2>✅ Interview Scheduled!</h2>
            <p><b>Company:</b> {company}</p>
            <p><b>Position:</b> {job_title}</p>
            <p><b>Date:</b> {date}</p>
            <p><b>Time:</b> {time}</p>
            {f'<p><b>Meeting Link:</b> <a href="{meeting_link}">{meeting_link}</a></p>' if meeting_link else ''}
            
            <h3>Preparation Checklist:</h3>
            <ul>
                <li>Review company background</li>
                <li>Practice C++ and distributed systems questions</li>
                <li>Prepare questions for interviewer</li>
                <li>Test audio/video 15 mins before</li>
            </ul>
            
            <p>All the best! 💪</p>
        </body>
        </html>
        """
        
        msg = MIMEText(html, "html")
        msg["Subject"] = f"🎯 Interview Scheduled: {company} - {job_title}"
        msg["From"] = self.email
        msg["To"] = self.email
        
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)
            print(f"✅ Interview confirmation email sent")
        except:
            pass
        
        print(f"✅ Interview scheduled with {company}")
        return True
    
    # ============= FEATURE 6: ADVANCED HTML DASHBOARD =============
    def generate_advanced_dashboard(self):
        """Generate HTML dashboard with all application stats"""
        
        total_apps = len(self.responses)
        pending_follow_ups = len([f for f in self.follow_ups if f["status"] == "scheduled"])
        total_connections = len(self.connections)
        total_interviews = len(self.interviews)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Job Application Dashboard</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                h1 {{ color: #1a4d8c; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
                .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .stat-number {{ font-size: 36px; font-weight: bold; color: #1a4d8c; }}
                .stat-label {{ color: #666; margin-top: 5px; }}
                table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                th {{ background: #1a4d8c; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 12px; border-bottom: 1px solid #eee; }}
                .follow-up {{ background: #fff3cd; }}
                .interview {{ background: #d4edda; }}
                .section {{ margin-top: 40px; }}
                .section h2 {{ color: #333; border-bottom: 2px solid #1a4d8c; padding-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Job Application Dashboard</h1>
                <p>Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_apps}</div>
                        <div class="stat-label">Total Applications</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{pending_follow_ups}</div>
                        <div class="stat-label">Pending Follow-ups</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_connections}</div>
                        <div class="stat-label">LinkedIn Connections</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_interviews}</div>
                        <div class="stat-label">Interviews Scheduled</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📋 Recent Applications</h2>
                    <table>
                        <tr>
                            <th>Company</th>
                            <th>Position</th>
                            <th>Date</th>
                            <th>Match Score</th>
                            <th>Status</th>
                        </tr>
        """
        
        # Add recent applications
        recent_apps = list(self.responses.items())[-10:]
        for job_key, data in recent_apps:
            follow_up_status = "✅" if any(f["company"] == data["company"] and f["status"] == "follow_up_sent" for f in self.follow_ups) else "⏳"
            html += f"""
                        <tr>
                            <td><b>{data['company']}</b></td>
                            <td>{data['job_title'][:40]}...</td>
                            <td>{data['sent_date']}</td>
                            <td>{data.get('match_score', 0)}%</td>
                            <td>{follow_up_status}</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
                
                <div class="section">
                    <h2>📅 Upcoming Follow-ups</h2>
                    <table>
                        <tr>
                            <th>Company</th>
                            <th>Position</th>
                            <th>Follow-up Date</th>
                            <th>Status</th>
                        </tr>
        """
        
        # Add upcoming follow-ups
        for fu in self.follow_ups[-5:]:
            if fu["status"] == "scheduled":
                html += f"""
                        <tr class="follow-up">
                            <td>{fu['company']}</td>
                            <td>{fu['job_title'][:30]}...</td>
                            <td>{fu['follow_up_date']}</td>
                            <td>Scheduled</td>
                        </tr>
                """
        
        html += """
                    </table>
                </div>
                
                <div class="section">
                    <h2>🎯 Interviews Scheduled</h2>
                    <table>
                        <tr>
                            <th>Company</th>
                            <th>Position</th>
                            <th>Date</th>
                            <th>Time</th>
                        </tr>
        """
        
        # Add interviews
        for interview in self.interviews[-5:]:
            html += f"""
                        <tr class="interview">
                            <td>{interview['company']}</td>
                            <td>{interview['job_title'][:30]}...</td>
                            <td>{interview['date']}</td>
                            <td>{interview['time']}</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
                
                <div style="margin-top: 40px; text-align: center; color: #666;">
                    <p>🎯 Target: 5 applications/day | Current CTC: 24 LPA | Target: 35-50 LPA</p>
                    <p>Keep pushing! 💪</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("dashboard.html", "w") as f:
            f.write(html)
        
        print("✅ Advanced dashboard generated: dashboard.html")
        return html
    
    # ============= FEATURE 7: DAILY REPORT EMAIL =============
    def send_daily_report(self):
        """Send daily report email with application stats"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_apps = [j for j in self.responses.values() if j.get("sent_date") == today]
        pending_follow_ups = [f for f in self.follow_ups if f["status"] == "scheduled" and f["follow_up_date"] <= today]
        
        html = f"""
        <html>
        <body style="font-family: Arial; line-height: 1.6;">
            <h2 style="color: #1a4d8c;">📈 Daily Job Application Report</h2>
            <p><b>Date:</b> {today}</p>
            
            <h3>Today's Summary:</h3>
            <ul>
                <li>✅ Applications Sent: {len(today_apps)}</li>
                <li>📊 Total Applications: {len(self.responses)}</li>
                <li>⏳ Pending Follow-ups: {len(pending_follow_ups)}</li>
                <li>🎯 Interviews Scheduled: {len(self.interviews)}</li>
            </ul>
            
            <h3>Companies Applied Today:</h3>
            <ul>
        """
        
        for app in today_apps:
            html += f"<li><b>{app['company']}</b> - {app['job_title']} (Match: {app.get('match_score', 0)}%)</li>"
        
        html += """
            </ul>
            
            <h3>Follow-ups Due Today:</h3>
            <ul>
        """
        
        for fu in pending_follow_ups:
            html += f"<li><b>{fu['company']}</b> - {fu['job_title']}</li>"
        
        if not pending_follow_ups:
            html += "<li>No follow-ups due today</li>"
        
        html += """
            </ul>
            
            <h3>Next Steps:</h3>
            <ol>
                <li>Send LinkedIn connection requests</li>
                <li>Prepare for upcoming interviews</li>
                <li>Review C++ and system design concepts</li>
            </ol>
            
            <hr>
            <p style="color: #666;">Target: 35-50 LPA | Keep going! 💪</p>
        </body>
        </html>
        """
        
        # Send to self
        msg = MIMEText(html, "html")
        msg["Subject"] = f"📊 Daily Job Report - {today}"
        msg["From"] = self.email
        msg["To"] = self.email
        
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)
            print("✅ Daily report email sent")
            return True
        except Exception as e:
            print(f"❌ Failed to send daily report: {e}")
            return False
    
    # ============= RESUME GENERATION =============
    def generate_resume_summary(self, job: Dict) -> str:
        """Generate customized resume summary"""
        
        company = job['company']
        title = job['title']
        
        if "uber" in title.lower() and "dell" in company.lower():
            company = "Uber"
        elif "dell" in title.lower() and "uber" in company.lower():
            company = "Dell Technologies"
        
        prompt = f"""
        Create a professional resume summary (4-5 lines) for:
        
        Job Title: {title}
        Company: {company}
        
        Candidate:
        - Name: Anil Kumar
        - Current: Technical Lead at Sabre/Coforge (6.5+ years)
        - Skills: Modern C++ (11/14/17/20), distributed systems, multithreading, Linux
        - Domains: Telecom (Amdocs), Travel (Sabre)
        - Key Achievement: 30% performance improvement
        
        Make it ATS-friendly and mention the 30% achievement.
        """
        
        return self._get_ai_response(prompt, "gpt-3.5-turbo")
    
    def generate_professional_resume(self, job: Dict) -> Optional[str]:
        """Generate perfect resume with proper formatting"""
        
        if not job.get("company"):
            return None
        
        company = job['company']
        title = job['title']
        
        if "uber" in title.lower() and "dell" in company.lower():
            company = "Uber"
        elif "dell" in title.lower() and "uber" in company.lower():
            company = "Dell Technologies"
        
        custom_path = f"custom_resumes/Anil_Kumar_{company.replace(' ', '_')}.pdf"
        os.makedirs("custom_resumes", exist_ok=True)
        
        doc = SimpleDocTemplate(custom_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        
        name_style = ParagraphStyle('NameStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, spaceAfter=4, textColor=colors.HexColor('#1a4d8c'))
        title_style = ParagraphStyle('TitleStyle', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#555555'), spaceAfter=8)
        contact_style = ParagraphStyle('ContactStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#777777'), spaceAfter=16)
        section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=14, spaceAfter=8, spaceBefore=12, textColor=colors.HexColor('#1a4d8c'), borderWidth=1, borderColor=colors.HexColor('#cccccc'), borderPadding=(0,0,3,0))
        company_style = ParagraphStyle('CompanyStyle', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=12, spaceAfter=2, textColor=colors.HexColor('#333333'))
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=10, textColor=colors.HexColor('#888888'), spaceAfter=4)
        bullet_style = ParagraphStyle('BulletStyle', parent=styles['Normal'], fontSize=10, leftIndent=20, spaceAfter=4, textColor=colors.HexColor('#444444'))
        normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=10, spaceAfter=6, textColor=colors.HexColor('#444444'))
        
        story = []
        
        story.append(Paragraph("ANIL KUMAR", name_style))
        story.append(Paragraph("Modern C++ Systems Engineer | High-Performance, Multi-Threaded Backend Systems", title_style))
        story.append(Paragraph("📍 Bangalore, India | ✉️ anilkruz@gmail.com | 📱 +91-9557846156", contact_style))
        story.append(Spacer(1, 0.1*inch))
        
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
        
        if "cisco" in company.lower():
            summary = f"""Experienced Technical Lead with 6.5+ years at Sabre/Coforge, specializing in Modern C++ (11/14/17/20), distributed systems, and low-latency applications. Proven expertise in Telecom (Amdocs) and Travel domains with a track record of delivering 30% performance improvement. Seeking to leverage this expertise at {company} to build high-performance systems."""
        elif "uber" in company.lower():
            summary = f"""Technical Lead with 6.5+ years of experience building mission-critical backend systems at Sabre/Coforge. Expert in Modern C++, distributed systems, and performance optimization. Successfully led optimization initiatives that improved system performance by 30%. Excited to contribute to {company}'s innovative engineering team."""
        else:
            summary = f"""Results-driven Technical Lead with 6.5+ years of experience at Sabre/Coforge, specializing in Modern C++ (11/14/17/20), distributed systems, and performance optimization. Proven track record in Telecom and Travel domains with a key achievement of 30% system performance improvement. Ready to leverage expertise at {company}."""
        
        story.append(Paragraph(summary, normal_style))
        story.append(Spacer(1, 0.1*inch))
        
        story.append(Paragraph("TECHNICAL SKILLS", section_style))
        
        skills = [
            ("Programming:", "Modern C++ (11/14/17/20), C, STL"),
            ("Systems:", "Linux, IPC, TCP/IP Basics"),
            ("Concurrency:", "Multithreading, Mutex, Condition Variables"),
            ("Memory Management:", "RAII, Smart Pointers"),
            ("Debugging:", "GDB, Valgrind, perf, AddressSanitizer"),
            ("Testing:", "Google Test, Unit Testing"),
            ("Tools:", "Git, CMake, Azure DevOps")
        ]
        
        for category, items in skills:
            story.append(Paragraph(f"• <b>{category}</b> {items}", bullet_style))
        
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_style))
        
        # Technical Lead
        story.append(Paragraph("Technical Lead - Coforge (Client: Sabre)", company_style))
        story.append(Paragraph("Nov 2025 - Present | Bangalore", date_style))
        story.append(Paragraph("• Leading development of core C++ modules for large-scale airline reservation systems", bullet_style))
        story.append(Paragraph("• Designed and optimized multi-threaded backend components, improved performance by 30%", bullet_style))
        story.append(Paragraph("• Resolved complex race conditions in long-running Linux services using GDB and sanitizers", bullet_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Senior Consultant
        story.append(Paragraph("Senior Consultant - Capgemini", company_style))
        story.append(Paragraph("Mar 2025 - Nov 2025 | Gurugram", date_style))
        story.append(Paragraph("• Worked on high-availability backend modules in C++ focusing on system reliability", bullet_style))
        story.append(Paragraph("• Contributed to modernization of legacy components for improved memory safety", bullet_style))
        story.append(Spacer(1, 0.1*inch))
        
        # SDE-2
        story.append(Paragraph("SDE-2 - CSG", company_style))
        story.append(Paragraph("Jun 2022 - Mar 2025 | Bangalore", date_style))
        story.append(Paragraph("• Developed scalable Modern C++ backend services for transaction processing systems", bullet_style))
        story.append(Paragraph("• Worked on concurrency control in distributed modules", bullet_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Amdocs
        story.append(Paragraph("Software Developer - Amdocs", company_style))
        story.append(Paragraph("Jun 2019 - Jun 2022 | Pune", date_style))
        story.append(Paragraph("• Built Linux-based telecom backend systems using C++11/14", bullet_style))
        story.append(Paragraph("• Implemented IPC mechanisms in high-throughput environments", bullet_style))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("EDUCATION", section_style))
        story.append(Paragraph("<b>Master's Degree in Computer Science</b> - Thapar Institute of Engineering and Technology", normal_style))
        
        doc.build(story)
        return custom_path
    
    def generate_cover_letter(self, job: Dict) -> Optional[str]:
        """Generate human-like cover letter"""
        
        if not job.get("company"):
            return None
        
        company = job['company']
        title = job['title']
        
        if "uber" in title.lower() and "dell" in company.lower():
            company = "Uber"
        elif "dell" in title.lower() and "uber" in company.lower():
            company = "Dell Technologies"
        
        prompt = f"""
        Write a natural, professional job application email for:
        
        Position: {title}
        Company: {company}
        
        Candidate: Anil Kumar
        - Technical Lead at Sabre/Coforge (6.5+ years)
        - Expertise: Modern C++, distributed systems
        - Key achievement: 30% performance improvement
        
        Rules:
        1. 4 short paragraphs
        2. Single line breaks only
        3. NO "Note:" or extra text
        4. Sound human, not robotic
        5. Mention why interested in {company}
        
        Format exactly:
        Dear Hiring Team at {company},
        
        [Intro paragraph]
        
        [Experience paragraph with 30% achievement]
        
        [Why {company} paragraph]
        
        [Closing paragraph]
        
        Thanks,
        Anil Kumar
        """
        
        letter = self._get_ai_response(prompt, "gpt-3.5-turbo")
        
        if letter:
            letter = re.sub(r'\n\s*\n\s*\n', '\n\n', letter)
            letter = re.sub(r'\n\s*Note:.*?\n', '\n', letter)
            letter = '\n'.join(line.rstrip() for line in letter.split('\n'))
        
        return letter
    
    def send_application(self, job: Dict, hr_email: str, cover_letter: str, resume_path: str) -> bool:
        """Send email with clean formatting"""
        
        msg = MIMEMultipart()
        msg["From"] = self.email
        msg["To"] = hr_email
        
        clean_title = job['title'].replace(' jobs', '').replace(' (29 new)', '').strip()
        msg["Subject"] = f"{clean_title} - Anil Kumar - 6.5+ years C++"
        
        clean_letter = cover_letter
        if "Note:" in clean_letter:
            clean_letter = clean_letter.split("Note:")[0].strip()
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial; line-height: 1.5; color: #333; max-width: 600px; margin: 0 auto;">
            {clean_letter.replace(chr(10), '<br><br>')}
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, "html"))
        
        try:
            with open(resume_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename=Anil_Kumar_Resume.pdf")
                msg.attach(part)
        except Exception as e:
            print(f"⚠️ Resume attachment failed: {e}")
            return False
        
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"❌ Email send failed: {e}")
            return False
    
    def track_application(self, job: Dict, hr_email: str):
        """Track sent application"""
        job_key = f"{job['company']}_{job['title']}"
        
        self.responses[job_key] = {
            "company": job["company"],
            "job_title": job["title"],
            "sent_date": datetime.now().strftime("%Y-%m-%d"),
            "hr_email": hr_email,
            "status": "applied",
            "match_score": job.get("match_score", 0),
            "url": job.get("url", "")
        }
        
        self._save_json(self.responses_file, self.responses)
        
        self.applied_jobs.append({
            "company": job["company"],
            "title": job["title"],
            "url": job["url"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "hr_email": hr_email
        })
        self._save_json(self.applied_jobs_file, self.applied_jobs)
    
    def run_daily_hunt(self):
        """Main function to run daily job application"""
        print("="*70)
        print("🚀 JOB HUNTER 3000 - DAILY EXECUTION")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        jobs = self.get_recent_jobs(days=2)
        
        if not jobs:
            print("❌ No matching jobs found today")
            return
        
        jobs_to_apply = [j for j in jobs if j.get("match_score", 0) >= 60][:self.daily_apply_limit]
        
        print(f"\n🎯 Applying to {len(jobs_to_apply)} jobs today:")
        
        successful = 0
        for i, job in enumerate(jobs_to_apply, 1):
            print(f"\n📌 Job {i}/{len(jobs_to_apply)}: {job['title']}")
            print(f"   Company: {job['company']}")
            print(f"   Match Score: {job.get('match_score', 0)}")
            
            if "uber" in job['title'].lower() and "dell" in job['company'].lower():
                job['company'] = "Uber"
                print(f"   🔧 Fixed company: Uber")
            elif "dell" in job['title'].lower() and "uber" in job['company'].lower():
                job['company'] = "Dell Technologies"
                print(f"   🔧 Fixed company: Dell Technologies")
            
            job_id = f"{job['company']}_{job['title']}"
            if job_id in self.responses:
                print("⏭️ Already applied, skipping")
                continue
            
            hr_email = self.find_hr_email(job["company"])
            
            if not hr_email:
                print("❌ No HR email found")
                continue
            
            print(f"📧 HR Email: {hr_email}")
            
            # Smart matching
            match_analysis = self.smart_job_matching(job)
            print(f"   🤖 AI Match Score: {match_analysis.get('match_score', 0)}%")
            if match_analysis.get('recommendations'):
                print(f"   💡 Tip: {match_analysis['recommendations']}")
            
            resume_path = self.generate_professional_resume(job)
            if not resume_path:
                print("❌ Resume generation failed")
                continue
            
            cover_letter = self.generate_cover_letter(job)
            if not cover_letter:
                print("❌ Cover letter generation failed")
                continue
            
            if self.send_application(job, hr_email, cover_letter, resume_path):
                successful += 1
                self.track_application(job, hr_email)
                
                # Schedule follow-up
                self.schedule_follow_up(job, days=7)
                
                # Save LinkedIn connection
                self.send_linkedin_connection(job["company"], job["title"])
                
                # Open career page for manual apply
                if i <= 2:  # Only first 2 jobs
                    self.auto_apply_company(job["company"], job["title"], job.get("url", ""))
                
                print("✅ Application sent successfully!")
            else:
                print("❌ Failed to send")
            
            if i < len(jobs_to_apply):
                print("⏳ Waiting 30 seconds...")
                time.sleep(30)
        
        # Send follow-ups
        follow_ups_sent = self.send_follow_up_emails()
        
        # Generate dashboard
        self.generate_advanced_dashboard()
        
        # Send daily report
        self.send_daily_report()
        
        print("\n" + "="*70)
        print(f"✅ Daily job hunt completed!")
        print(f"   📨 Applications sent: {successful}/{len(jobs_to_apply)}")
        print(f"   📅 Follow-ups sent: {follow_ups_sent}")
        print(f"   🔗 LinkedIn connections saved: {len(jobs_to_apply)}")
        print(f"   📊 Dashboard: dashboard.html")
        print("="*70)
        
        return successful

if __name__ == "__main__":
    hunter = JobHunter3000()
    hunter.run_daily_hunt()
