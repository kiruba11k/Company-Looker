import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from datetime import datetime, timedelta
import time
from groq import Groq
import io
import urllib.parse

# Page configuration
st.set_page_config(
    page_title="🏢 AI Company Scout - Hybrid Edition",
    page_icon="🔍",
    layout="wide"
)

class HybridCompanyScout:
    def __init__(self):
        self.groq_client = Groq(api_key=st.secrets.get("GROQ_API_KEY"))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_google_news_rss(self, query, max_results=20, days_back=None):
        """Free Google News RSS search with date filtering"""
        try:
            base_url = "https://news.google.com/rss"
            
            # Add date filtering to query
            dated_query = query
            if days_back:
                dated_query = f"{query} when:{days_back}d"
            
            search_url = f"{base_url}/search?q={dated_query.replace(' ', '%20')}&hl=en-IN&gl=IN&ceid=IN:en"
            
            response = self.session.get(search_url, timeout=15)
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                articles = []
                for item in root.findall('.//item')[:max_results]:
                    title = item.find('title').text if item.find('title') is not None else ''
                    link = item.find('link').text if item.find('link') is not None else ''
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                    description = item.find('description').text if item.find('description') is not None else ''
                    
                    # Clean HTML tags from description
                    description = re.sub(r'<[^>]+>', '', description)
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'source': 'Google News',
                        'date': pub_date,
                        'content': f"{title}. {description}"
                    })
                
                return articles
            return []
        except Exception as e:
            st.error(f"Google News error: {str(e)}")
            return []

    def search_duckduckgo_news(self, query, max_results=15, days_back=365):
        """DuckDuckGo search with date filtering"""
        try:
            # Calculate date range (from Jan 2024)
            start_date = "2024-01-01"
            
            # DuckDuckGo search with date filter
            base_url = "https://html.duckduckgo.com/html/"
            dated_query = f"{query} after:{start_date}"
            
            params = {
                'q': dated_query,
                'kl': 'in-en',
                'df': 'm'  # Recent results
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = self.session.post(base_url, data=params, headers=headers, timeout=20)
            articles = []
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                results = soup.find_all('div', class_='result')
                
                for result in results[:max_results]:
                    try:
                        title_elem = result.find('a', class_='result__a')
                        snippet_elem = result.find('a', class_='result__snippet')
                        
                        if title_elem:
                            title = title_elem.text.strip()
                            link = title_elem.get('href')
                            snippet = snippet_elem.text.strip() if snippet_elem else ""
                            
                            # Extract actual URL from DuckDuckGo redirect
                            if link and 'uddg=' in link:
                                match = re.search(r'uddg=([^&]+)', link)
                                if match:
                                    link = urllib.parse.unquote(match.group(1))
                            
                            # Only include valid news links
                            if link and any(domain in link for domain in ['.com', '.in', '.org', '.net']):
                                articles.append({
                                    'title': title,
                                    'link': link,
                                    'description': snippet,
                                    'source': 'DuckDuckGo',
                                    'date': '2024+',
                                    'content': f"{title}. {snippet}"
                                })
                    except Exception:
                        continue
                
                return articles
            else:
                return []
                
        except Exception as e:
            st.error(f"DuckDuckGo search error: {str(e)}")
            return []

    def search_bing_news_free(self, query, max_results=10):
        """Free Bing news search alternative"""
        try:
            # Use Bing search with news filter
            search_url = "https://www.bing.com/news/search"
            params = {
                'q': f"{query} India construction site:news",
                'qft': 'sortbydate="1"',  # Sort by date
                'form': 'YFNR'
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            articles = []
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                news_cards = soup.find_all('div', class_='news-card')
                
                for card in news_cards[:max_results]:
                    try:
                        title_elem = card.find('a', class_='title')
                        if title_elem:
                            title = title_elem.text.strip()
                            link = title_elem.get('href')
                            description = ""
                            
                            desc_elem = card.find('div', class_='snippet')
                            if desc_elem:
                                description = desc_elem.text.strip()
                            
                            articles.append({
                                'title': title,
                                'link': link,
                                'description': description,
                                'source': 'Bing News',
                                'date': 'Recent',
                                'content': f"{title}. {description}"
                            })
                    except Exception:
                        continue
                
                return articles
            return []
            
        except Exception as e:
            return []

    def hybrid_search(self, search_terms, max_results_per_source=15, use_duckduckgo=True, use_google=True):
        """Hybrid search across multiple free sources"""
        all_articles = []
        
        for term in search_terms:
            if use_google:
                st.info(f"🔍 Searching Google News for: {term}")
                google_articles = self.search_google_news_rss(term, max_results_per_source, days_back=365)
                all_articles.extend(google_articles)
                time.sleep(1)
            
            if use_duckduckgo:
                st.info(f"🔍 Searching DuckDuckGo for: {term}")
                ddg_articles = self.search_duckduckgo_news(term, max_results_per_source)
                all_articles.extend(ddg_articles)
                time.sleep(1)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article['link'] not in seen_urls:
                seen_urls.add(article['link'])
                unique_articles.append(article)
        
        return unique_articles

    def get_search_queries(self, project_types, sectors):
        """Generate targeted search queries based on user selection"""
        base_queries = []
        
        # Greenfield projects (new construction)
        if "Greenfield Projects" in project_types:
            base_queries.extend([
                "new construction India",
                "greenfield project India", 
                "new facility construction",
                "groundbreaking ceremony India",
                "new plant construction India"
            ])
        
        # Brownfield projects (expansion)
        if "Brownfield Projects" in project_types:
            base_queries.extend([
                "expansion project India",
                "capacity expansion India",
                "brownfield expansion",
                "facility expansion India",
                "plant expansion India"
            ])
        
        # Sector-specific queries
        sector_queries = []
        for sector in sectors:
            if sector == "Airports":
                sector_queries.extend(["new airport construction", "airport terminal expansion", "airport modernization"])
            elif sector == "Ports":
                sector_queries.extend(["port expansion", "new terminal port", "maritime infrastructure"])
            elif sector == "Malls":
                sector_queries.extend(["new mall construction", "shopping complex inauguration", "retail expansion"])
            elif sector == "Hospitals":
                sector_queries.extend(["new hospital construction", "medical facility expansion", "healthcare infrastructure"])
            elif sector == "Commercial":
                sector_queries.extend(["commercial complex", "office building construction", "business park development"])
            elif sector == "Industrial":
                sector_queries.extend(["factory construction", "industrial plant", "manufacturing facility"])
        
        # Combine base queries with sector queries
        final_queries = []
        for base in base_queries:
            final_queries.append(base)
            for sector in sector_queries:
                final_queries.append(f"{base} {sector}")
        
        return list(set(final_queries))[:10]  # Limit to 10 unique queries

    def extract_companies_from_articles(self, articles):
        """Use Groq to intelligently extract company information with project classification"""
        if not articles:
            return []
            
        extracted_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, article in enumerate(articles):
            try:
                status_text.text(f"🤖 Analyzing article {i+1}/{len(articles)}...")
                progress_bar.progress((i + 1) / len(articles))
                
                content = article['content']
                if len(content) > 3000:
                    content = content[:3000]
                
                system_prompt = """You are an expert Indian business analyst. Extract companies and classify projects as GREENFIELD (new construction) or BROWNFIELD (expansion).

                GREENFIELD PROJECTS: New construction, new facilities, completely new projects
                BROWNFIELD PROJECTS: Expansion, capacity increase, modernization of existing facilities

                Also identify the SECTOR: Airport, Port, Mall, Hospital, Commercial, Industrial, Residential, Infrastructure

                Return JSON format:
                {
                    "companies": [
                        {
                            "company_name": "extracted company name",
                            "core_intent": "what they are building/doing",
                            "stage": "completion stage/timeline",
                            "project_type": "Greenfield/Brownfield",
                            "sector": "Airport/Port/Mall/Hospital/Commercial/Industrial/Infrastructure",
                            "confidence": "high/medium/low"
                        }
                    ]
                }

                If no companies found, return: {"companies": []}"""
                
                user_prompt = f"""
                Analyze this Indian business/construction news article:

                TITLE: {article['title']}
                CONTENT: {content}

                Extract ALL companies and classify their projects. Focus on Indian infrastructure, construction, and development projects.
                """
                
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model="mixtral-8x7b-32768",
                    temperature=0.1,
                    max_tokens=1500,
                    response_format={"type": "json_object"}
                )
                
                response_text = chat_completion.choices[0].message.content
                
                try:
                    data = json.loads(response_text.strip())
                    companies = data.get('companies', [])
                    
                    for company in companies:
                        if company.get('company_name') and company.get('company_name') != 'null':
                            # Add to results with article info
                            extracted_data.append({
                                'Company Name': company['company_name'],
                                'Source Link': article['link'],
                                'Core Intent': company.get('core_intent', 'Construction Project'),
                                'Stage': company.get('stage', 'Under Construction'),
                                'Project Type': company.get('project_type', 'Unknown'),
                                'Sector': company.get('sector', 'Infrastructure'),
                                'Confidence': company.get('confidence', 'medium'),
                                'Article Title': article['title'],
                                'Source': article['source'],
                                'Date': article.get('date', '2024+')
                            })
                            
                except json.JSONDecodeError:
                    continue
                    
            except Exception as e:
                continue
        
        progress_bar.empty()
        status_text.empty()
        return extracted_data

    def filter_and_rank_companies(self, companies):
        """Filter and rank companies by relevance"""
        if not companies:
            return []
        
        # Score companies based on multiple factors
        for company in companies:
            score = 0
            
            # Confidence scoring
            if company['Confidence'] == 'high':
                score += 3
            elif company['Confidence'] == 'medium':
                score += 2
            else:
                score += 1
            
            # Timeline keywords boost
            stage = company['Stage'].lower()
            timeline_keywords = ['month', 'complet', 'inaugurat', 'open', 'launch', 'deadline', 'final']
            if any(keyword in stage for keyword in timeline_keywords):
                score += 2
            
            # Project type preference
            if company['Project Type'] in ['Greenfield', 'Brownfield']:
                score += 2
            
            # Sector relevance
            sector = company['Sector'].lower()
            priority_sectors = ['airport', 'port', 'mall', 'commercial', 'industrial']
            if any(priority in sector for priority in priority_sectors):
                score += 1
            
            company['Relevance Score'] = score
        
        # Sort by relevance and remove duplicates
        companies.sort(key=lambda x: x['Relevance Score'], reverse=True)
        
        # Remove duplicates based on company name + project
        seen_companies = set()
        unique_companies = []
        for company in companies:
            company_key = f"{company['Company Name'].lower().strip()}_{company['Core Intent'][:50]}"
            if company_key not in seen_companies:
                seen_companies.add(company_key)
                unique_companies.append(company)
        
        return unique_companies

    def generate_tsv_output(self, companies):
        """Generate TSV output with all fields"""
        if not companies:
            return "No companies found"
        
        tsv_lines = ["Company Name\tSource Link\tCore Intent\tStage\tProject Type\tSector\tConfidence"]
        for company in companies:
            company_name = str(company['Company Name']).replace('\t', ' ').replace('\n', ' ')
            source_link = str(company['Source Link']).replace('\t', ' ')
            core_intent = str(company['Core Intent']).replace('\t', ' ').replace('\n', ' ')
            stage = str(company['Stage']).replace('\t', ' ').replace('\n', ' ')
            project_type = str(company['Project Type']).replace('\t', ' ')
            sector = str(company['Sector']).replace('\t', ' ')
            confidence = str(company['Confidence']).replace('\t', ' ')
            
            tsv_line = f"{company_name}\t{source_link}\t{core_intent}\t{stage}\t{project_type}\t{sector}\t{confidence}"
            tsv_lines.append(tsv_line)
        
        return "\n".join(tsv_lines)

def main():
    st.title("AI Company Scout - Hybrid Edition")
    st.markdown("### Multi-Source Search for Indian Greenfield & Brownfield Projects")
    
    if not st.secrets.get("GROQ_API_KEY"):
        st.error(" Groq API key required (free at https://console.groq.com)")

        return
    
    scout = HybridCompanyScout()
    
    with st.sidebar:
        st.header("Search Configuration")
        
        st.subheader("Project Types")
        project_types = st.multiselect(
            "Select Project Types:",
            ["Greenfield Projects", "Brownfield Projects"],
            default=["Greenfield Projects", "Brownfield Projects"]
        )
        
        st.subheader("Target Sectors")
        sectors = st.multiselect(
            "Select Sectors:",
            ["Airports", "Ports", "Malls", "Hospitals", "Commercial", "Industrial", "Infrastructure"],
            default=["Airports", "Ports", "Malls", "Commercial"]
        )
        
        st.subheader("Search Sources")
        use_google = st.checkbox("Use Google News", value=True)
        use_duckduckgo = st.checkbox("Use DuckDuckGo", value=True)
        
        st.subheader("Search Settings")
        max_articles = st.slider("Articles to Analyze", 10, 100, 30)
        max_per_source = st.slider("Results per Search", 5, 30, 15)
        
        st.info("""
        **Date Range:** All searches filtered from January 2024 onwards
        **Greenfield:** New construction projects
        **Brownfield:** Expansion of existing facilities
        """)
    
    st.header("🚀 Hybrid Multi-Source Search")
    
    if st.button("🎯 Start Advanced Search", type="primary", use_container_width=True):
        # Generate targeted search queries
        search_queries = scout.get_search_queries(project_types, sectors)
        
        st.info(f"🔍 Using {len(search_queries)} targeted search queries")
        
        with st.spinner("🌐 Searching across multiple sources..."):
            # Perform hybrid search
            articles = scout.hybrid_search(
                search_queries, 
                max_per_source, 
                use_duckduckgo, 
                use_google
            )
            
            if not articles:
                st.error("""
                ❌ No articles found. Possible issues:
                - Internet connection problem
                - Search engines temporarily unavailable
                - Try different search terms or sectors
                """)
                return
            
            st.success(f" Found {len(articles)} articles from {len(set(a['source'] for a in articles))} sources")
            
            # Show search summary
            col1, col2, col3 = st.columns(3)
            with col1:
                google_count = len([a for a in articles if a['source'] == 'Google News'])
                st.metric("Google News", google_count)
            with col2:
                ddg_count = len([a for a in articles if a['source'] == 'DuckDuckGo'])
                st.metric("DuckDuckGo", ddg_count)
            with col3:
                st.metric("Total Sources", len(set(a['source'] for a in articles)))
            
            # Show sample articles
            with st.expander(" View Sample Articles"):
                for i, article in enumerate(articles[:]):
                    st.write(f"**{i+1}. {article['title']}**")
                    st.write(f"**Source:** {article['source']}")
                    st.write(f"**Link:** {article['link']}")
                    st.write("---")
        
        with st.spinner(" AI analyzing articles for companies and project types..."):
            # Extract companies using AI
            companies_data = scout.extract_companies_from_articles(articles[:max_articles])
            
            if not companies_data:
                st.error("""
                ❌ No companies extracted. This could mean:
                - Articles don't contain specific company names
                - Try different sectors or project types
                - News coverage might be limited for selected criteria
                """)
                return
            
            # Filter and rank companies
            ranked_companies = scout.filter_and_rank_companies(companies_data)
            
            st.success(f" Found {len(ranked_companies)} companies with {len(set(c['Project Type'] for c in ranked_companies))} project types!")
        
        # Display results
        st.header(" Discovery Results")
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Articles Analyzed", len(articles[:max_articles]))
        with col2:
            st.metric("Companies Found", len(ranked_companies))
        with col3:
            greenfield_count = len([c for c in ranked_companies if c['Project Type'] == 'Greenfield'])
            st.metric("Greenfield", greenfield_count)
        with col4:
            brownfield_count = len([c for c in ranked_companies if c['Project Type'] == 'Brownfield'])
            st.metric("Brownfield", brownfield_count)
        
        # Sector distribution
        if ranked_companies:
            sectors_count = {}
            for company in ranked_companies:
                sector = company['Sector']
                sectors_count[sector] = sectors_count.get(sector, 0) + 1
            
            st.subheader(" Sector Distribution")
            sector_df = pd.DataFrame(list(sectors_count.items()), columns=['Sector', 'Count'])
            st.bar_chart(sector_df.set_index('Sector'))
        
        # Company details table
        st.subheader(" Company Details")
        df = pd.DataFrame(ranked_companies)
        
        # Color coding
        def color_project_type(val):
            if val == 'Greenfield':
                return 'background-color: #90EE90; color: black;'
            elif val == 'Brownfield':
                return 'background-color: #FFB6C1; color: black;'
            return ''
        
        def color_confidence(val):
            if val == 'high':
                return 'color: green; font-weight: bold'
            elif val == 'medium':
                return 'color: orange'
            else:
                return 'color: red'
        
        styled_df = df.style.map(color_confidence, subset=['Confidence'])\
                          .map(color_project_type, subset=['Project Type'])
        
        st.dataframe(
            styled_df,
            column_config={
                "Source Link": st.column_config.LinkColumn("Source Link"),
                "Relevance Score": st.column_config.ProgressColumn(
                    "Relevance",
                    help="How relevant this company is to your search",
                    format="%f",
                    min_value=0,
                    max_value=10,
                )
            },
            use_container_width=True,
            hide_index=True
        )
        
        # TSV Output
        st.subheader(" TSV Output - Copy Ready")
        tsv_output = scout.generate_tsv_output(ranked_companies)
        st.code(tsv_output, language='text')
        
        # Download button
        st.download_button(
            label=" Download Complete TSV",
            data=tsv_output,
            file_name=f"hybrid_companies_{datetime.now().strftime('%Y%m%d_%H%M')}.tsv",
            mime="text/tab-separated-values",
            use_container_width=True
        )
        
        # Business insights
        if ranked_companies:
            st.header("🎯 Business Insights for WiFi Sales")
            
            top_greenfield = [c for c in ranked_companies if c['Project Type'] == 'Greenfield'][:3]
            top_brownfield = [c for c in ranked_companies if c['Project Type'] == 'Brownfield'][:3]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(" Top Greenfield Prospects")
                for i, company in enumerate(top_greenfield):
                    st.write(f"**{i+1}. {company['Company Name']}**")
                    st.write(f"*Project:* {company['Core Intent']}")
                    st.write(f"*Sector:* {company['Sector']}")
                    st.write(f"*Stage:* {company['Stage']}")
                    st.write("---")
            
            with col2:
                st.subheader(" Top Brownfield Prospects")
                for i, company in enumerate(top_brownfield):
                    st.write(f"**{i+1}. {company['Company Name']}**")
                    st.write(f"*Project:* {company['Core Intent']}")
                    st.write(f"*Sector:* {company['Sector']}")
                    st.write(f"*Stage:* {company['Stage']}")
                    st.write("---")

    else:
        # Instructions
        st.markdown("""
       
        """)

if __name__ == "__main__":
    main()
