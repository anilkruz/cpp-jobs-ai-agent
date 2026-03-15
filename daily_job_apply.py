import os
import json
import time
import re
import smtplib
import dns.resolver
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
import validate_email_address
from features import AdvancedFeatures

# Load environment variables
load_dotenv()

class JobHunter3000:
    def __init__(self):
        """Initialize all clients and configurations"""
        # API Clients
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Email config
        self.email = os.getenv("EMAIL")
        self.app_password = os.getenv("APP_PASSWORD")
        self.phone = "+91-9557846156"
        
        # SerpAPI key for job search
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        if not self.serpapi_key:
            print("⚠️ WARNING: SERPAPI_KEY not found in environment variables")
            print("💡 Add SERPAPI_KEY to GitHub Secrets for live job search")
        
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
        self.applied_jobs_file = "applied_jobs.json"
        self.responses_file = "responses.json"
        self.follow_ups_file = "follow_ups.json"
        self.manual_review_file = "manual_review_emails.json"
        self.valid_emails_file = "validated_emails.json"
        self.interviews_file = "interviews.json"
        self.learning_tasks_file = "learning_tasks.json"
        
        # Daily limit
        self.daily_apply_limit = 5
        
        # Load all data
        self.applied_jobs = self._load_json(self.applied_jobs_file, [])
        self.responses = self._load_json(self.responses_file, {})
        self.follow_ups = self._load_json(self.follow_ups_file, [])
        self.manual_review = self._load_json(self.manual_review_file, [])
        self.validated_emails = self._load_json(self.valid_emails_file, {})
        self.interviews = self._load_json(self.interviews_file, [])
        self.learning_tasks = self._load_json(self.learning_tasks_file, {})
        
        # Initialize advanced features
        self.advanced = AdvancedFeatures(self)
        
        # Email blacklist - known invalid domains
        self.blacklist_domains = [
            'responsive.com', 'tekit.com', 'example.com', 'test.com',
            'domain.com', 'company.com', 'yourcompany.com', 'sample.com',
            'unknown.com', 'dummy.com', 'fake.com', 'temp.com',
            'mailinator.com', 'guerrillamail.com', 'throwaway.com'
        ]
        
        # Generic email prefixes to avoid
        self.generic_prefixes = [
            'hr', 'careers', 'jobs', 'recruitment', 'talent',
            'info', 'contact', 'support', 'admin', 'hello',
            'career', 'job', 'hiring', 'recruiter'
        ]
    
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
    
    # ============= JOB SEARCH USING SERPAPI (FREE) =============
    def get_recent_jobs(self, days: int = 2) -> List[Dict]:
        """Get jobs using SerpAPI (free - 100 searches/month)"""
        
        print(f"🔍 Searching for C++ jobs using SerpAPI...")
        
        if not self.serpapi_key:
            print("❌ SerpAPI key not found - using fallback jobs")
            return self._get_fallback_jobs()
        
        jobs = []
        
        # SerpAPI Google Jobs search
        params = {
            "api_key": self.serpapi_key,
            "engine": "google_jobs",
            "q": "C++ developer Bangalore",
            "hl": "en",
            "gl": "in",
            "chips": "date_posted:today"  # Recent jobs
        }
        
        try:
            print("   📡 Fetching jobs from SerpAPI...")
            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                jobs_results = data.get("jobs_results", [])
                
                if not jobs_results:
                    print("   ⚠️ No jobs found from SerpAPI")
                    return self._get_fallback_jobs()
                
                for job in jobs_results[:self.daily_apply_limit * 2]:
                    # Extract job details
                    title = job.get("title", "Unknown")
                    company = job.get("company_name", "Unknown")
                    description = job.get("description", "")
                    
                    # Get apply link
                    related_links = job.get("related_links", [])
                    apply_url = ""
                    for link in related_links:
                        if link.get("link", ""):
                            apply_url = link.get("link")
                            break
                    
                    job_data = {
                        "title": title,
                        "company": company,
                        "url": apply_url,
                        "content": description,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "serpapi"
                    }
                    jobs.append(job_data)
                    print(f"   ✅ Found: {title[:40]} at {company}")
            else:
                print(f"❌ SerpAPI error: {response.status_code}")
                return self._get_fallback_jobs()
                
        except Exception as e:
            print(f"❌ SerpAPI exception: {e}")
            return self._get_fallback_jobs()
        
        print(f"✅ Total jobs found: {len(jobs)}")
        return jobs[:self.daily_apply_limit * 2]
    
    def _get_fallback_jobs(self) -> List[Dict]:
        """Fallback hardcoded jobs when API fails"""
        print("📋 Using fallback jobs for testing...")
        
        return [
            {
                "title": "Senior C++ Developer - Distributed Systems",
                "company": "Cisco",
                "url": "https://www.linkedin.com/jobs/view/123456",
                "content": "We are looking for a Senior C++ Developer with expertise in distributed systems, multithreading, and low-latency applications. 6+ years of experience required. Location: Bangalore.",
                "date": datetime.now().strftime("%Y-%m-%d")
            },
            {
                "title": "Lead C++ Engineer - Fintech",
                "company": "Goldman Sachs",
                "url": "https://www.linkedin.com/jobs/view/123457",
                "content": "Goldman Sachs is hiring a Lead C++ Engineer for our fintech division. Experience with high-frequency trading systems, C++17/20, and performance optimization required.",
                "date": datetime.now().strftime("%Y-%m-%d")
            },
            {
                "title": "Distributed Systems Engineer",
                "company": "Microsoft",
                "url": "https://www.linkedin.com/jobs/view/123458",
                "content": "Microsoft is looking for a Distributed Systems Engineer to work on Azure. Strong C++ skills and experience with distributed systems required.",
                "date": datetime.now().strftime("%Y-%m-%d")
            },
            {
                "title": "Low Latency C++ Developer",
                "company": "Uber",
                "url": "https://www.linkedin.com/jobs/view/123459",
                "content": "Uber is hiring a Low Latency C++ Developer for our real-time matching systems. Experience with multithreading and performance optimization required.",
                "date": datetime.now().strftime("%Y-%m-%d")
            },
            {
                "title": "Senior Software Engineer - C++",
                "company": "Dell Technologies",
                "url": "https://www.linkedin.com/jobs/view/123460",
                "content": "Dell is seeking a Senior Software Engineer with strong C++ skills to work on distributed storage systems. Location: Bangalore.",
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        ]
    
    # ============= EMAIL VALIDATION (ZERO BOUNCE) =============
    def validate_email_ultimate(self, email: str, company: str) -> Dict:
        """
        Ultimate email validation with multiple checks
        Returns: {'valid': bool, 'confidence': int, 'reason': str, 'email': str}
        """
        
        result = {
            'valid': False,
            'confidence': 0,
            'reason': '',
            'email': email
        }
        
        # Check 1: Basic format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            result['reason'] = 'Invalid email format'
            return result
        
        domain = email.split('@')[1]
        local_part = email.split('@')[0].lower()
        
        # Check 2: Blacklist domains
        if any(black in domain for black in self.blacklist_domains):
            result['reason'] = 'Domain in blacklist'
            return result
        
        # Check 3: Generic email check
        if local_part in self.generic_prefixes:
            result['confidence'] = 30
            result['reason'] = 'Generic email prefix - may be valid but low confidence'
        
        # Check 4: DNS MX records (primary validation)
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if mx_records:
                result['valid'] = True
                result['confidence'] = max(result['confidence'], 80)
                result['reason'] = 'Valid - MX records found'
                return result
        except Exception as e:
            result['reason'] = f'DNS validation failed: {str(e)}'
            return result
        
        return result
    
    # ============= FIND HUMAN EMAILS FROM JOB CONTENT =============
    def find_human_emails_from_content(self, job: Dict) -> List[Dict]:
        """
        Extract human emails from job posting content
        Returns list of {'email': str, 'name': str, 'confidence': int}
        """
        
        results = []
        content = job.get('content', '')
        company = job.get('company', '')
        
        # Strategy 1: Look for email patterns with names
        email_name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+).*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        matches = re.findall(email_name_pattern, content)
        
        for match in matches:
            if len(match) >= 2:
                name = match[0].strip()
                email = match[1].strip()
                
                validation = self.validate_email_ultimate(email, company)
                if validation['valid']:
                    results.append({
                        'email': email,
                        'name': name,
                        'confidence': validation['confidence'],
                        'source': 'direct_match'
                    })
        
        # Strategy 2: Look for recruiter names and generate emails
        name_pattern = r'(?:recruiter|hiring manager|talent acquisition|contact)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)'
        names = re.findall(name_pattern, content, re.IGNORECASE)
        
        for name in names[:3]:
            try:
                first, last = name.lower().split()
                company_clean = company.lower().replace(' ', '')
                
                email_formats = [
                    f"{first}.{last}@{company_clean}.com",
                    f"{first}@{company_clean}.com",
                    f"{first[0]}{last}@{company_clean}.com"
                ]
                
                for email in email_formats:
                    validation = self.validate_email_ultimate(email, company)
                    if validation['valid']:
                        results.append({
                            'email': email,
                            'name': name,
                            'confidence': validation['confidence'],
                            'source': 'generated_from_name'
                        })
                        break
            except:
                continue
        
        # Strategy 3: Common HR email patterns (fallback)
        company_clean = company.lower().replace(' ', '')
        common_patterns = [
            f"careers@{company_clean}.com",
            f"jobs@{company_clean}.com",
            f"recruitment@{company_clean}.com",
            f"talent@{company_clean}.com",
            f"hr@{company_clean}.com"
        ]
        
        for email in common_patterns:
            validation = self.validate_email_ultimate(email, company)
            if validation['valid']:
                results.append({
                    'email': email,
                    'confidence': validation['confidence'],
                    'source': 'common_pattern'
                })
                break
        
        return results
    
    # ============= JOB EXTRACTION =============
    def extract_job_details(self, content: str, url: str) -> Dict:
        """Extract job title and company from posting"""
        
        # Try from URL first
        if "linkedin.com" in url:
            patterns = [
                r'linkedin\.com/jobs/view/([^/]+)',
                r'linkedin\.com/jobs/([^/]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    title = match.group(1).replace('-', ' ').title()
                    return {"title": title, "company": "Unknown"}
        
        # Use AI for extraction if needed
        prompt = f"""
        Extract job title and company from this posting.
        Return as JSON: {{"title": "...", "company": "..."}}
        
        Text: {content[:500]}
        """
        
        try:
            result = self._get_ai_response(prompt, "gpt-3.5-turbo")
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
        
        return {"title": "Unknown", "company": "Unknown"}
    
    # ============= GET VALIDATED TARGETS =============
    def get_valid_targets(self, job: Dict) -> List[Dict]:
        """
        Get validated email targets for a job
        Returns list of validated targets with confidence scores
        """
        
        targets = []
        company = job['company']
        
        # Check cache first
        cache_key = f"{company}_{job['title']}"
        if cache_key in self.validated_emails:
            cached = self.validated_emails[cache_key]
            if datetime.now().timestamp() - cached.get('timestamp', 0) < 86400:  # 24 hours
                print(f"📦 Using cached email for {company}")
                return cached.get('targets', [])
        
        # Strategy 1: Find human emails from job content
        human_emails = self.find_human_emails_from_content(job)
        for email_data in human_emails:
            targets.append({
                'email': email_data['email'],
                'name': email_data.get('name'),
                'confidence': email_data['confidence'],
                'type': 'human',
                'priority': 1
            })
        
        # Strategy 2: Common HR email patterns (if no human emails found)
        if not targets:
            company_clean = company.lower().replace(' ', '')
            common_patterns = [
                f"careers@{company_clean}.com",
                f"jobs@{company_clean}.com"
            ]
            
            for email in common_patterns:
                validation = self.validate_email_ultimate(email, company)
                if validation['valid']:
                    targets.append({
                        'email': email,
                        'confidence': validation['confidence'],
                        'type': 'common',
                        'priority': 2
                    })
                    break
        
        # Remove duplicates by email
        seen = set()
        unique_targets = []
        for t in targets:
            if t['email'] not in seen:
                seen.add(t['email'])
                unique_targets.append(t)
        
        # Sort by confidence and priority
        unique_targets.sort(key=lambda x: (-x['confidence'], x['priority']))
        
        # Cache results
        self.validated_emails[cache_key] = {
            'targets': unique_targets,
            'timestamp': datetime.now().timestamp()
        }
        self._save_json(self.valid_emails_file, self.validated_emails)
        
        return unique_targets
    
    # ============= CLEAN JOB TITLE =============
    def clean_job_title(self, title: str) -> str:
        """Clean job title - remove extra text"""
        title = re.sub(r'Jobs?.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'Bangalore.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'Bengaluru.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'Karnataka.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'India.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\(\d+\s+new\)', '', title)
        return title.strip()
    
    # ============= GENERATE COVER LETTER =============
    def generate_personalized_letter(self, job: Dict, name: str) -> str:
        """Generate personalized cover letter with EXACT spacing"""
        
        clean_title = self.clean_job_title(job['title'])
        
        prompt = f"""
        Write a professional job application email with EXACT spacing:
        
        To: {name}
        Company: {job['company']}
        Position: {clean_title}
        
        Candidate: Anil Kumar
        - Technical Lead at Sabre/Coforge (6.5+ years)
        - Expertise: Modern C++, distributed systems
        - Key achievement: 30% performance improvement
        
        CRITICAL SPACING RULES:
        1. EXACTLY one blank line between paragraphs (NOT two)
        2. NO blank lines at start or end
        3. Each paragraph: 2-3 sentences only
        4. Total: 4 paragraphs
        
        FORMAT (copy EXACTLY):
        Dear {name},
        
        I am writing to express my interest in the {clean_title} position at {job['company']}. I am currently a Technical Lead at Sabre/Coforge with 6.5+ years of experience building high-performance backend systems using Modern C++.
        
        In my current role, I led a team to optimize multi-threaded components, achieving a 30% improvement in system performance. My expertise includes distributed systems, low-latency programming, and performance optimization on Linux platforms.
        
        I am particularly drawn to {job['company']} because of its reputation for innovation in the tech industry. The opportunity to contribute to cutting-edge projects aligns perfectly with my career aspirations.
        
        I would welcome the opportunity to discuss how my experience can benefit your team. I am available for an interview at your convenience.
        
        Thanks,
        Anil Kumar
        """
        
        letter = self._get_ai_response(prompt, "gpt-3.5-turbo")
        
        # Fix any spacing issues
        if letter:
            letter = re.sub(r'\n\s*\n\s*\n', '\n\n', letter)
            letter = '\n'.join(line.rstrip() for line in letter.split('\n'))
        
        return letter
    
    def generate_cover_letter(self, job: Dict) -> str:
        """Generate standard cover letter with EXACT spacing"""
        
        clean_title = self.clean_job_title(job['title'])
        
        prompt = f"""
        Write a professional job application email with EXACT spacing:
        
        Company: {job['company']}
        Position: {clean_title}
        
        Candidate: Anil Kumar
        - Technical Lead at Sabre/Coforge (6.5+ years)
        - Expertise: Modern C++, distributed systems
        - Key achievement: 30% performance improvement
        
        CRITICAL SPACING RULES:
        1. EXACTLY one blank line between paragraphs (NOT two)
        2. NO blank lines at start or end
        3. Each paragraph: 2-3 sentences only
        4. Total: 4 paragraphs
        
        FORMAT (copy EXACTLY):
        Dear Hiring Team at {job['company']},
        
        I am writing to express my interest in the {clean_title} position at {job['company']}. I am currently a Technical Lead at Sabre/Coforge with 6.5+ years of experience building high-performance backend systems using Modern C++.
        
        In my current role, I led a team to optimize multi-threaded components, achieving a 30% improvement in system performance. My expertise includes distributed systems, low-latency programming, and performance optimization on Linux platforms.
        
        I am particularly drawn to {job['company']} because of its reputation for innovation and technical excellence. The opportunity to work on challenging problems aligns perfectly with my skills and experience.
        
        I would welcome the opportunity to discuss how my experience can benefit your team. I am available for an interview at your convenience.
        
        Thanks,
        Anil Kumar
        """
        
        letter = self._get_ai_response(prompt, "gpt-3.5-turbo")
        
        # Fix any spacing issues
        if letter:
            letter = re.sub(r'\n\s*\n\s*\n', '\n\n', letter)
            letter = '\n'.join(line.rstrip() for line in letter.split('\n'))
        
        return letter
    
    # ============= GENERATE RESUME =============
    def generate_professional_resume(self, job: Dict) -> str:
        """Generate customized resume PDF"""
        
        custom_path = f"custom_resumes/Anil_Kumar_{job['company'].replace(' ', '_')}.pdf"
        os.makedirs("custom_resumes", exist_ok=True)
        
        doc = SimpleDocTemplate(custom_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Styles
        name_style = ParagraphStyle('Name', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1a4d8c'))
        contact_style = ParagraphStyle('Contact', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#777777'))
        section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#1a4d8c'), spaceAfter=8)
        bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'], fontSize=10, leftIndent=20)
        
        # Header
        story.append(Paragraph("ANIL KUMAR", name_style))
        story.append(Paragraph("📧 anilkruz@gmail.com | 📍 Bangalore | 📱 +91-9557846156", contact_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Summary
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
        summary = f"Technical Lead with 6.5+ years at Sabre/Coforge, specializing in Modern C++ and distributed systems. Proven track record of 30% performance improvement. Seeking to leverage expertise at {job['company']}."
        story.append(Paragraph(summary, bullet_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Skills
        story.append(Paragraph("TECHNICAL SKILLS", section_style))
        skills = [
            "• Programming: Modern C++ (11/14/17/20), C, STL",
            "• Systems: Linux, IPC, TCP/IP",
            "• Concurrency: Multithreading, Mutex, Condition Variables",
            "• Tools: GDB, Git, CMake, perf, Valgrind"
        ]
        for skill in skills:
            story.append(Paragraph(skill, bullet_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Experience
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_style))
        experience = [
            "• Technical Lead at Coforge (Sabre) - Nov 2025 to Present",
            "  - Leading C++ modules for airline reservation systems",
            "  - Achieved 30% performance improvement",
            "",
            "• Senior Consultant at Capgemini - Mar 2025 to Nov 2025",
            "  - High-availability C++ backend modules",
            "",
            "• SDE-2 at CSG - Jun 2022 to Mar 2025",
            "  - Modern C++ backend services",
            "",
            "• Software Developer at Amdocs - Jun 2019 to Jun 2022",
            "  - Linux-based telecom systems using C++11/14"
        ]
        for line in experience:
            story.append(Paragraph(line, bullet_style))
        
        doc.build(story)
        return custom_path
    
    # ============= SEND EMAIL =============
    def send_email(self, job: Dict, to_email: str, cover_letter: str, resume_path: str) -> bool:
        """Send email with attachment"""
        
        msg = MIMEMultipart()
        msg["From"] = self.email
        msg["To"] = to_email
        
        # Clean subject
        clean_title = self.clean_job_title(job['title'])
        msg["Subject"] = f"{clean_title} - Anil Kumar - 6.5+ years C++"
        
        # Email body - preserve single line breaks
        html_body = f"""
        <html>
        <body style="font-family: Arial; line-height: 1.5; max-width: 600px; margin: 0 auto;">
            {cover_letter.replace(chr(10), '<br>')}
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, "html"))
        
        # Attach resume
        try:
            with open(resume_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment; filename=Anil_Kumar_Resume.pdf")
                msg.attach(part)
        except Exception as e:
            print(f"❌ Resume attachment failed: {e}")
            return False
        
        # Send
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"❌ Email send failed: {e}")
            return False
    
    # ============= TRACK APPLICATION =============
    def track_application(self, job: Dict, target: Dict):
        """Track successful application"""
        
        job_key = f"{job['company']}_{job['title']}"
        
        self.responses[job_key] = {
            "company": job["company"],
            "job_title": job["title"],
            "sent_date": datetime.now().strftime("%Y-%m-%d"),
            "target_email": target["email"],
            "target_name": target.get("name"),
            "confidence": target["confidence"],
            "status": "applied"
        }
        
        self._save_json(self.responses_file, self.responses)
        
        # Also add to applied jobs
        self.applied_jobs.append({
            "company": job["company"],
            "title": job["title"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "email": target["email"]
        })
        self._save_json(self.applied_jobs_file, self.applied_jobs)
    
    # ============= SCHEDULE FOLLOW-UP =============
    def schedule_follow_up(self, job: Dict, days: int = 7):
        """Schedule follow-up email"""
        
        follow_up = {
            "company": job["company"],
            "job_title": job["title"],
            "sent_date": datetime.now().strftime("%Y-%m-%d"),
            "follow_up_date": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"),
            "status": "scheduled"
        }
        
        self.follow_ups.append(follow_up)
        self._save_json(self.follow_ups_file, self.follow_ups)
        print(f"📅 Follow-up scheduled for {follow_up['follow_up_date']}")
    
    # ============= SEND FOLLOW-UPS =============
    def send_follow_ups(self):
        """Check and send scheduled follow-ups"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        sent = 0
        
        for fu in self.follow_ups:
            if fu["status"] == "scheduled" and fu["follow_up_date"] <= today:
                
                prompt = f"""
                Write a polite follow-up email for:
                
                Company: {fu['company']}
                Position: {fu['job_title']}
                Original Application: {fu['sent_date']}
                
                Keep it short, professional, and not desperate.
                """
                
                follow_up_email = self._get_ai_response(prompt, "gpt-3.5-turbo")
                
                # Fix spacing
                follow_up_email = re.sub(r'\n\s*\n\s*\n', '\n\n', follow_up_email)
                
                # Send to self as reminder
                msg = MIMEText(follow_up_email)
                msg["From"] = self.email
                msg["To"] = self.email
                msg["Subject"] = f"Follow-up: {fu['company']} - {fu['job_title']}"
                
                try:
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                        server.login(self.email, self.app_password)
                        server.send_message(msg)
                    
                    fu["status"] = "follow_up_sent"
                    fu["follow_up_sent_date"] = today
                    sent += 1
                    print(f"✅ Follow-up reminder sent for {fu['company']}")
                except:
                    continue
        
        self._save_json(self.follow_ups_file, self.follow_ups)
        return sent
    
    # ============= INTERVIEW SCHEDULER =============
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
        
        # Send confirmation email
        html = f"""
        <html>
        <body style="font-family: Arial;">
            <h2>✅ Interview Scheduled!</h2>
            <p><b>Company:</b> {company}</p>
            <p><b>Position:</b> {job_title}</p>
            <p><b>Date:</b> {date}</p>
            <p><b>Time:</b> {time}</p>
            {f'<p><b>Link:</b> <a href="{meeting_link}">{meeting_link}</a></p>' if meeting_link else ''}
            
            <h3>Preparation Checklist:</h3>
            <ul>
                <li>Review company background</li>
                <li>Practice C++ concepts</li>
                <li>Prepare questions</li>
                <li>Test audio/video 15 mins before</li>
            </ul>
        </body>
        </html>
        """
        
        msg = MIMEText(html, "html")
        msg["Subject"] = f"🎯 Interview: {company} - {job_title}"
        msg["From"] = self.email
        msg["To"] = self.email
        
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)
            print(f"✅ Interview scheduled with {company}")
            return True
        except:
            return False
    
    # ============= SEND INTERVIEW REMINDERS =============
    def send_interview_reminders(self):
        """Send reminders for upcoming interviews"""
        
        today = datetime.now()
        reminders_sent = 0
        
        for interview in self.interviews:
            if interview.get("reminder_sent"):
                continue
            
            try:
                interview_date = datetime.strptime(f"{interview['date']} {interview['time']}", "%Y-%m-%d %H:%M")
                days_until = (interview_date - today).days
                
                if 0 <= days_until <= 1:  # 0 or 1 day before
                    
                    html = f"""
                    <html>
                    <body style="font-family: Arial;">
                        <h2>🎯 Interview Tomorrow!</h2>
                        <p><b>Company:</b> {interview['company']}</p>
                        <p><b>Position:</b> {interview['job_title']}</p>
                        <p><b>Date:</b> {interview['date']}</p>
                        <p><b>Time:</b> {interview['time']}</p>
                        
                        <h3>Final Checklist:</h3>
                        <ul>
                            <li>✅ Resume printed/ready</li>
                            <li>✅ Company research done</li>
                            <li>✅ Questions prepared</li>
                            <li>✅ Setup ready 30 mins early</li>
                        </ul>
                        
                        <p>Good luck! 💪</p>
                    </body>
                    </html>
                    """
                    
                    msg = MIMEText(html, "html")
                    msg["Subject"] = f"🎯 Interview Tomorrow: {interview['company']}"
                    msg["From"] = self.email
                    msg["To"] = self.email
                    
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                        server.login(self.email, self.app_password)
                        server.send_message(msg)
                    
                    interview["reminder_sent"] = True
                    reminders_sent += 1
                    print(f"✅ Reminder sent for {interview['company']}")
            except:
                continue
        
        self._save_json(self.interviews_file, self.interviews)
        return reminders_sent
    
    # ============= GENERATE LEARNING TASKS =============
    def generate_learning_tasks(self) -> str:
        """Generate daily C++ learning tasks"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check if already generated today
        if today in self.learning_tasks:
            return self.learning_tasks[today]
        
        prompt = """
        Generate 5 C++ and distributed systems learning tasks for today:
        
        Focus areas:
        - Modern C++ (C++17/20 features)
        - Distributed systems concepts
        - Low-latency programming
        - System design for interviews
        
        Format as bullet points with specific topics.
        Keep it practical and interview-focused.
        """
        
        tasks = self._get_ai_response(prompt, "gpt-3.5-turbo")
        
        # Cache it
        self.learning_tasks[today] = tasks
        self._save_json(self.learning_tasks_file, self.learning_tasks)
        
        return tasks
    
    # ============= GENERATE MANUAL REVIEW HTML =============
    def generate_manual_review_html(self):
        """Generate HTML report of emails needing review"""
        
        if not self.manual_review:
            return
        
        html = """
        <html>
        <head>
            <title>Manual Email Review Required</title>
            <style>
                body { font-family: Arial; padding: 20px; background: #f5f5f5; }
                h1 { color: #1a4d8c; }
                table { border-collapse: collapse; width: 100%; background: white; }
                th { background: #1a4d8c; color: white; padding: 12px; text-align: left; }
                td { padding: 12px; border: 1px solid #ddd; }
                .review { background: #fff3cd; }
                .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
                .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .stat-number { font-size: 24px; font-weight: bold; color: #1a4d8c; }
            </style>
        </head>
        <body>
            <h1>📝 Manual Email Review Dashboard</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{}</div>
                    <div>Pending Reviews</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{}</div>
                    <div>Total Applications</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{}</div>
                    <div>Follow-ups Scheduled</div>
                </div>
            </div>
            
            <h2>Emails Requiring Manual Review</h2>
            <table>
                <tr>
                    <th>Company</th>
                    <th>Position</th>
                    <th>Date</th>
                    <th>Reason</th>
                    <th>Action</th>
                </tr>
        """.format(
            len([r for r in self.manual_review if r.get('status') == 'needs_manual_review']),
            len(self.responses),
            len([f for f in self.follow_ups if f['status'] == 'scheduled'])
        )
        
        for item in self.manual_review[-10:]:
            if item.get('status') == 'needs_manual_review':
                html += f"""
                <tr class="review">
                    <td><b>{item['company']}</b></td>
                    <td>{item['job_title'][:50]}</td>
                    <td>{item['date']}</td>
                    <td>{item.get('reason', 'No valid emails found')}</td>
                    <td><a href="{item.get('url', '#')}" target="_blank" style="background: #1a4d8c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px;">View Job</a></td>
                </tr>
                """
        
        # Add recent applications
        html += """
            </table>
            
            <h2>Recent Successful Applications</h2>
            <table>
                <tr>
                    <th>Company</th>
                    <th>Position</th>
                    <th>Date</th>
                    <th>Email</th>
                    <th>Confidence</th>
                </tr>
        """
        
        recent = list(self.responses.items())[-5:]
        for key, data in recent:
            html += f"""
                <tr>
                    <td><b>{data['company']}</b></td>
                    <td>{data['job_title'][:40]}</td>
                    <td>{data['sent_date']}</td>
                    <td>{data['target_email']}</td>
                    <td>{data['confidence']}%</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Upcoming Follow-ups</h2>
            <table>
                <tr>
                    <th>Company</th>
                    <th>Position</th>
                    <th>Follow-up Date</th>
                </tr>
        """
        
        for fu in self.follow_ups[-5:]:
            if fu['status'] == 'scheduled':
                html += f"""
                <tr>
                    <td>{fu['company']}</td>
                    <td>{fu['job_title'][:40]}</td>
                    <td>{fu['follow_up_date']}</td>
                </tr>
                """
        
        html += """
            </table>
            
            <h2>Today's Learning Tasks</h2>
            <div style="background: white; padding: 20px; border-radius: 10px;">
        """
        
        tasks = self.generate_learning_tasks()
        html += tasks.replace('\n', '<br>')
        
        html += """
            </div>
            
            <p style="margin-top: 20px; color: #666;">Generated: {}</p>
        </body>
        </html>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        with open("dashboard.html", "w") as f:
            f.write(html)
        
        print("✅ Dashboard generated: dashboard.html")
    
    # ============= SEND DAILY REPORT =============
    def send_daily_report(self, successful: int, total: int):
        """Send daily report email"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        html = f"""
        <html>
        <body style="font-family: Arial; line-height: 1.5;">
            <h2 style="color: #1a4d8c;">📊 Daily Job Report - {today}</h2>
            
            <h3>Today's Summary:</h3>
            <ul>
                <li>✅ Applications Sent: {successful}/{total}</li>
                <li>📊 Total Applications: {len(self.responses)}</li>
                <li>⏳ Pending Follow-ups: {len([f for f in self.follow_ups if f['status'] == 'scheduled'])}</li>
                <li>🎯 Interviews Scheduled: {len(self.interviews)}</li>
                <li>📝 Manual Review: {len([r for r in self.manual_review if r.get('status') == 'needs_manual_review'])}</li>
            </ul>
            
            <h3>Today's Learning Tasks:</h3>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                {self.generate_learning_tasks().replace(chr(10), '<br>')}
            </div>
            
            <h3>Next Steps:</h3>
            <ol>
                <li>Check dashboard.html for manual reviews</li>
                <li>Prepare for any scheduled interviews</li>
                <li>Complete today's learning tasks</li>
            </ol>
            
            <hr>
            <p style="color: #666;">Target: 35-50 LPA | Keep going! 💪</p>
        </body>
        </html>
        """
        
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
        except:
            return False
    
    # ============= SEND APPLICATION (MAIN) =============
    def send_application_zero_bounce(self, job: Dict) -> bool:
        """
        Send application with zero bounce guarantee
        """
        
        print(f"\n📌 Processing: {job['title']} at {job['company']}")
        
        # Get validated targets
        targets = self.get_valid_targets(job)
        
        if not targets:
            print(f"❌ No valid email targets found for {job['company']}")
            
            self.manual_review.append({
                'company': job['company'],
                'job_title': job['title'],
                'url': job.get('url', ''),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'status': 'needs_manual_review',
                'reason': 'No valid emails found'
            })
            self._save_json(self.manual_review_file, self.manual_review)
            return False
        
        # Try each target
        for target in targets[:2]:
            print(f"📧 Trying: {target['email']} (confidence: {target['confidence']}%)")
            
            if target.get('name'):
                cover_letter = self.generate_personalized_letter(job, target['name'])
            else:
                cover_letter = self.generate_cover_letter(job)
            
            resume_path = self.generate_professional_resume(job)
            
            if self.send_email(job, target['email'], cover_letter, resume_path):
                print(f"✅ Email sent to {target['email']}")
                
                self.track_application(job, target)
                self.schedule_follow_up(job)
                
                return True
        
        print(f"❌ All targets failed for {job['company']}")
        return False
    
    # ============= MAIN FUNCTION =============
    def run_daily_hunt(self):
        """Main execution function"""
        
        print("="*70)
        print("🚀 JOB HUNTER 3000 - ZERO BOUNCE EDITION")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Get jobs
        jobs = self.get_recent_jobs()
        
        if not jobs:
            print("❌ No jobs found")
            return
        
        # Apply to jobs
        jobs_to_apply = jobs[:self.daily_apply_limit]
        successful = 0
        
        for i, job in enumerate(jobs_to_apply, 1):
            print(f"\n{'='*40}")
            print(f"Job {i}/{len(jobs_to_apply)}")
            
            if self.send_application_zero_bounce(job):
                successful += 1
            
            if i < len(jobs_to_apply):
                print("⏳ Waiting 30 seconds...")
                time.sleep(30)
        
        # Send follow-ups
        follow_sent = self.send_follow_ups()
        
        # Send interview reminders
        reminder_sent = self.send_interview_reminders()
        
        # Generate basic dashboard
        self.generate_manual_review_html()
        
        # ============= ADVANCED FEATURES FROM FEATURES.PY =============
        print("\n📊 Generating advanced analytics...")
        try:
            analytics = self.advanced.response_analytics()
            if analytics and analytics.get('avg_match_score'):
                print(f"   Avg Match Score: {analytics['avg_match_score']}%")
                print(f"   Follow-up Rate: {analytics['follow_up_rate']}%")
        except Exception as e:
            print(f"   ⚠️ Analytics failed: {e}")

        # Research top 2 companies
        for job in jobs_to_apply[:2]:
            print(f"\n🔍 Researching {job['company']}...")
            try:
                # Note: research_company uses OpenAI, not Tavily
                research = self.advanced.research_company(job['company'])
                with open(f"research_{job['company'].replace(' ', '_')}.txt", 'w') as f:
                    f.write(research)
                print(f"   ✅ Research saved")
            except Exception as e:
                print(f"   ❌ Research failed: {e}")

        # Track competitors weekly (once a week)
        if datetime.now().weekday() == 0:  # Monday
            print("\n📈 Tracking competitor trends...")
            try:
                trends = self.advanced.track_competitors()
                print("✅ Competitor analysis done")
            except Exception as e:
                print(f"❌ Competitor tracking failed: {e}")

        # Generate advanced dashboard
        try:
            self.advanced.generate_advanced_dashboard()
            print("✅ Advanced dashboard generated")
        except Exception as e:
            print(f"❌ Advanced dashboard failed: {e}")

        # Improved job search for next run (Note: this uses Tavily in features.py)
        # You may want to comment this out or modify features.py
        try:
            # better_jobs = self.advanced.improved_job_search()
            # print(f"\n🎯 Found {len(better_jobs)} premium jobs for next time")
            pass
        except Exception as e:
            print(f"❌ Job search failed: {e}")
        
        # Send daily report
        self.send_daily_report(successful, len(jobs_to_apply))
        
        # Summary
        print(f"\n{'='*70}")
        print(f"✅ Daily hunt completed!")
        print(f"   📨 Successfully sent: {successful}/{len(jobs_to_apply)}")
        print(f"   📅 Follow-ups sent: {follow_sent}")
        print(f"   🎯 Reminders sent: {reminder_sent}")
        print(f"   📝 Manual review: {len([r for r in self.manual_review if r.get('status') == 'needs_manual_review'])}")
        print(f"   📊 Dashboard: dashboard.html")
        print(f"{'='*70}")

if __name__ == "__main__":
    hunter = JobHunter3000()
    hunter.run_daily_hunt()
