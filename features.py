# features.py - All new features in one file (No Tavily)

import json
import re
from datetime import datetime, timedelta
from collections import Counter
import matplotlib.pyplot as plt
import io
import base64

class AdvancedFeatures:
    def __init__(self, hunter):
        self.hunter = hunter
    
    # ============= FEATURE 1: RESPONSE ANALYTICS (UPDATED) =============
    def response_analytics(self):
        """Track and analyze application responses"""
        
        responses = self.hunter.responses
        if not responses:
            return {"message": "No data yet", "total_applications": 0}
        
        total = len(responses)
        
        # Calculate metrics
        companies = [r['company'] for r in responses.values()]
        unique_companies = len(set(companies))
        most_applied = Counter(companies).most_common(3)
        
        # NEW: Count human vs generic emails
        human_count = sum(1 for r in responses.values() if r.get('type') == 'human')
        generic_count = sum(1 for r in responses.values() if r.get('type') == 'generic')
        
        # Match score analysis
        match_scores = [r.get('match_score', 0) for r in responses.values()]
        avg_match = sum(match_scores) / total if match_scores else 0
        
        # Follow-up status
        follow_ups_done = len([f for f in self.hunter.follow_ups if f['status'] == 'follow_up_sent'])
        follow_up_rate = (follow_ups_done / total * 100) if total > 0 else 0
        
        analytics = {
            'total_applications': total,
            'unique_companies': unique_companies,
            'avg_match_score': round(avg_match, 2),
            'follow_up_rate': round(follow_up_rate, 2),
            'top_companies': most_applied,
            'daily_avg': round(total / max(1, (datetime.now() - datetime.strptime(list(responses.values())[0]['sent_date'], '%Y-%m-%d')).days), 2),
            'human_emails': human_count,
            'generic_emails': generic_count,
            'human_percentage': round((human_count/total)*100, 1) if total > 0 else 0
        }
        
        # Generate insights
        insights = []
        if avg_match < 70:
            insights.append("📉 Match score low - Focus on fintech companies")
        if follow_up_rate < 50:
            insights.append("📨 Follow-up more - Increases response rate by 40%")
        if unique_companies < total/2:
            insights.append("🎯 Target more companies - Avoid over-applying to same company")
        if human_count < generic_count:
            insights.append("👤 More generic emails than human - Focus on finding recruiters directly")
        
        analytics['insights'] = insights
        
        # Save analytics
        with open('analytics.json', 'w') as f:
            json.dump(analytics, f, indent=2)
        
        return analytics
    
    # ============= FEATURE 2: COMPANY RESEARCH =============
    def research_company(self, company_name):
        """Deep research on target company using OpenAI only"""
        
        print(f"🔍 Researching {company_name} using AI...")
        
        prompt = f"""
        Provide detailed research about {company_name} for interview preparation:
        
        Include:
        1. Tech Stack - What programming languages, frameworks, tools they use
        2. Engineering Culture - Work-life balance, agile practices, remote work
        3. Interview Process - Typical rounds, difficulty level, common questions
        4. Company Health - Recent funding, growth, market position
        5. Tips for C++ developers interviewing at {company_name}
        
        Format with clear sections and bullet points.
        Be specific and practical for interview prep.
        """
        
        summary = self.hunter._get_ai_response(prompt)
        
        # Save research
        research_file = f"research_{company_name.lower().replace(' ', '_')}.txt"
        with open(research_file, 'w') as f:
            f.write(f"Company Research: {company_name}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write("="*50 + "\n\n")
            f.write(summary)
        
        print(f"✅ Research saved to {research_file}")
        return summary
    
    # ============= FEATURE 3: COMPETITOR TRACKING =============
    def track_competitors(self):
        """Track market trends using AI knowledge"""
        
        print("📈 Analyzing market trends using AI...")
        
        prompt = """
        Analyze current market trends for C++ developers in India (2026):
        
        Provide:
        1. Current salary range for 6-8 years experience C++ developers in Bangalore (in LPA)
        2. Top 10 paying companies for C++ engineers in India
        3. Most in-demand C++ skills right now
        4. Remote work trends for C++ developers
        5. 5 actionable insights for a C++ developer targeting 40-50 LPA package
        
        Base this on general industry knowledge and trends.
        Be specific with numbers and company names.
        """
        
        analysis = self.hunter._get_ai_response(prompt)
        
        # Save trends
        with open('competitor_trends.json', 'w') as f:
            json.dump({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'analysis': analysis
            }, f, indent=2)
        
        print("✅ Competitor analysis saved to competitor_trends.json")
        return analysis
    
    # ============= FEATURE 4: ADVANCED DASHBOARD (UPDATED) =============
    def generate_advanced_dashboard(self):
        """Generate beautiful HTML dashboard with charts"""
        
        analytics = self.response_analytics()
        responses = self.hunter.responses
        
        if analytics.get('total_applications', 0) == 0:
            print("⚠️ No data yet for advanced dashboard")
            return
        
        # Prepare data for charts
        dates = []
        companies = []
        scores = []
        types = []  # NEW: track email types
        
        for r in responses.values():
            dates.append(r['sent_date'])
            companies.append(r['company'])
            scores.append(r.get('match_score', 0))
            types.append(r.get('type', 'unknown'))
        
        # Count by type for chart
        human_count = types.count('human')
        generic_count = types.count('generic')
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Advanced Job Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: 'Segoe UI', Arial; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #1a4d8c, #2a6db0); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .stat-number {{ font-size: 36px; font-weight: bold; color: #1a4d8c; }}
                .stat-label {{ color: #666; margin-top: 10px; }}
                .chart-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }}
                .chart-card {{ background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                table {{ width: 100%; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                th {{ background: #1a4d8c; color: white; padding: 15px; }}
                td {{ padding: 15px; border-bottom: 1px solid #eee; }}
                .insight {{ background: #e8f4fd; padding: 15px; border-radius: 10px; margin: 10px 0; }}
                .competitor {{ background: #fff3cd; padding: 20px; border-radius: 15px; margin-top: 30px; }}
                .human {{ color: #28a745; font-weight: bold; }}
                .generic {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Advanced Job Application Dashboard</h1>
                    <p>Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{analytics['total_applications']}</div>
                        <div class="stat-label">Total Applications</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{analytics['unique_companies']}</div>
                        <div class="stat-label">Unique Companies</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{analytics['avg_match_score']}%</div>
                        <div class="stat-label">Avg Match Score</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{analytics['human_emails']}</div>
                        <div class="stat-label">Human Emails</div>
                    </div>
                </div>
                
                <div class="chart-grid">
                    <div class="chart-card">
                        <h3>Applications by Company</h3>
                        <canvas id="companyChart"></canvas>
                    </div>
                    <div class="chart-card">
                        <h3>Match Score Trend</h3>
                        <canvas id="scoreChart"></canvas>
                    </div>
                    <div class="chart-card">
                        <h3>Email Types</h3>
                        <canvas id="typeChart"></canvas>
                    </div>
                </div>
                
                <div class="insight">
                    <h3>💡 Insights</h3>
                    <ul>
                        {''.join(f'<li>{i}</li>' for i in analytics.get('insights', ['No insights yet']))}
                    </ul>
                </div>
                
                <h2>Recent Applications</h2>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Company</th>
                        <th>Position</th>
                        <th>Match Score</th>
                        <th>Type</th>
                        <th>Status</th>
                    </tr>
                    {''.join(f'''
                    <tr>
                        <td>{r['sent_date']}</td>
                        <td><b>{r['company']}</b></td>
                        <td>{r['job_title'][:40]}</td>
                        <td>{r.get('match_score', 0)}%</td>
                        <td class="{'human' if r.get('type') == 'human' else 'generic'}">{r.get('type', 'unknown')}</td>
                        <td>✅ Applied</td>
                    </tr>
                    ''' for r in list(responses.values())[-10:])}
                </table>
                
                <div class="competitor">
                    <h3>📊 Market Insights</h3>
                    <div id="competitorData">Loading...</div>
                </div>
            </div>
            
            <script>
                // Company chart
                new Chart(document.getElementById('companyChart'), {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps([c[0] for c in analytics.get('top_companies', [])])},
                        datasets: [{{
                            label: 'Applications',
                            data: {json.dumps([c[1] for c in analytics.get('top_companies', [])])},
                            backgroundColor: '#1a4d8c'
                        }}]
                    }}
                }});
                
                // Score chart
                new Chart(document.getElementById('scoreChart'), {{
                    type: 'line',
                    data: {{
                        labels: {json.dumps(dates[-10:])},
                        datasets: [{{
                            label: 'Match Score',
                            data: {json.dumps(scores[-10:])},
                            borderColor: '#2a6db0',
                            tension: 0.1
                        }}]
                    }}
                }});
                
                // Email type chart
                new Chart(document.getElementById('typeChart'), {{
                    type: 'pie',
                    data: {{
                        labels: ['Human Emails', 'Generic Emails'],
                        datasets: [{{
                            data: [{human_count}, {generic_count}],
                            backgroundColor: ['#28a745', '#dc3545']
                        }}]
                    }}
                }});
                
                // Load competitor data
                fetch('competitor_trends.json')
                    .then(r => r.json())
                    .then(d => document.getElementById('competitorData').innerHTML = d.analysis.replace(/\\n/g, '<br>'))
                    .catch(e => document.getElementById('competitorData').innerHTML = 'Market insights will appear here after Monday analysis');
            </script>
        </body>
        </html>
        """
        
        with open('advanced_dashboard.html', 'w') as f:
            f.write(html)
        
        print("✅ Advanced dashboard generated: advanced_dashboard.html")
    
    # ============= FEATURE 5: AUTO-APPLY IMPROVEMENTS =============
    def improved_job_search(self):
        """Better job search suggestions using AI"""
        
        print("🎯 Generating premium job search suggestions...")
        
        prompt = """
        Suggest 10 specific job search queries for a C++ developer targeting 40-50 LPA packages:
        
        Focus on:
        - Fintech companies in Bangalore
        - Low latency systems roles
        - Distributed systems positions
        - High-frequency trading firms
        
        Format each as: "site:linkedin.com/jobs [keywords] Bangalore"
        Also list target companies with their typical C++ roles.
        """
        
        suggestions = self.hunter._get_ai_response(prompt)
        
        # Save suggestions
        with open('job_search_suggestions.txt', 'w') as f:
            f.write("🎯 Premium Job Search Suggestions\n")
            f.write("="*40 + "\n\n")
            f.write(suggestions)
        
        print("✅ Job search suggestions saved to job_search_suggestions.txt")
        return suggestions
