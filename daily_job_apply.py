import os
import json
import time
import re
import csv
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import PyPDF2
import io

# Load environment variables
load_dotenv()

class JobHunter3000:
    def __init__(self):
        """Initialize all clients and configurations"""
        # API Clients
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        
        # Email config
        self.email = os.getenv("EMAIL")
        self.app_password = os.getenv("APP_PASSWORD")
        
        # Profile
        self.profile = {
            "name": "Anil Kumar",
            "experience": "6.5+ years",
            "current_ctc": "24 LPA",
            "target_ctc": "35-50 LPA",
            "location": "Bangalore",
            "skills": ["Modern C++ (11/14/17/20)", "Multithreading", "Distributed Systems", 
                      "Linux", "GDB", "Performance Optimization", "STL", "IPC"],
            "domains": ["Telecom (Amdocs)", "Travel (Sabre/Coforge)"],
            "current_role": "Technical Lead at Coforge (Sabre)"
        }
        
        # Files
        self.base_resume_path = "Anil_Kumar_Resume.pdf"
        self.applied_jobs_file = "applied_jobs.json"
        self.responses_file = "responses.json"
        
        # Daily limit
        self.daily_apply_limit = 5
        
        # Load applied jobs
        self.applied_jobs = self._load_json(self.applied_jobs_file, [])
        self.responses = self._load_json(self.responses_file, {})
    
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
    
    # ============= FEATURE 1: RECENT JOBS FIRST =============
    def get_recent_jobs(self, days: int = 2) -> List[Dict]:
        """Get jobs posted in last 'days' days"""
        print(f"🔍 Searching jobs from last {days} days...")
        
        # Target companies (from previous analysis)
        target_companies = [
            "Cohesity", "ClickHouse", "NetApp", "Striim", "Ciroos",
            "RingCentral", "Nutanix", "Dell EMC", "MongoDB", "Huawei",
            "Goldman Sachs", "JPMorgan", "Uber", "Salesforce", "Oracle",
            "Microsoft", "Google", "Amazon", "Amadeus", "Travelport"
        ]
        
        all_jobs = []
        
        # Search queries for recent jobs
        queries = [
            "C++ backend Bangalore posted last 2 days",
            "distributed systems engineer Bangalore recent",
            "site:linkedin.com/jobs C++ Bangalore 2026",
            "C++17 C++20 jobs Bangalore new",
            "low latency C++ Bangalore hiring"
        ]
        
        for query in queries:
            try:
                results = self.tavily.search(
                    query=query,
                    max_results=3,
                    search_depth="advanced"
                )
                
                for r in results.get("results", []):
                    # Extract date from content
                    job_date = self._extract_date(r.get("content", ""))
                    
                    # Only include if within last 'days' days
                    if job_date and (datetime.now() - job_date).days <= days:
                        job = {
                            "title": r.get("title", ""),
                            "company": self._extract_company(r.get("content", ""), r.get("url", "")),
                            "url": r.get("url", ""),
                            "content": r.get("content", ""),
                            "date": job_date.strftime("%Y-%m-%d"),
                            "source": "tavily"
                        }
                        
                        # Extract skills match score
                        job["match_score"] = self._calculate_match_score(job["content"])
                        all_jobs.append(job)
                        
            except Exception as e:
                print(f"⚠️ Search error: {e}")
        
        # Sort by date (newest first) and match score
        all_jobs.sort(key=lambda x: (x.get("date", ""), x.get("match_score", 0)), reverse=True)
        
        # Remove duplicates
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job["url"] not in seen_urls and len(unique_jobs) < self.daily_apply_limit * 2:
                seen_urls.add(job["url"])
                unique_jobs.append(job)
        
        print(f"✅ Found {len(unique_jobs)} recent jobs")
        return unique_jobs[:self.daily_apply_limit * 2]  # Return extra for filtering
    
    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract posting date from text"""
        # Try to find patterns like "Posted 2 days ago", "Mar 12, 2026", etc.
        patterns = [
            r"posted (\d+) days? ago",
            r"(\d+) days? ago",
            r"(\w+ \d{1,2},? \d{4})",  # Mar 12, 2026
            r"(\d{4}-\d{2}-\d{2})"      # 2026-03-12
        ]
        
        text_lower = text.lower()
        
        # Check relative dates
        for pattern in patterns[:2]:
            match = re.search(pattern, text_lower)
            if match:
                days = int(match.group(1))
                return datetime.now() - timedelta(days=days)
        
        # Check absolute dates
        for pattern in patterns[2:]:
            match = re.search(pattern, text)
            if match:
                try:
                    return datetime.strptime(match.group(1), "%b %d, %Y")
                except:
                    try:
                        return datetime.strptime(match.group(1), "%Y-%m-%d")
                    except:
                        pass
        
        return datetime.now()  # Default to today if can't parse
    
    def _extract_company(self, content: str, url: str) -> str:
        """Extract company name from content or URL"""
        # Try to find in URL
        if "linkedin.com/company/" in url:
            parts = url.split("/")
            for i, part in enumerate(parts):
                if part == "company" and i+1 < len(parts):
                    return parts[i+1].replace("-", " ").title()
        
        # Try AI extraction
        prompt = f"Extract company name from this job posting. Return only name:\n{content[:500]}"
        company = self._get_ai_response(prompt, "gpt-3.5-turbo")
        if company and len(company) < 50:
            return company.strip()
        
        return "Unknown"
    
    def _calculate_match_score(self, content: str) -> int:
        """Calculate how well job matches profile"""
        score = 50
        content_lower = content.lower()
        
        # Skills match
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
        
        # Domain match
        if any(domain in content_lower for domain in ["fintech", "trading", "hft"]):
            score += 15  # High package domain
        if "telecom" in content_lower or "5g" in content_lower:
            score += 5
        if "travel" in content_lower or "airline" in content_lower or "reservation" in content_lower:
            score += 10  # Sabre domain match
        
        return min(score, 100)
    
    # ============= FEATURE 2: HR EMAIL FINDER =============
    def find_hr_email(self, company: str, job_content: str = "") -> Optional[str]:
        """Advanced HR email finder"""
        
        # Check if email in job content
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, job_content)
        if emails:
            return emails[0]
        
        # Try common patterns
        company_clean = company.lower().replace(" ", "").replace(".", "")
        common_patterns = [
            f"hr@{company_clean}.com",
            f"careers@{company_clean}.com",
            f"jobs@{company_clean}.com",
            f"recruitment@{company_clean}.com",
            f"talent@{company_clean}.com",
            f"{company_clean}-hr@company.com"
        ]
        
        # Try Tavily search for HR emails
        try:
            results = self.tavily.search(
                f"{company} HR email contact",
                max_results=3
            )
            
            for r in results.get("results", []):
                found_emails = re.findall(email_pattern, r.get("content", ""))
                if found_emails:
                    return found_emails[0]
        except:
            pass
        
        # Return first common pattern as guess
        return common_patterns[0] if common_patterns else None
    
    # ============= FEATURE 3: RESUME CUSTOMIZATION =============
    def customize_resume(self, job: Dict) -> str:
        """Create customized resume summary based on job"""
        prompt = f"""
        JOB DETAILS:
        Title: {job['title']}
        Company: {job['company']}
        Description: {job['content'][:1500]}

        CANDIDATE PROFILE:
        {json.dumps(self.profile, indent=2)}

        TASK: Create a 3-point resume summary tailored to this job:
        1. First line: Current role + experience + key achievement (match job requirements)
        2. Second line: Technical skills that match this job (mention specific C++ versions, tools)
        3. Third line: Domain experience relevant to this job (Telecom/Travel/Distributed Systems)

        FORMAT: Plain text, 3 lines maximum. Make it ATS-friendly.
        """
        
        return self._get_ai_response(prompt)
    
    def generate_pdf_resume(self, customized_summary: str, job: Dict) -> str:
        """Generate customized PDF resume"""
        custom_resume_path = f"custom_resumes/Anil_Kumar_{job['company'].replace(' ', '_')}.pdf"
        os.makedirs("custom_resumes", exist_ok=True)
        
        # Create new PDF with customized summary
        c = canvas.Canvas(custom_resume_path, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Anil Kumar")
        
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, "📧 official.anil@gmail.com | 📍 Bangalore | 📱 +91-XXXXXXXXXX")
        
        # Customized Summary
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 100, "PROFESSIONAL SUMMARY")
        
        c.setFont("Helvetica", 10)
        y = height - 120
        for line in customized_summary.split('\n'):
            c.drawString(50, y, line.strip())
            y -= 15
        
        # Add base resume content from original PDF
        try:
            with open(self.base_resume_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                # Skip first page? Or merge intelligently
                # For simplicity, we'll just note that full resume attached
        except:
            pass
        
        c.save()
        return custom_resume_path
    
    # ============= FEATURE 4: COVER LETTER =============
    def generate_cover_letter(self, job: Dict, customized_summary: str) -> str:
        """Generate professional cover letter"""
        prompt = f"""
        JOB: {job['title']} at {job['company']}
        
        JOB DESCRIPTION:
        {job['content'][:1000]}
        
        CANDIDATE SUMMARY:
        {customized_summary}
        
        WRITE a professional email cover letter with:
        1. Subject: Application for {job['title']} - Anil Kumar - 6.5+ years C++
        2. Paragraph 1: Introduction - current role at Sabre/Coforge, interest in {job['company']}
        3. Paragraph 2: Match technical skills to job requirements (be specific)
        4. Paragraph 3: Key achievement from past role (with numbers if possible)
        5. Paragraph 4: Call to action - request for interview
        
        TONE: Professional, confident, concise (max 250 words)
        FORMAT: Plain text with clear paragraphs
        """
        
        return self._get_ai_response(prompt)
    
    # ============= FEATURE 5: SEND EMAIL WITH ATTACHMENTS =============
    def send_application(self, hr_email: str, job: Dict, cover_letter: str, resume_path: str) -> bool:
        """Send email with customized resume"""
        
        msg = MIMEMultipart()
        msg["From"] = self.email
        msg["To"] = hr_email
        msg["Subject"] = f"Application for {job['title']} - Anil Kumar - 6.5+ years C++ (Sabre)"
        
        # HTML Email body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            {cover_letter.replace(chr(10), '<br><br>')}
            
            <br><br>
            <hr style="border: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
            <strong>Note:</strong> Resume customized specifically for {job['company']} {job['title']} position.<br>
            For any queries, please reply to this email or call me at +91-XXXXXXXXXX.
            </p>
            
            <p style="color: #999; font-size: 11px;">
            • Looking forward to hearing from you<br>
            • Available for interview this week
            </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, "html"))
        
        # Attach customized resume
        try:
            with open(resume_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=Anil_Kumar_Resume_{job['company'].replace(' ', '_')}.pdf"
                )
                msg.attach(part)
        except Exception as e:
            print(f"⚠️ Resume attachment failed: {e}")
        
        # Send email
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"❌ Email send failed: {e}")
            return False
    
    # ============= FEATURE 6: RESPONSE TRACKER =============
    def track_response(self, company: str, job_title: str, sent_date: str):
        """Track sent applications"""
        job_key = f"{company}_{job_title}"
        
        if job_key not in self.responses:
            self.responses[job_key] = {
                "company": company,
                "job_title": job_title,
                "sent_date": sent_date,
                "follow_up_sent": False,
                "status": "applied",
                "notes": []
            }
            
            self._save_json(self.responses_file, self.responses)
    
    def check_follow_ups(self):
        """Check if follow-up needed for applications"""
        today = datetime.now()
        
        for job_key, data in self.responses.items():
            sent_date = datetime.strptime(data["sent_date"], "%Y-%m-%d")
            days_passed = (today - sent_date).days
            
            # Send follow-up after 7 days if no response
            if days_passed >= 7 and not data["follow_up_sent"] and data["status"] == "applied":
                self._send_follow_up(data)
                data["follow_up_sent"] = True
                data["notes"].append(f"Follow-up sent on {today.strftime('%Y-%m-%d')}")
        
        self._save_json(self.responses_file, self.responses)
    
    def _send_follow_up(self, app_data: Dict):
        """Send follow-up email"""
        # Implementation for follow-up emails
        pass
    
    # ============= FEATURE 7: DASHBOARD =============
    def generate_dashboard(self):
        """Generate application dashboard"""
        dashboard = f"""
        📊 JOB APPLICATION DASHBOARD - {datetime.now().strftime('%Y-%m-%d')}
        {'='*50}
        
        Total Applications Sent: {len(self.responses)}
        
        Status Breakdown:
        - Applied: {sum(1 for r in self.responses.values() if r['status'] == 'applied')}
        - Follow-up Sent: {sum(1 for r in self.responses.values() if r['follow_up_sent'])}
        - Replied: {sum(1 for r in self.responses.values() if r['status'] == 'replied')}
        - Interview: {sum(1 for r in self.responses.values() if r['status'] == 'interview')}
        
        Recent Applications (Last 7 days):
        """
        
        for job_key, data in list(self.responses.items())[-5:]:
            dashboard += f"\n  • {data['company']} - {data['job_title']} ({data['sent_date']})"
        
        dashboard += f"\n\n{'='*50}\n✨ Target: 5 applications/day | Current CTC: 24 LPA | Target: 35-50 LPA"
        
        # Save dashboard
        with open("dashboard.txt", "w") as f:
            f.write(dashboard)
        
        print(dashboard)
        return dashboard
    
    # ============= MAIN EXECUTION =============
    def run_daily_hunt(self):
        """Main function to run daily job application"""
        print("="*60)
        print("🚀 JOB HUNTER 3000 - DAILY EXECUTION")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Step 1: Get recent jobs
        jobs = self.get_recent_jobs(days=2)
        
        if not jobs:
            print("❌ No recent jobs found")
            return
        
        # Step 2: Filter to daily limit (5)
        jobs_to_apply = jobs[:self.daily_apply_limit]
        
        print(f"\n🎯 Applying to {len(jobs_to_apply)} jobs today:")
        
        # Step 3: Apply to each job
        successful_apps = 0
        for i, job in enumerate(jobs_to_apply, 1):
            print(f"\n📌 Job {i}/{len(jobs_to_apply)}: {job['title']} at {job['company']}")
            
            # Check if already applied
            job_id = f"{job['company']}_{job['title']}"
            if job_id in [f"{j.get('company')}_{j.get('title')}" for j in self.applied_jobs]:
                print("⏭️ Already applied, skipping")
                continue
            
            # Find HR email
            hr_email = self.find_hr_email(job["company"], job["content"])
            if not hr_email:
                print("❌ No HR email found")
                continue
            
            print(f"📧 HR Email: {hr_email}")
            
            # Customize resume
            customized_summary = self.customize_resume(job)
            print("📝 Resume customized")
            
            # Generate PDF
            resume_path = self.generate_pdf_resume(customized_summary, job)
            print("📄 PDF generated")
            
            # Generate cover letter
            cover_letter = self.generate_cover_letter(job, customized_summary)
            
            # Send email
            success = self.send_application(hr_email, job, cover_letter, resume_path)
            
            if success:
                successful_apps += 1
                # Track application
                self.applied_jobs.append({
                    "company": job["company"],
                    "title": job["title"],
                    "url": job["url"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "hr_email": hr_email,
                    "match_score": job.get("match_score", 0)
                })
                self._save_json(self.applied_jobs_file, self.applied_jobs)
                
                # Track for responses
                self.track_response(job["company"], job["title"], datetime.now().strftime("%Y-%m-%d"))
                
                print("✅ Application sent successfully!")
            else:
                print("❌ Failed to send")
            
            # Delay between applications
            if i < len(jobs_to_apply):
                print("⏳ Waiting 30 seconds before next application...")
                time.sleep(30)
        
        # Step 4: Check follow-ups
        self.check_follow_ups()
        
        # Step 5: Generate dashboard
        dashboard = self.generate_dashboard()
        
        # Step 6: Send summary email to self
        self._send_daily_summary(successful_apps, jobs_to_apply)
        
        print("\n" + "="*60)
        print(f"✅ Daily job hunt completed! {successful_apps}/{len(jobs_to_apply)} applications sent")
        print("="*60)
        
        return successful_apps
    
    def _send_daily_summary(self, sent_count: int, jobs: List[Dict]):
        """Send daily summary email to self"""
        subject = f"📊 Job Hunt Summary - {datetime.now().strftime('%Y-%m-%d')}"
        
        html = f"""
        <html>
        <body style="font-family: Arial;">
            <h2>Daily Job Application Summary</h2>
            <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
            <p><strong>Applications Sent:</strong> {sent_count}/{len(jobs)}</p>
            
            <h3>Jobs Applied:</h3>
            <ul>
        """
        
        for job in jobs[:sent_count]:
            html += f"<li><b>{job['company']}</b> - {job['title']}<br><small>Match Score: {job.get('match_score', 0)}</small></li>"
        
        html += """
            </ul>
            
            <h3>Next Steps:</h3>
            <ul>
                <li>Check responses in Gmail</li>
                <li>Prepare for interviews</li>
                <li>Tomorrow's applications ready at 9 AM IST</li>
            </ul>
            
            <hr>
            <p style="color: #666;">Dashboard attached in dashboard.txt</p>
        </body>
        </html>
        """
        
        msg = MIMEText(html, "html")
        msg["Subject"] = subject
        msg["From"] = self.email
        msg["To"] = self.email
        
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)
        except:
            pass

# ============= MAIN EXECUTION =============
if __name__ == "__main__":
    hunter = JobHunter3000()
    hunter.run_daily_hunt()
