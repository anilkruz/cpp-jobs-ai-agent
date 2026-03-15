# features.py - All new features in one file

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
    
    # ============= FEATURE 1: RESPONSE ANALYTICS =============
    def response_analytics(self):
        """Track and analyze application responses"""
        
        responses = self.hunter.responses
        if not responses:
            return "No data yet"
        
        total = len(responses)
        
        # Calculate metrics
        companies = [r['company'] for r in responses.values()]
        unique_companies = len(set(companies))
        most_applied = Counter(companies).most_common(3)
        
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
            'daily_avg': round(total / max(1, (datetime.now() - datetime.strptime(list(responses.values())[0]['sent_date'], '%Y-%m-%d')).days), 2)
        }
        
        # Generate insights
        insights = []
        if avg_match < 70:
            insights.append("📉 Match score low - Focus on fintech companies")
        if follow_up_rate < 50:
            insights.append("📨 Follow-up more - Increases response rate by 40%")
        if unique_companies < total/2:
            insights.append("🎯 Target more companies - Avoid over-applying to same company")
        
        analytics['insights'] = insights
        
        # Save analytics
        with open('analytics.json', 'w') as f:
            json.dump(analytics, f, indent=2)
        
        return analytics
    
    # ============= FEATURE 2: COMPANY RESEARCH =============
    def research_company(self, company_name):
        """Deep research on target company"""
        
        print(f"🔍 Researching {company_name}...")
        
        queries = [
            f"{company_name} tech stack blog 2026",
            f"{company_name} engineering culture glassdoor",
            f"{company_name} interview process leetcode",
            f"{company_name} funding valuation latest",
            f"{company_name} C++ github repositories"
        ]
        
        research_data = {}
        for query in queries:
            try:
                results = self.hunter.tavily.search(query, max_results=2)
                research_data[query] = [r['content'][:500] for r in results.get('results', [])]
            except:
                research_data[query] = ["No data found"]
        
        # AI Summary
        prompt = f"""
        Summarize key findings about {company_name} for interview prep:
        
        Tech Stack: {research_data.get(f"{company_name} tech stack blog 2026", ["N/A"])}
        Culture: {research_data.get(f"{company_name} engineering culture glassdoor", ["N/A"])}
        Interview: {research_data.get(f"{company_name} interview process leetcode", ["N/A"])}
        Financials: {research_data.get(f"{company_name} funding valuation latest", ["N/A"])}
        Code: {research_data.get(f"{company_name} C++ github repositories", ["N/A"])}
        
        Format:
        1. Tech Stack (C++ version, frameworks)
        2. Culture & Work-life balance
        3. Interview Process (rounds, difficulty)
        4. Company Health (funding, growth)
        5. Tips for interview
        """
        
        summary = self.hunter._get_ai_response(prompt)
        
        # Save research
        research_file = f"research_{company_name.lower().replace(' ', '_')}.json"
        with open(research_file, 'w') as f:
            json.dump({
                'company': company_name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'summary': summary,
                'raw_data': research_data
            }, f, indent=2)
        
        return summary
    
    # ============= FEATURE 3: COMPETITOR TRACKING =============
    def track_competitors(self):
        """Track market trends and competitor activities"""
        
        queries = [
            "C++ developer salary trends Bangalore 2026",
            "top paying companies for C++ engineers India",
            "distributed systems jobs remote Bangalore",
            "how to get 50 LPA package C++ developer",
            "C++14 C++17 interview questions 2026"
        ]
        
        trends = []
        for query in queries:
            try:
                results = self.hunter.tavily.search(query, max_results=2)
                trends.extend([r['content'][:300] for r in results.get('results', [])])
            except:
                continue
        
        # AI Analysis
        prompt = f"""
        Analyze these market trends for C++ developers:
        
        {chr(10).join(trends[:5])}
        
        Give:
        1. Current salary range for 6-8 years C++ (in LPA)
        2. Top 5 paying companies
        3. Most in-demand skills
        4. Remote work trends
        5. 3 actionable insights for job search
        """
        
        analysis = self.hunter._get_ai_response(prompt)
        
        # Save trends
        with open('competitor_trends.json', 'w') as f:
            json.dump({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'analysis': analysis,
                'raw_trends': trends
            }, f, indent=2)
        
        return analysis
    
    # ============= FEATURE 4: ADVANCED DASHBOARD =============
    def generate_advanced_dashboard(self):
        """Generate beautiful HTML dashboard with charts"""
        
        analytics = self.response_analytics()
        responses = self.hunter.responses
        
        # Prepare data for charts
        dates = []
        companies = []
        scores = []
        
        for r in responses.values():
            dates.append(r['sent_date'])
            companies.append(r['company'])
            scores.append(r.get('match_score', 0))
        
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
                .chart-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px; }}
                .chart-card {{ background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                table {{ width: 100%; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                th {{ background: #1a4d8c; color: white; padding: 15px; }}
                td {{ padding: 15px; border-bottom: 1px solid #eee; }}
                .insight {{ background: #e8f4fd; padding: 15px; border-radius: 10px; margin: 10px 0; }}
                .competitor {{ background: #fff3cd; padding: 20px; border-radius: 15px; margin-top: 30px; }}
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
                        <div class="stat-number">{analytics['daily_avg']}</div>
                        <div class="stat-label">Daily Average</div>
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
                        <th>Status</th>
                    </tr>
                    {''.join(f'''
                    <tr>
                        <td>{r['sent_date']}</td>
                        <td><b>{r['company']}</b></td>
                        <td>{r['job_title'][:40]}</td>
                        <td>{r.get('match_score', 0)}%</td>
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
                
                // Load competitor data
                fetch('competitor_trends.json')
                    .then(r => r.json())
                    .then(d => document.getElementById('competitorData').innerHTML = d.analysis.replace(/\\n/g, '<br>'));
            </script>
        </body>
        </html>
        """
        
        with open('advanced_dashboard.html', 'w') as f:
            f.write(html)
        
        print("✅ Advanced dashboard generated: advanced_dashboard.html")
    
    # ============= FEATURE 5: AUTO-APPLY IMPROVEMENTS =============
    def improved_job_search(self):
        """Better job search with fintech focus"""
        
        # Priority companies for high package
        priority_companies = [
            'goldman sachs', 'jpmorgan', 'morgan stanley', 'blackrock',
            'jump trading', 'tower research', 'optiver', 'cisco', 'microsoft',
            'google', 'amazon', 'uber', 'salesforce', 'oracle'
        ]
        
        # Premium keywords
        premium_keywords = [
            'low latency', 'high frequency', 'trading', 'fintech',
            'quant', 'hft', 'core banking', 'payment gateway',
            'distributed systems', 'real time', 'high throughput'
        ]
        
        all_jobs = []
        
        # Search fintech first
        for keyword in premium_keywords[:3]:
            query = f"site:linkedin.com/jobs {keyword} C++ Bangalore"
            try:
                results = self.hunter.tavily.search(query, max_results=3)
                for r in results.get('results', []):
                    job = self.hunter.extract_job_details(r.get('content', ''), r.get('url', ''))
                    if job['company'].lower() in [c.lower() for c in priority_companies]:
                        job['priority'] = '🔥 HIGH PRIORITY'
                    else:
                        job['priority'] = '📌 Standard'
                    all_jobs.append(job)
            except:
                continue
        
        return all_jobs
