import os
import json
import time
import re
import smtplib
import dns.resolver
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
        
        # Daily limit
        self.daily_apply_limit = 5
        
        # Load applied jobs
        self.applied_jobs = self._load_json(self.applied_jobs_file, [])
        self.responses = self._load_json(self.responses_file, {})
        
        # Fake domains to skip
        self.fake_domains = ['unknown.com', 'example.com', 'company.com', 'domain.com', 'test.com']
    
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
        
        # Skip fake domains
        if any(fake in domain for fake in self.fake_domains) or 'unknown' in domain.lower():
            return False
        
        try:
            # Check if domain has MX records (accepts mail)
            dns.resolver.resolve(domain, 'MX')
            return True
        except:
            try:
                # Fallback to A record
                dns.resolver.resolve(domain, 'A')
                return True
            except:
                return False
    
    def extract_company_name(self, content: str, url: str) -> Optional[str]:
        """Extract company name from job posting"""
        
        # First try from URL
        if url and "linkedin.com" in url:
            # LinkedIn URL patterns
            patterns = [
                r'linkedin\.com/company/([^/?#]+)',
                r'linkedin\.com/jobs/view/[^/]+-at-([^-]+)-'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    company = match.group(1).replace('-', ' ').title()
                    return company
        
        # Then try from content
        content_sample = content[:500]
        
        # Common patterns in job posts
        patterns = [
            r'at ([A-Z][a-zA-Z0-9\s&]+)(?:\s+is hiring|\s+careers|\s+jobs)',
            r'([A-Z][a-zA-Z0-9\s&]+) (?:is looking for|is hiring|careers)',
            r'jobs? at ([A-Z][a-zA-Z0-9\s&]+)',
            r'([A-Z][a-zA-Z0-9\s&]+) (?:Bangalore|Bengalore)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content_sample)
            if match:
                company = match.group(1).strip()
                if len(company) > 2 and len(company) < 50:
                    return company
        
        # Finally use AI
        prompt = f"""Extract ONLY the company name from this job posting.
        Rules:
        - Return ONLY the company name, nothing else
        - If multiple companies, return the hiring company
        - If unsure, return "Unknown"
        
        Text: {content[:500]}"""
        
        company = self._get_ai_response(prompt, "gpt-3.5-turbo")
        if company and company != "Unknown" and len(company) < 50:
            return company.strip()
        
        return None
    
    def get_recent_jobs(self, days: int = 2) -> List[Dict]:
        """Get jobs posted in last 'days' days"""
        print(f"🔍 Searching jobs from last {days} days...")
        
        queries = [
            "site:linkedin.com/jobs C++ backend Bangalore",
            "site:linkedin.com/jobs distributed systems Bangalore",
            "site:linkedin.com/jobs low latency C++ Bangalore",
            "C++ developer Bangalore hiring 2026",
            "C++17 C++20 jobs Bangalore"
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
                    # Extract company name
                    company = self.extract_company_name(
                        r.get("content", ""),
                        r.get("url", "")
                    )
                    
                    # Skip if no company found
                    if not company:
                        continue
                    
                    # Calculate match score
                    match_score = self._calculate_match_score(r.get("content", ""))
                    
                    # Only include if good match
                    if match_score >= 60:
                        job = {
                            "title": r.get("title", ""),
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
        
        # Remove duplicates by URL
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)
        
        # Sort by match score
        unique_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        print(f"✅ Found {len(unique_jobs)} matching jobs")
        return unique_jobs[:self.daily_apply_limit * 2]  # Return extra for filtering
    
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
            score += 15
        if "telecom" in content_lower or "5g" in content_lower:
            score += 5
        if "travel" in content_lower or "airline" in content_lower:
            score += 10
        
        return min(score, 100)
    
    def find_hr_email(self, company: str, job_content: str = "", job_url: str = "") -> Optional[str]:
        """Find HR email ONLY for real companies"""
        
        # Must have valid company
        if not company or company == "Unknown" or len(company) < 3:
            return None
        
        # Skip if not from LinkedIn
        if "linkedin.com" not in job_url.lower():
            return None
        
        # First check job content for emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, job_content)
        
        for email in emails:
            if self.validate_email_domain(email):
                return email
        
        # Generate common HR email patterns
        company_clean = re.sub(r'[^a-zA-Z0-9]', '', company.lower())
        
        # List of companies with known HR email patterns
        known_companies = {
            'cohesity': 'careers',
            'nutanix': 'jobs',
            'netapp': 'careers',
            'dell': 'careers',
            'emc': 'careers',
            'microsoft': 'jobs',
            'google': 'careers',
            'amazon': 'jobs',
            'goldmansachs': 'careers',
            'jpmorgan': 'jobs',
            'uber': 'careers',
            'salesforce': 'careers'
        }
        
        prefix = known_companies.get(company_clean, 'careers')
        candidate_email = f"{prefix}@{company_clean}.com"
        
        if self.validate_email_domain(candidate_email):
            return candidate_email
        
        return None
    
    def generate_resume_summary(self, job: Dict) -> str:
        """Generate customized resume summary"""
        prompt = f"""
        Create a professional resume summary (3-4 lines) for:
        
        Job: {job['title']} at {job['company']}
        Job Description: {job['content'][:800]}
        
        Candidate:
        - Technical Lead at Sabre/Coforge (6.5+ years)
        - Expert in Modern C++ (11/14/17/20), distributed systems
        - Telecom (Amdocs) and Travel domain experience
        
        Rules:
        - Make it ATS-friendly
        - Include specific skills matching the job
        - Mention 30% performance improvement achievement
        - Keep it concise and professional
        """
        
        return self._get_ai_response(prompt, "gpt-3.5-turbo")
    
    def generate_professional_resume(self, job: Dict, summary: str) -> Optional[str]:
        """Generate proper professional resume PDF"""
        
        if not job.get("company") or job["company"] == "Unknown":
            return None
        
        custom_path = f"custom_resumes/Anil_Kumar_{job['company'].replace(' ', '_')}.pdf"
        os.makedirs("custom_resumes", exist_ok=True)
        
        doc = SimpleDocTemplate(custom_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=12
        )
        
        # Header
        story.append(Paragraph("Anil Kumar", title_style))
        story.append(Paragraph("📧 official.anil@gmail.com | 📍 Bangalore", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Customized Summary
        story.append(Paragraph("PROFESSIONAL SUMMARY", styles['Heading2']))
        story.append(Paragraph(summary, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Work Experience
        experience = [
            ["Technical Lead - Coforge (Client: Sabre)", "Nov 2025 - Present"],
            ["• Leading C++ modules for airline reservation systems", ""],
            ["• Optimized multi-threaded components, improved performance by 30%", ""],
            ["", ""],
            ["Senior Consultant - Capgemini", "Mar 2025 - Nov 2025"],
            ["• High-availability C++ backend modules", ""],
            ["", ""],
            ["SDE-2 - CSG", "Jun 2022 - Mar 2025"],
            ["• Modern C++ backend for transaction processing", ""],
            ["", ""],
            ["Software Developer - Amdocs", "Jun 2019 - Jun 2022"],
            ["• Linux-based telecom backend using C++11/14", ""]
        ]
        
        exp_table = Table(experience, colWidths=[4.5*inch, 1.5*inch])
        exp_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        
        story.append(Paragraph("WORK EXPERIENCE", styles['Heading2']))
        story.append(exp_table)
        story.append(Spacer(1, 0.1*inch))
        
        # Technical Skills
        skills = """
        • Languages: Modern C++ (11/14/17/20), C, STL
        • Systems: Linux, IPC (Shared Memory, Pipes, Message Queues)
        • Concurrency: Multithreading, Mutex, Condition Variables
        • Tools: GDB, Valgrind, perf, Google Test, CMake, Git
        """
        story.append(Paragraph("TECHNICAL SKILLS", styles['Heading2']))
        story.append(Paragraph(skills, styles['Normal']))
        
        # Education
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("EDUCATION", styles['Heading2']))
        story.append(Paragraph("Master's in Computer Science - Thapar Institute", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return custom_path
    
    def generate_cover_letter(self, job: Dict) -> Optional[str]:
        """Generate human-like cover letter"""
        
        if not job.get("company") or job["company"] == "Unknown":
            return None
        
        prompt = f"""
        Write a natural, professional job application email for:
        
        Job: {job['title']} at {job['company']}
        Company: {job['company']}
        
        Candidate: Anil Kumar
        - Technical Lead at Sabre/Coforge (6.5+ years C++)
        - Expertise: Modern C++, distributed systems, low-latency systems
        - Key achievement: Led team to improve system performance by 30%
        
        Rules:
        1. DON'T use phrases like "esteemed organization" (too formal)
        2. Sound like a real human wrote it
        3. Be specific about why interested in THIS company
        4. Keep it 150-200 words
        5. Use natural, conversational tone
        
        Format:
        Subject: Application for {job['title']} - Anil Kumar - 6.5+ years C++
        
        Dear Hiring Team at {job['company']},
        
        [Body... make it flow naturally, mention the 30% improvement achievement]
        
        Thanks,
        Anil Kumar
        """
        
        return self._get_ai_response(prompt, "gpt-3.5-turbo")
    
    def send_application(self, job: Dict, hr_email: str, cover_letter: str, resume_path: str) -> bool:
        """Send email with customized resume"""
        
        msg = MIMEMultipart()
        msg["From"] = self.email
        msg["To"] = hr_email
        msg["Subject"] = f"Application for {job['title']} - Anil Kumar - 6.5+ years C++ (Sabre)"
        
        # HTML Email body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            {cover_letter.replace(chr(10), '<br><br>')}
            
            <br>
            <hr style="border: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
            <strong>Note:</strong> Resume customized specifically for {job['company']}.<br>
            Available for interview this week.
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
            return False
        
        # Send email
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
            "follow_up_sent": False,
            "match_score": job.get("match_score", 0)
        }
        
        self._save_json(self.responses_file, self.responses)
        
        # Add to applied jobs list
        self.applied_jobs.append({
            "company": job["company"],
            "title": job["title"],
            "url": job["url"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "hr_email": hr_email
        })
        self._save_json(self.applied_jobs_file, self.applied_jobs)
    
    def generate_dashboard(self):
        """Generate application dashboard"""
        total = len(self.responses)
        today = datetime.now().strftime("%Y-%m-%d")
        
        dashboard = f"""
╔══════════════════════════════════════════════════════════════╗
║                 JOB APPLICATION DASHBOARD                     ║
║                        {today}                                 ║
╠════════════════════════════════════════════════════════════════╣
║                                                              ║
║   📊 Total Applications: {total:<4}                                  ║
║   🎯 Target: 5 per day                                       ║
║   💰 Current CTC: 24 LPA                                     ║
║   🚀 Target CTC: 35-50 LPA                                   ║
║                                                              ║
╠════════════════════════════════════════════════════════════════╣
║                                                              ║
║   📋 Recent Applications:                                     ║
"""
        
        # Last 5 applications
        recent = list(self.responses.items())[-5:]
        for job_key, data in recent:
            dashboard += f"║   • {data['company']:<20} - {data['sent_date']} (Score: {data['match_score']})  ║\n"
        
        dashboard += """
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        
        with open("dashboard.txt", "w") as f:
            f.write(dashboard)
        
        print(dashboard)
        return dashboard
    
    def run_daily_hunt(self):
        """Main function to run daily job application"""
        print("="*70)
        print("🚀 JOB HUNTER 3000 - DAILY EXECUTION")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Get recent jobs
        jobs = self.get_recent_jobs(days=2)
        
        if not jobs:
            print("❌ No matching jobs found today")
            return
        
        # Filter to daily limit
        jobs_to_apply = [j for j in jobs if j.get("match_score", 0) >= 60][:self.daily_apply_limit]
        
        print(f"\n🎯 Applying to {len(jobs_to_apply)} jobs today:")
        
        successful = 0
        for i, job in enumerate(jobs_to_apply, 1):
            print(f"\n📌 Job {i}/{len(jobs_to_apply)}: {job['title']}")
            print(f"   Company: {job['company']}")
            print(f"   Match Score: {job.get('match_score', 0)}")
            
            # Check if already applied
            job_id = f"{job['company']}_{job['title']}"
            if job_id in self.responses:
                print("⏭️ Already applied, skipping")
                continue
            
            # Find HR email
            hr_email = self.find_hr_email(
                job["company"],
                job["content"],
                job["url"]
            )
            
            if not hr_email:
                print("❌ No valid HR email found")
                continue
            
            print(f"📧 HR Email: {hr_email}")
            
            # Generate resume summary
            summary = self.generate_resume_summary(job)
            
            # Generate PDF
            resume_path = self.generate_professional_resume(job, summary)
            if not resume_path:
                print("❌ Resume generation failed")
                continue
            
            # Generate cover letter
            cover_letter = self.generate_cover_letter(job)
            if not cover_letter:
                print("❌ Cover letter generation failed")
                continue
            
            # Send email
            if self.send_application(job, hr_email, cover_letter, resume_path):
                successful += 1
                self.track_application(job, hr_email)
                print("✅ Application sent successfully!")
            else:
                print("❌ Failed to send")
            
            # Delay between applications
            if i < len(jobs_to_apply):
                print("⏳ Waiting 30 seconds...")
                time.sleep(30)
        
        # Generate dashboard
        self.generate_dashboard()
        
        print("\n" + "="*70)
        print(f"✅ Daily job hunt completed! {successful}/{len(jobs_to_apply)} applications sent")
        print("="*70)
        
        return successful

if __name__ == "__main__":
    hunter = JobHunter3000()
    hunter.run_daily_hunt()
