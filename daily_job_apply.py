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

# Optional: Selenium for LinkedIn automation
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not installed. Auto-connect will use manual mode.")

# Load environment variables
load_dotenv()

class JobHunter3000:
    # ============= HELPER FUNCTIONS (PEHLE DEFINE) =============
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
    
    # ============= INITIALIZATION =============
    def __init__(self):
        """Initialize all clients and configurations"""
        # API Clients
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Email config
        self.email = os.getenv("EMAIL")
        self.app_password = os.getenv("APP_PASSWORD")
        self.phone = "+91-9557846156"
        
        # LinkedIn credentials
        self.linkedin_email = os.getenv("LINKEDIN_EMAIL")
        self.linkedin_password = os.getenv("LINKEDIN_PASSWORD")
        
        # SerpAPI key
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        if not self.serpapi_key:
            print("⚠️ WARNING: SERPAPI_KEY not found in environment variables")
        
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
        self.recruiters_file = "linkedin_recruiters.json"
        self.linkedin_dms_file = "linkedin_dms.json"
        self.connections_file = "linkedin_connections.json"
        self.auto_apply_log_file = "auto_apply_log.json"
        
        # Daily limits
        self.daily_apply_limit = 3
        self.daily_connect_limit = 5
        self.max_connections_per_day = 20
        
        # Load all data
        self.applied_jobs = self._load_json(self.applied_jobs_file, [])
        self.responses = self._load_json(self.responses_file, {})
        self.follow_ups = self._load_json(self.follow_ups_file, [])
        self.manual_review = self._load_json(self.manual_review_file, [])
        self.validated_emails = self._load_json(self.valid_emails_file, {})
        self.interviews = self._load_json(self.interviews_file, [])
        self.learning_tasks = self._load_json(self.learning_tasks_file, {})
        self.recruiters = self._load_json(self.recruiters_file, [])
        self.linkedin_dms = self._load_json(self.linkedin_dms_file, [])
        self.connections = self._load_json(self.connections_file, [])
        self.auto_apply_log = self._load_json(self.auto_apply_log_file, [])
        
        # Initialize advanced features
        self.advanced = AdvancedFeatures(self)
        
        # Email blacklist
        self.blacklist_domains = [
            'responsive.com', 'tekit.com', 'example.com', 'test.com',
            'domain.com', 'company.com', 'yourcompany.com', 'sample.com',
            'unknown.com', 'dummy.com', 'fake.com', 'temp.com',
            'mailinator.com', 'guerrillamail.com', 'throwaway.com'
        ]
        
        # Generic email prefixes to AVOID
        self.generic_prefixes = [
            'hr', 'careers', 'jobs', 'recruitment', 'talent',
            'info', 'contact', 'support', 'admin', 'hello',
            'career', 'job', 'hiring'
        ]
    
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
    
    # ============= FIND RECRUITERS ON LINKEDIN =============
    def find_linkedin_recruiters(self, company: str, job_title: str) -> List[Dict]:
        """Find recruiters on LinkedIn for specific company"""
        
        print(f"🔍 Searching for recruiters at {company}...")
        
        queries = [
            f"site:linkedin.com/in/ {company} recruiter Bangalore",
            f"site:linkedin.com/in/ {company} talent acquisition",
            f"site:linkedin.com/in/ {company} hiring manager",
            f"site:linkedin.com/in/ Technical Recruiter {company}"
        ]
        
        found_recruiters = []
        
        for query in queries:
            try:
                params = {
                    "api_key": self.serpapi_key,
                    "engine": "google",
                    "q": query,
                    "num": 5
                }
                
                response = requests.get(
                    "https://serpapi.com/search",
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    organic = data.get("organic_results", [])
                    
                    for result in organic[:3]:
                        link = result.get("link", "")
                        title = result.get("title", "")
                        snippet = result.get("snippet", "")
                        
                        if "linkedin.com/in/" in link:
                            # Extract name from title
                            name_match = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+)', title)
                            name = name_match.group(1) if name_match else "Unknown"
                            
                            # Extract profile ID from URL
                            profile_id = link.split("/in/")[-1].split("/")[0]
                            
                            # Try to find email
                            email = self.generate_recruiter_email(name, company)
                            
                            found_recruiters.append({
                                "name": name,
                                "company": company,
                                "profile_url": link,
                                "profile_id": profile_id,
                                "title": title,
                                "email": email,
                                "snippet": snippet,
                                "source": query,
                                "found_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
            except Exception as e:
                print(f"   ⚠️ Search error: {e}")
                continue
        
        # Save recruiters
        self.recruiters.extend(found_recruiters)
        self._save_json(self.recruiters_file, self.recruiters)
        
        print(f"✅ Found {len(found_recruiters)} recruiters at {company}")
        return found_recruiters
    
    def generate_recruiter_email(self, name: str, company: str) -> str:
        """Generate probable recruiter email from name"""
        
        try:
            first, last = name.lower().split()
            company_clean = company.lower().replace(' ', '').replace('.', '')
            
            # Common recruiter email formats
            formats = [
                f"{first}.{last}@{company_clean}.com",
                f"{first}@{company_clean}.com",
                f"{first[0]}{last}@{company_clean}.com",
                f"{last}.{first}@{company_clean}.com",
                f"recruiter.{first}.{last}@{company_clean}.com"
            ]
            
            return formats[0]
        except:
            return f"recruiter@{company.lower().replace(' ', '')}.com"
    
    # ============= LINKEDIN AUTO-CONNECT FEATURE =============
    def connect_with_recruiter(self, recruiter: Dict, job: Dict) -> bool:
        """
        Send LinkedIn connection request to recruiter
        Returns True if successful
        """
        
        if not SELENIUM_AVAILABLE:
            print("⚠️ Selenium not installed. Saving for manual connection.")
            return self._save_manual_connection(recruiter, job)
        
        if not self.linkedin_email or not self.linkedin_password:
            print("⚠️ LinkedIn credentials not found. Saving for manual connection.")
            return self._save_manual_connection(recruiter, job)
        
        # Check daily limit
        today = datetime.now().strftime("%Y-%m-%d")
        today_connections = [c for c in self.connections if c.get('date') == today]
        
        if len(today_connections) >= self.max_connections_per_day:
            print(f"⚠️ Daily connection limit reached ({self.max_connections_per_day})")
            return self._save_manual_connection(recruiter, job)
        
        print(f"🔌 Attempting to connect with {recruiter['name']} on LinkedIn...")
        
        # Custom message for connection
        message = f"""Hi {recruiter['name']},

I came across the {job['title']} position at {recruiter['company']} and I'm very interested. I'm a Technical Lead with 6.5+ years of experience in Modern C++ and distributed systems.

Would love to connect and learn more about opportunities at {recruiter['company']}.

Thanks,
Anil Kumar"""

        # Setup Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = None
        try:
            # Initialize driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            wait = WebDriverWait(driver, 20)
            
            # Step 1: Login to LinkedIn
            print("   📝 Logging into LinkedIn...")
            driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Enter email
            email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_field.send_keys(self.linkedin_email)
            
            # Enter password
            password_field = driver.find_element(By.ID, "password")
            password_field.send_keys(self.linkedin_password)
            
            # Submit
            password_field.send_keys(Keys.RETURN)
            time.sleep(3)
            
            # Check if login successful
            if "feed" not in driver.current_url:
                print("❌ LinkedIn login failed")
                return self._save_manual_connection(recruiter, job)
            
            print("   ✅ Logged in successfully")
            
            # Step 2: Go to recruiter profile
            print(f"   👤 Visiting profile: {recruiter['name']}")
            driver.get(recruiter['profile_url'])
            time.sleep(3)
            
            # Step 3: Click Connect button
            try:
                # Try multiple possible button texts
                connect_selectors = [
                    "button[aria-label*='Invite']",
                    "button[aria-label*='Connect']",
                    "button:contains('Connect')",
                    "//button[contains(@aria-label, 'Invite')]",
                    "//button[contains(@aria-label, 'Connect')]"
                ]
                
                connect_button = None
                for selector in connect_selectors:
                    try:
                        if selector.startswith("//"):
                            connect_button = driver.find_element(By.XPATH, selector)
                        else:
                            connect_button = driver.find_element(By.CSS_SELECTOR, selector)
                        if connect_button:
                            break
                    except:
                        continue
                
                if not connect_button:
                    print("   ⚠️ Connect button not found (maybe already connected)")
                    return self._save_manual_connection(recruiter, job, "already_connected")
                
                driver.execute_script("arguments[0].click();", connect_button)
                time.sleep(2)
                
                # Step 4: Add note
                try:
                    add_note_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Add a note')]")
                    driver.execute_script("arguments[0].click();", add_note_button)
                    time.sleep(1)
                    
                    # Find note textarea
                    note_area = driver.find_element(By.ID, "custom-message")
                    note_area.send_keys(message)
                    time.sleep(1)
                    
                    # Send
                    send_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send invitation')]")
                    driver.execute_script("arguments[0].click();", send_button)
                    
                    print(f"   ✅ Connection request sent with note")
                    
                except:
                    # If no note option, just send without note
                    try:
                        send_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send')]")
                        driver.execute_script("arguments[0].click();", send_button)
                        print(f"   ✅ Connection request sent (no note)")
                    except:
                        print("   ⚠️ Could not send connection")
                        return False
                
                # Record successful connection
                connection_record = {
                    "recruiter_name": recruiter['name'],
                    "recruiter_profile": recruiter['profile_url'],
                    "company": recruiter['company'],
                    "job_title": job['title'],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "message": message,
                    "status": "connected"
                }
                self.connections.append(connection_record)
                self._save_json(self.connections_file, self.connections)
                
                return True
                
            except Exception as e:
                print(f"   ❌ Error during connection: {e}")
                return self._save_manual_connection(recruiter, job)
        
        except Exception as e:
            print(f"❌ LinkedIn automation error: {e}")
            return self._save_manual_connection(recruiter, job)
        
        finally:
            if driver:
                driver.quit()
    
    def _save_manual_connection(self, recruiter: Dict, job: Dict, status: str = "pending") -> bool:
        """Save connection for manual sending"""
        
        connection_record = {
            "recruiter_name": recruiter['name'],
            "recruiter_profile": recruiter['profile_url'],
            "company": recruiter['company'],
            "job_title": job['title'],
            "email": recruiter.get('email'),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "status": status,
            "manual": True,
            "message_template": f"""Hi {recruiter['name']},

I came across the {job['title']} position at {recruiter['company']} and I'm very interested. I'm a Technical Lead with 6.5+ years of experience in Modern C++ and distributed systems.

Would love to connect and learn more about opportunities at {recruiter['company']}.

Thanks,
Anil Kumar"""
        }
        
        self.connections.append(connection_record)
        self._save_json(self.connections_file, self.connections)
        
        print(f"📝 Saved for manual connection: {recruiter['profile_url']}")
        return True
    
    # ============= SEND LINKEDIN DM =============
    def send_linkedin_dm(self, recruiter: Dict, job: Dict) -> bool:
        """Save DM for manual sending"""
        
        message_template = f"""Hi {recruiter['name']},

I hope this message finds you well. I came across the {job['title']} position at {recruiter['company']} and I'm very interested.

I'm a Technical Lead at Sabre/Coforge with 6.5+ years of experience in Modern C++, distributed systems, and low-latency applications. I recently led an optimization initiative that improved system performance by 30%.

Would it be possible to connect and discuss how my experience might align with your team's needs?

Best regards,
Anil Kumar"""
        
        dm_record = {
            "recruiter_name": recruiter['name'],
            "recruiter_profile": recruiter['profile_url'],
            "company": recruiter['company'],
            "job_title": job['title'],
            "message": message_template,
            "status": "pending",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "email": recruiter.get('email')
        }
        
        self.linkedin_dms.append(dm_record)
        self._save_json(self.linkedin_dms_file, self.linkedin_dms)
        
        return True
    
    # ============= IS HUMAN EMAIL =============
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
    
    # ============= EMAIL VALIDATION =============
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
            'type': 'generic'
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
        
        # Check 4: DNS MX records
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
        
        return results
    
    # ============= GET VALIDATED TARGETS =============
    def get_valid_targets(self, job: Dict) -> List[Dict]:
        """
        Get validated email targets - PRIORITIZE RECRUITERS
        """
        
        targets = []
        company = job['company']
        
        # Check cache first
        cache_key = f"{company}_{job['title']}"
        if cache_key in self.validated_emails:
            cached = self.validated_emails[cache_key]
            if datetime.now().timestamp() - cached.get('timestamp', 0) < 86400:
                print(f"📦 Using cached emails for {company}")
                return cached.get('targets', [])
        
        # STRATEGY 1: Find recruiters on LinkedIn (BEST)
        recruiters = self.find_linkedin_recruiters(company, job['title'])
        for rec in recruiters:
            # Try to connect on LinkedIn
            self.connect_with_recruiter(rec, job)
            
            # Also save for DM
            self.send_linkedin_dm(rec, job)
            
            # Add email if available
            validation = self.validate_email_ultimate(rec['email'], company)
            if validation['valid']:
                targets.append({
                    'email': rec['email'],
                    'name': rec['name'],
                    'confidence': 95,
                    'type': 'recruiter',
                    'source': 'linkedin',
                    'profile_url': rec['profile_url'],
                    'profile_id': rec.get('profile_id'),
                    'priority': 1
                })
        
        # STRATEGY 2: Human emails from job content
        if not targets:
            human_emails = self.find_human_emails_from_content(job)
            for email_data in human_emails:
                targets.append({
                    'email': email_data['email'],
                    'name': email_data.get('name'),
                    'confidence': email_data['confidence'],
                    'type': 'human',
                    'source': email_data['source'],
                    'priority': 2
                })
        
        # Remove duplicates
        seen = set()
        unique_targets = []
        for t in targets:
            if t['email'] not in seen:
                seen.add(t['email'])
                unique_targets.append(t)
        
        # Sort by priority
        unique_targets.sort(key=lambda x: x['priority'])
        
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
        
        Position: {cleanTitle}
        
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
    
    # ============= GENERATE RESUME =============
    def generate_professional_resume(self, job: Dict) -> str:
        """Generate beautifully formatted resume PDF"""
        
        custom_path = f"custom_resumes/Anil_Kumar_{job['company'].replace(' ', '_')}.pdf"
        os.makedirs("custom_resumes", exist_ok=True)
        
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
        
        # Custom styles
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
        
        # Header
        story.append(Paragraph("ANIL KUMAR", title_style))
        story.append(Paragraph("Senior C++ Engineer | Distributed Systems | Low Latency", subtitle_style))
        story.append(Paragraph(
            "✉️ anilkruz@gmail.com  |  📍 Bangalore, India  |  📱 +91-9557846156",
            contact_style
        ))
        
        # Summary
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
        summary_text = f"""Results-driven Technical Lead with 6.5+ years of experience at Sabre/Coforge, 
        specializing in Modern C++ (11/14/17/20), distributed systems, and performance optimization. 
        Proven track record of delivering 30% performance improvement through multi-threaded optimization. 
        Seeking to leverage expertise at {job['company']} to build high-performance, scalable systems."""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Skills
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
        
        # Experience
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_style))
        
        # Technical Lead
        story.append(Paragraph("<b>Technical Lead</b> - Coforge (Client: Sabre)", styles['Heading3']))
        story.append(Paragraph("<i>Nov 2025 - Present | Bangalore</i>", styles['Italic']))
        story.append(Paragraph("• Leading development of core C++ modules for large-scale airline reservation systems", bullet_style))
        story.append(Paragraph("• Designed and optimized multi-threaded backend components, achieved <b>30% performance improvement</b>", bullet_style))
        story.append(Paragraph("• Resolved complex race conditions in long-running Linux services using GDB and sanitizers", bullet_style))
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
        
        doc.build(story)
        print(f"✅ Resume generated: {custom_path}")
        return custom_path
    
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
            "type": target["type"],
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
    
    # ============= GENERATE REPORTS =============
    def generate_recruiter_report(self):
        """Generate HTML report of LinkedIn DMs to send"""
        
        pending_dms = [dm for dm in self.linkedin_dms if dm['status'] == 'pending']
        
        if not pending_dms:
            return
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkedIn Recruiter Outreach</title>
            <style>
                body { font-family: Arial; padding: 20px; background: #f5f5f5; }
                h1 { color: #1a4d8c; }
                .dm-card {{ 
                    background: white; 
                    border-radius: 10px; 
                    padding: 20px; 
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .recruiter-name {{ font-size: 18px; font-weight: bold; color: #1a4d8c; }}
                .company {{ color: #666; }}
                .profile-link {{ 
                    background: #1a4d8c; 
                    color: white; 
                    padding: 5px 10px; 
                    text-decoration: none; 
                    border-radius: 5px;
                    display: inline-block;
                    margin: 10px 0;
                }}
                .message {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 5px;
                    white-space: pre-wrap;
                    margin: 10px 0;
                }}
                .email {{ color: #28a745; }}
            </style>
        </head>
        <body>
            <h1>📬 LinkedIn Recruiter Outreach ({})</h1>
        """.format(len(pending_dms))
        
        for dm in pending_dms:
            html += f"""
            <div class="dm-card">
                <div class="recruiter-name">{dm['recruiter_name']}</div>
                <div class="company">{dm['company']} - {dm['job_title']}</div>
                <a href="{dm['recruiter_profile']}" target="_blank" class="profile-link">View LinkedIn Profile</a>
                <div class="email">📧 {dm.get('email', 'No email')}</div>
                <div class="message">{dm['message']}</div>
                <small>Added: {dm['created_at']}</small>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        with open("linkedin_outreach.html", "w") as f:
            f.write(html)
        
        print("✅ LinkedIn outreach report: linkedin_outreach.html")
    
    def generate_connection_report(self):
        """Generate HTML report of LinkedIn connections"""
        
        pending_connections = [c for c in self.connections if c.get('status') == 'pending']
        successful_connections = [c for c in self.connections if c.get('status') == 'connected']
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkedIn Connections Report</title>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                h1, h2 {{ color: #1a4d8c; }}
                .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stat-number {{ font-size: 36px; font-weight: bold; color: #1a4d8c; }}
                .connection-card {{ 
                    background: white; 
                    border-radius: 10px; 
                    padding: 20px; 
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .success {{ border-left: 5px solid #28a745; }}
                .pending {{ border-left: 5px solid #ffc107; }}
                .name {{ font-size: 18px; font-weight: bold; color: #1a4d8c; }}
                .company {{ color: #666; }}
                .profile-link {{ 
                    background: #1a4d8c; 
                    color: white; 
                    padding: 5px 10px; 
                    text-decoration: none; 
                    border-radius: 5px;
                    display: inline-block;
                    margin: 10px 0;
                }}
                .message {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 5px;
                    white-space: pre-wrap;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <h1>🔗 LinkedIn Connections Report</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{len(self.connections)}</div>
                    <div>Total Connections</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(successful_connections)}</div>
                    <div>Successful</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(pending_connections)}</div>
                    <div>Pending</div>
                </div>
            </div>
            
            <h2>✅ Successful Connections</h2>
        """
        
        for conn in successful_connections[-5:]:
            html += f"""
            <div class="connection-card success">
                <div class="name">{conn['recruiter_name']}</div>
                <div class="company">{conn['company']} - {conn.get('job_title', 'Unknown')}</div>
                <a href="{conn['recruiter_profile']}" target="_blank" class="profile-link">View Profile</a>
                <div class="message">{conn.get('message_template', conn.get('message', 'No message'))}</div>
                <small>Connected on: {conn['date']} at {conn.get('time', '')}</small>
            </div>
            """
        
        html += """
            <h2>⏳ Pending Connections</h2>
        """
        
        for conn in pending_connections[-10:]:
            html += f"""
            <div class="connection-card pending">
                <div class="name">{conn['recruiter_name']}</div>
                <div class="company">{conn['company']} - {conn.get('job_title', 'Unknown')}</div>
                <a href="{conn['recruiter_profile']}" target="_blank" class="profile-link">Connect Manually</a>
                <div class="message">{conn.get('message_template', conn.get('message', 'No message'))}</div>
                <small>Added: {conn['date']} at {conn.get('time', '')}</small>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        with open("linkedin_connections.html", "w") as f:
            f.write(html)
        
        print("✅ LinkedIn connections report: linkedin_connections.html")
    
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
        
        html += """
            </table>
        </body>
        </html>
        """
        
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
                <li>🔗 LinkedIn Connections: {len([c for c in self.connections if c.get('status') == 'connected'])}</li>
            </ul>
            
            <h3>Today's Learning Tasks:</h3>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                {self.generate_learning_tasks().replace(chr(10), '<br>')}
            </div>
            
            <h3>Next Steps:</h3>
            <ol>
                <li>Send pending LinkedIn connection requests</li>
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
    
    # ============= SEND APPLICATION =============
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
            target_type = "👤 RECRUITER" if target['type'] == 'recruiter' else "👤 HUMAN" if target['type'] == 'human' else "📧 GENERIC"
            print(f"📧 Trying {target_type}: {target['email']} (confidence: {target['confidence']}%)")
            
            if target.get('name'):
                cover_letter = self.generate_personalized_letter(job, target['name'])
            else:
                cover_letter = self.generate_cover_letter(job)
            
            resume_path = self.generate_professional_resume(job)
            
            if self.send_email(job, target['email'], cover_letter, resume_path):
                print(f"✅ Email sent to {target['email']}")
                
                self.track_application(job, target)
                
                # If recruiter, no need to try others
                if target['type'] in ['recruiter', 'human']:
                    print(f"   Stopping further attempts - priority contact made")
                    return True
                
                self.schedule_follow_up(job)
                return True
        
        print(f"❌ All targets failed for {job['company']}")
        return False
    
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
                
                if 0 <= days_until <= 1:
                    
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
    
    # ============= CLEANUP OLD LOGS =============
    def cleanup_old_logs(self, days=7):
        """Delete logs older than specified days"""
        import shutil
        count = 0
        for f in os.listdir("logs"):
            path = os.path.join("logs", f)
            if os.path.isfile(path):
                file_time = datetime.fromtimestamp(os.path.getmtime(path))
                if (datetime.now() - file_time).days > days:
                    os.remove(path)
                    count += 1
        if count > 0:
            print(f"🧹 Cleaned up {count} old log files")
    
    # ============= MAIN FUNCTION =============
    def run_daily_hunt(self):
        """Main execution function"""
        
        print("="*70)
        print("🚀 JOB HUNTER 3000 - LINKEDIN AUTO-CONNECT EDITION")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Cleanup old logs
        self.cleanup_old_logs()
        
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
            print(f"Job {i}/{len(jobs_to_apply)}: {job['title']} at {job['company']}")
            
            if self.send_application_zero_bounce(job):
                successful += 1
            
            if i < len(jobs_to_apply):
                print("⏳ Waiting 60 seconds...")
                time.sleep(60)
        
        # Send follow-ups
        follow_sent = self.send_follow_ups()
        
        # Send interview reminders
        reminder_sent = self.send_interview_reminders()
        
        # Generate reports
        self.generate_connection_report()
        self.generate_recruiter_report()
        self.generate_manual_review_html()
        
        # Advanced features
        try:
            self.advanced.generate_advanced_dashboard()
        except Exception as e:
            print(f"⚠️ Advanced dashboard error: {e}")
        
        # Send daily report
        self.send_daily_report(successful, len(jobs_to_apply))
        
        # Summary
        successful_connects = len([c for c in self.connections if c.get('status') == 'connected'])
        pending_connects = len([c for c in self.connections if c.get('status') == 'pending'])
        
        print(f"\n{'='*70}")
        print(f"✅ Daily hunt completed!")
        print(f"   📨 Emails sent: {successful}/{len(jobs_to_apply)}")
        print(f"   📅 Follow-ups sent: {follow_sent}")
        print(f"   🎯 Reminders sent: {reminder_sent}")
        print(f"   🔗 LinkedIn connections: {successful_connects} successful, {pending_connects} pending")
        print(f"   📬 DMs pending: {len([dm for dm in self.linkedin_dms if dm['status'] == 'pending'])}")
        print(f"   📊 Reports: linkedin_connections.html, linkedin_outreach.html, dashboard.html")
        print(f"{'='*70}")

if __name__ == "__main__":
    hunter = JobHunter3000()
    hunter.run_daily_hunt()
