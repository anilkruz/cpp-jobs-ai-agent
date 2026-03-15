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
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
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
        
        # Generic email prefixes to avoid (LOW CONFIDENCE)
        self.generic_prefixes = [
            'hr', 'careers', 'jobs', 'recruitment', 'talent',
            'info', 'contact', 'support', 'admin', 'hello',
            'career', 'job', 'hiring', 'recruiter'
        ]
        
        # Human email patterns (HIGH CONFIDENCE)
        self.human_patterns = [
            r'^[a-z]+\.[a-z]+@',  # first.last@
            r'^[a-z]+\.[a-z]+\.[a-z]+@',  # first.m.last@
            r'^[a-z][a-z][a-z]+@',  # initials based
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
    
    # ============= JOB SEARCH USING SERPAPI =============
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
            "chips": "date_posted:today"
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
    
    # ============= IMPROVED EMAIL VALIDATION =============
    def is_human_email(self, email: str) -> bool:
        """Check if email looks like a human (not generic)"""
        local_part = email.split('@')[0].lower()
        
        # Check generic prefixes
        if local_part in self.generic_prefixes:
            return False
        
        # Check patterns that indicate human
        if '.' in local_part and not any(x in local_part for x in ['noreply', 'no-reply']):
            return True
        
        # Check length (humans usually have 5-20 chars)
        if 5 <= len(local_part) <= 20:
            return True
        
        return False
    
    def validate_email_ultimate(self, email: str, company: str) -> Dict:
        """
        Ultimate email validation with multiple checks
        Returns: {'valid': bool, 'confidence': int, 'reason': str, 'email': str, 'type': str}
        """
        
        result = {
            'valid': False,
            'confidence': 0,
            'reason': '',
            'email': email,
            'type': 'generic'  # default type
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
        
        # Check 3: Determine if human or generic
        if self.is_human_email(email):
            result['type'] = 'human'
            result['confidence'] = 70
        else:
            result['type'] = 'generic'
            result['confidence'] = 30
        
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
        Returns list of {'email': str, 'name': str, 'confidence': int, 'type': str}
        """
        
        results = []
        content = job.get('content', '')
        company = job.get('company', '')
        
        # Strategy 1: Look for email patterns with names (HIGHEST CONFIDENCE)
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
                        'type': 'human',
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
                            'type': 'human',
                            'source': 'generated_from_name'
                        })
                        break
            except:
                continue
        
        # Strategy 3: Common HR email patterns (LOW CONFIDENCE - fallback)
        if not results:
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
                        'type': 'generic',
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
    
    # ============= GET VALIDATED TARGETS WITH PROPER TYPE =============
    def get_valid_targets(self, job: Dict) -> List[Dict]:
        """
        Get validated email targets for a job
        Returns list of validated targets with confidence scores and type
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
                'type': email_data['type'],  # 'human' or 'generic'
                'source': email_data['source'],
                'priority': 1 if email_data['type'] == 'human' else 2
            })
        
        # Remove duplicates by email
        seen = set()
        unique_targets = []
        for t in targets:
            if t['email'] not in seen:
                seen.add(t['email'])
                unique_targets.append(t)
        
        # Sort by priority (human first) and confidence
        unique_targets.sort(key=lambda x: (x['priority'], -x['confidence']))
        
        # Cache results
        self.validated_emails[cache_key] = {
            'targets': unique_targets,
            'timestamp': datetime.now().timestamp()
        }
        self._save_json(self.valid_emails_file, self.validated_emails)
        
        return unique_targets
    
    # ============= IMPROVED RESUME GENERATION =============
    def generate_professional_resume(self, job: Dict) -> str:
        """Generate beautifully formatted resume PDF"""
        
        custom_path = f"custom_resumes/Anil_Kumar_{job['company'].replace(' ', '_')}.pdf"
        os.makedirs("custom_resumes", exist_ok=True)
        
        # Create PDF with better formatting
        doc = SimpleDocTemplate(
            custom_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles for better formatting
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            spaceAfter=6,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1a4d8c')
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=12,
            textColor=colors.HexColor('#555555'),
            spaceAfter=12,
            alignment=TA_LEFT
        )
        
        contact_style = ParagraphStyle(
            'ContactStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#777777'),
            spaceAfter=20,
            alignment=TA_LEFT
        )
        
        section_style = ParagraphStyle(
            'SectionStyle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceBefore=12,
            spaceAfter=6,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1a4d8c'),
            borderWidth=1,
            borderColor=colors.HexColor('#cccccc'),
            borderPadding=(0, 0, 3, 0)
        )
        
        bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leftIndent=20,
            spaceAfter=4,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#333333')
        )
        
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            spaceAfter=6,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#444444'),
            leading=14
        )
        
        # Header with better formatting
        story.append(Paragraph("ANIL KUMAR", title_style))
        story.append(Paragraph("Senior C++ Engineer | Distributed Systems | Low Latency", subtitle_style))
        story.append(Paragraph(
            "✉️ anilkruz@gmail.com  |  📍 Bangalore, India  |  📱 +91-9557846156  |  🔗 linkedin.com/in/anil-kumar",
            contact_style
        ))
        
        # Summary section
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
        summary_text = f"""Results-driven Technical Lead with 6.5+ years of experience at Sabre/Coforge, 
        specializing in Modern C++ (11/14/17/20), distributed systems, and performance optimization. 
        Proven track record of delivering 30% performance improvement through multi-threaded optimization. 
        Seeking to leverage expertise at {job['company']} to build high-performance, scalable systems."""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Technical Skills with better formatting
        story.append(Paragraph("TECHNICAL SKILLS", section_style))
        skills_data = [
            ["Programming:", "Modern C++ (11/14/17/20), C, STL, Boost"],
            ["Systems:", "Linux, IPC, TCP/IP, Socket Programming"],
            ["Concurrency:", "Multithreading, Mutex, Condition Variables, Thread Pools"],
            ["Tools:", "GDB, Valgrind, perf, Git, CMake, Google Test"],
            ["Debugging:", "AddressSanitizer, ThreadSanitizer, Core Dump Analysis"],
            ["Domains:", "Telecom (Amdocs), Travel (Sabre), Distributed Systems"]
        ]
        
        for category, items in skills_data:
            story.append(Paragraph(f"• <b>{category}</b>  {items}", bullet_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Experience with better formatting
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_style))
        
        # Technical Lead
        story.append(Paragraph("<b>Technical Lead</b> - Coforge (Client: Sabre)", styles['Heading3']))
        story.append(Paragraph("<i>Nov 2025 - Present | Bangalore</i>", styles['Italic']))
        story.append(Paragraph("• Leading development of core C++ modules for large-scale airline reservation systems", bullet_style))
        story.append(Paragraph("• Designed and optimized multi-threaded backend components, achieved <b>30% performance improvement</b>", bullet_style))
        story.append(Paragraph("• Resolved complex race conditions in long-running Linux services using GDB and sanitizers", bullet_style))
        story.append(Paragraph("• Improved performance-critical paths through CPU profiling (perf) and memory optimization", bullet_style))
        story.append(Spacer(1, 0.05*inch))
        
        # Senior Consultant
        story.append(Paragraph("<b>Senior Consultant</b> - Capgemini", styles['Heading3']))
        story.append(Paragraph("<i>Mar 2025 - Nov 2025 | Gurugram</i>", styles['Italic']))
        story.append(Paragraph("• Developed high-availability C++ backend modules for enterprise clients", bullet_style))
        story.append(Paragraph("• Modernized legacy codebase with C++17 features, improving maintainability", bullet_style))
        story.append(Spacer(1, 0.05*inch))
        
        # SDE-2
        story.append(Paragraph("<b>SDE-2</b> - CSG", styles['Heading3']))
        story.append(Paragraph("<i>Jun 2022 - Mar 2025 | Bangalore</i>", styles['Italic']))
        story.append(Paragraph("• Built scalable C++ backend services for high-throughput transaction processing", bullet_style))
        story.append(Paragraph("• Implemented concurrency control mechanisms in distributed modules", bullet_style))
        story.append(Spacer(1, 0.05*inch))
        
        # Amdocs
        story.append(Paragraph("<b>Software Developer</b> - Amdocs", styles['Heading3']))
        story.append(Paragraph("<i>Jun 2019 - Jun 2022 | Pune</i>", styles['Italic']))
        story.append(Paragraph("• Developed Linux-based telecom systems using Modern C++ (C++11/14)", bullet_style))
        story.append(Paragraph("• Implemented IPC mechanisms for high-throughput environments", bullet_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Education
        story.append(Paragraph("EDUCATION", section_style))
        story.append(Paragraph("<b>Master's Degree in Computer Science</b> - Thapar Institute of Engineering and Technology", normal_style))
        
        # Build PDF
        doc.build(story)
        print(f"✅ Resume generated: {custom_path}")
        return custom_path
    
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
        """Generate personalized cover letter"""
        
        clean_title = self.clean_job_title(job['title'])
        
        prompt = f"""
        Write a professional job application email to {name} at {job['company']}:
        
        Position: {clean_title}
        
        Candidate: Anil Kumar
        - Technical Lead at Sabre/Coforge (6.5+ years)
        - Expertise: Modern C++, distributed systems
        - Key achievement: 30% performance improvement
        
        Write 4 short paragraphs with single line breaks only.
        Sound professional but natural.
        """
        
        letter = self._get_ai_response(prompt, "gpt-3.5-turbo")
        
        if letter:
            letter = re.sub(r'\n\s*\n\s*\n', '\n\n', letter)
            letter = '\n'.join(line.rstrip() for line in letter.split('\n'))
        
        return letter
    
    def generate_cover_letter(self, job: Dict) -> str:
        """Generate standard cover letter"""
        
        clean_title = self.clean_job_title(job['title'])
        
        prompt = f"""
        Write a professional job application email for {job['company']}:
        
        Position: {clean_title}
        
        Candidate: Anil Kumar
        - Technical Lead at Sabre/Coforge (6.5+ years)
        - Expertise: Modern C++, distributed systems
        - Key achievement: 30% performance improvement
        
        Write 4 short paragraphs with single line breaks only.
        Sound professional but natural.
        """
        
        letter = self._get_ai_response(prompt, "gpt-3.5-turbo")
        
        if letter:
            letter = re.sub(r'\n\s*\n\s*\n', '\n\n', letter)
            letter = '\n'.join(line.rstrip() for line in letter.split('\n'))
        
        return letter
    
    # ============= SEND EMAIL =============
    def send_email(self, job: Dict, to_email: str, cover_letter: str, resume_path: str) -> bool:
        """Send email with attachment"""
        
        msg = MIMEMultipart()
        msg["From"] = self.email
        msg["To"] = to_email
        
        # Clean subject
        clean_title = self.clean_job_title(job['title'])
        msg["Subject"] = f"Application for {clean_title} - Anil Kumar - 6.5+ years C++"
        
        # Email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.5; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .signature {{ margin-top: 20px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                {cover_letter.replace(chr(10), '<br><br>')}
                <div class="signature">
                    <hr style="border: none; border-top: 1px solid #eee;">
                    <p style="font-size: 12px;">Anil Kumar | +91-9557846156 | anilkruz@gmail.com</p>
                </div>
            </div>
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
                part.add_header("Content-Disposition", f"attachment; filename=Anil_Kumar_Resume.pdf")
                msg.attach(part)
        except Exception as e:
            print(f"❌ Resume attachment failed: {e}")
            return False
        
        # Send
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)
            print(f"✅ Email sent to {to_email}")
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
            "type": target["type"],  # 'human' or 'generic'
            "status": "applied"
        }
        
        self._save_json(self.responses_file, self.responses)
        
        # Also add to applied jobs
        self.applied_jobs.append({
            "company": job["company"],
            "title": job["title"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "email": target["email"],
            "type": target["type"]
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
        
        # Try each target (prioritize human emails)
        for target in targets[:2]:
            email_type = "👤 HUMAN" if target['type'] == 'human' else "📧 GENERIC"
            print(f"📧 Trying {email_type}: {target['email']} (confidence: {target['confidence']}%)")
            
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
        
        # Generate basic dashboard
        self.generate_manual_review_html()
        
        # Advanced features
        print("\n📊 Generating advanced analytics...")
        try:
            analytics = self.advanced.response_analytics()
            if analytics and analytics.get('avg_match_score'):
                print(f"   Avg Match Score: {analytics['avg_match_score']}%")
                print(f"   Follow-up Rate: {analytics['follow_up_rate']}%")
        except Exception as e:
            print(f"   ⚠️ Analytics failed: {e}")

        # Research top companies
        for job in jobs_to_apply[:2]:
            print(f"\n🔍 Researching {job['company']}...")
            try:
                research = self.advanced.research_company(job['company'])
                with open(f"research_{job['company'].replace(' ', '_')}.txt", 'w') as f:
                    f.write(research)
                print(f"   ✅ Research saved")
            except Exception as e:
                print(f"   ❌ Research failed: {e}")

        # Generate advanced dashboard
        try:
            self.advanced.generate_advanced_dashboard()
            print("✅ Advanced dashboard generated")
        except Exception as e:
            print(f"❌ Advanced dashboard failed: {e}")
        
        # Send daily report
        self.send_daily_report(successful, len(jobs_to_apply))
        
        # Summary
        print(f"\n{'='*70}")
        print(f"✅ Daily hunt completed!")
        print(f"   📨 Successfully sent: {successful}/{len(jobs_to_apply)}")
        print(f"   📅 Follow-ups sent: {follow_sent}")
        print(f"   📝 Manual review: {len([r for r in self.manual_review if r.get('status') == 'needs_manual_review'])}")
        print(f"{'='*70}")

if __name__ == "__main__":
    hunter = JobHunter3000()
    hunter.run_daily_hunt()
