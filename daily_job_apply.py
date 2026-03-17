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
        
        # Daily limits
        self.daily_apply_limit = 3
        self.daily_connect_limit = 5
        self.max_connections_per_day = 20  # LinkedIn's limit
        
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
        chrome_options.add_argument("--headless")  # Run in background
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
    
    # ============= GET VALIDATED TARGETS (WITH CONNECT) =============
    def get_valid_targets(self, job: Dict) -> List[Dict]:
        """
        Get validated email targets - with LinkedIn connection
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
    
    # ============= GENERATE REPORTS =============
    def generate_connection_report(self):
        """Generate HTML report of LinkedIn connections"""
        
        pending_connections = [c for c in self.connections if c.get('status') == 'pending']
        successful_connections = [c for c in self.connections if c.get('status') == 'connected']
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkedIn Connections Report</title>
            <style>
                body { font-family: Arial; padding: 20px; background: #f5f5f5; }
                h1, h2 { color: #1a4d8c; }
                .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
                .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .stat-number { font-size: 36px; font-weight: bold; color: #1a4d8c; }
                .connection-card { 
                    background: white; 
                    border-radius: 10px; 
                    padding: 20px; 
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .success { border-left: 5px solid #28a745; }
                .pending { border-left: 5px solid #ffc107; }
                .name { font-size: 18px; font-weight: bold; color: #1a4d8c; }
                .company { color: #666; }
                .profile-link { 
                    background: #1a4d8c; 
                    color: white; 
                    padding: 5px 10px; 
                    text-decoration: none; 
                    border-radius: 5px;
                    display: inline-block;
                    margin: 10px 0;
                }
                .message { 
                    background: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 5px;
                    white-space: pre-wrap;
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <h1>🔗 LinkedIn Connections Report</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{}</div>
                    <div>Total Connections</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{}</div>
                    <div>Successful</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{}</div>
                    <div>Pending</div>
                </div>
            </div>
            
            <h2>✅ Successful Connections</h2>
        """.format(
            len(self.connections),
            len(successful_connections),
            len(pending_connections)
        )
        
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
    
    # ============= MAIN FUNCTION (UPDATED) =============
    def run_daily_hunt(self):
        """Main execution function"""
        
        print("="*70)
        print("🚀 JOB HUNTER 3000 - LINKEDIN AUTO-CONNECT EDITION")
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
            print(f"Job {i}/{len(jobs_to_apply)}: {job['title']} at {job['company']}")
            
            # This will now also find recruiters and send connection requests
            if self.send_application_zero_bounce(job):
                successful += 1
            
            # Add delay between jobs
            if i < len(jobs_to_apply):
                print("⏳ Waiting 60 seconds...")
                time.sleep(60)
        
        # Generate reports
        self.generate_connection_report()
        self.generate_recruiter_report()
        self.generate_manual_review_html()
        
        # Advanced features
        try:
            self.advanced.generate_advanced_dashboard()
        except:
            pass
        
        # Summary
        successful_connects = len([c for c in self.connections if c.get('status') == 'connected'])
        pending_connects = len([c for c in self.connections if c.get('status') == 'pending'])
        
        print(f"\n{'='*70}")
        print(f"✅ Daily hunt completed!")
        print(f"   📨 Emails sent: {successful}/{len(jobs_to_apply)}")
        print(f"   🔗 LinkedIn connections: {successful_connects} successful, {pending_connects} pending")
        print(f"   📬 DMs pending: {len([dm for dm in self.linkedin_dms if dm['status'] == 'pending'])}")
        print(f"   📊 Reports: linkedin_connections.html, linkedin_outreach.html")
        print(f"{'='*70}")

if __name__ == "__main__":
    hunter = JobHunter3000()
    hunter.run_daily_hunt()
