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
    page_title=" AI Company Scout - Multi-Sector Edition",
    page_icon="",
    layout="wide"
)

class MultiSectorCompanyScout:
    def __init__(self):
        self.groq_client = Groq(api_key=st.secrets.get("GROQ_API_KEY"))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Comprehensive sector list
        self.SECTORS = [
            "airport", "port", "mall", "multiplex", "theatre", "hospital",
            "it park", "technology park", "industrial park", "logistics park",
            "warehouse", "data centre", "stadium", "corporate campus", "office tower", "coworking",
            "manufacturing", "factory", "production facility", "industrial unit",
            "hotel", "resort", "hospitality", "restaurant", "food court",
            "university", "college", "educational campus", "school",
            "retail", "showroom", "automobile showroom", "consumer retail",
            "pharmaceutical", "healthcare", "medical center", "clinic",
            "bank", "financial center", "insurance", "financial services",
            "research center", "laboratory", "r&d facility"
        ]
        
        # Lead signals for targeted search
        self.LEAD_SIGNALS = [
            "inauguration", "opening soon", "opening", "to be operational", "commissioned",
            "near completion", "nearing completion", "construction to complete", "completion",
            "greenfield", "brownfield", "expansion", "expanding", "capacity expansion",
            "coming soon", "launch", "launching", "opening this month", "opening this week",
            "scheduled to open", "scheduled to be inaugurated", "will open",
            "under construction", "construction began", "breaking ground",
            "groundbreaking", "foundation stone", "foundation laid",
            "investment approved", "project approved", "clearance obtained",
            "tender", "bidding", "contract awarded", "construction contract"
        ]
    
    def search_google_news_rss(self, query, max_results=20):
        """Free Google News RSS search"""
        try:
            base_url = "https://news.google.com/rss"
            
            # Add date filtering (from Jan 2024)
            dated_query = f"{query} after:2024-01-01"
            
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

    def search_duckduckgo_news(self, query, max_results=15):
        """DuckDuckGo search with comprehensive query building"""
        try:
            # Build enhanced query with lead signals
            enhanced_query = self.build_enhanced_query(query)
            
            base_url = "https://html.duckduckgo.com/html/"
            params = {
                'q': enhanced_query,
                'kl': 'in-en',
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
                            if link and any(domain in link for domain in ['.com', '.in', '.org', '.net', '.co']):
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

    def build_enhanced_query(self, base_query):
        """Build enhanced search queries with lead signals"""
        # Combine base query with lead signals for better targeting
        lead_queries = []
        
        # Add lead signals to base query
        for signal in self.LEAD_SIGNALS[:5]:  # Use top 5 signals to avoid query being too long
            lead_queries.append(f'"{base_query} {signal}"')
        
        # Also create sector-specific queries
        sector_queries = []
        for sector in self.SECTORS[:3]:  # Use top 3 sectors
            sector_queries.append(f'"{sector} {base_query}"')
        
        # Combine all queries
        all_queries = lead_queries + sector_queries
        
        # Use OR operator to combine queries
        final_query = " OR ".join(all_queries[:3])  # Limit to 3 combined queries
        
        return f"({final_query}) India after:2024-01-01"

    def hybrid_search(self, search_terms, max_results_per_source=15):
        """Hybrid search across multiple free sources"""
        all_articles = []
        
        for term in search_terms:
            st.info(f" Searching Google News for: {term}")
            google_articles = self.search_google_news_rss(term, max_results_per_source)
            all_articles.extend(google_articles)
            time.sleep(1)
            
            st.info(f" Searching DuckDuckGo for: {term}")
            ddg_articles = self.search_duckduckgo_news(term, max_results_per_source)
            all_articles.extend(ddg_articles)
            time.sleep(1)
        
        # Remove duplicates based on URL and title
        seen_articles = set()
        unique_articles = []
        for article in all_articles:
            article_key = f"{article['title'][:100]}_{article['link']}"
            if article_key not in seen_articles:
                seen_articles.add(article_key)
                unique_articles.append(article)
        
        return unique_articles

    def get_search_queries(self, selected_sectors, project_types):
        """Generate targeted search queries based on user selection"""
        base_queries = []
        
        # Generate queries for each selected sector
        for sector in selected_sectors:
            sector_lower = sector.lower()
            
            # Greenfield projects (new construction)
            if "Greenfield Projects" in project_types:
                base_queries.extend([
                    f"new {sector_lower} construction India",
                    f"new {sector_lower} project India",
                    f"{sector_lower} groundbreaking India",
                    f"{sector_lower} foundation stone India"
                ])
            
            # Brownfield projects (expansion)
            if "Brownfield Projects" in project_types:
                base_queries.extend([
                    f"{sector_lower} expansion India",
                    f"{sector_lower} capacity increase India",
                    f"{sector_lower} modernization India",
                    f"{sector_lower} renovation India"
                ])
        
        # Add lead signal enhanced queries
        enhanced_queries = []
        for base_query in base_queries:
            # Add a few key lead signals to each base query
            for signal in self.LEAD_SIGNALS[:3]:
                enhanced_queries.append(f"{base_query} {signal}")
        
        return list(set(enhanced_queries))[:20]  # Limit to 20 unique queries

    def extract_companies_with_enhanced_groq(self, articles):
        """Use Groq with enhanced prompts for better extraction"""
        if not articles:
            return []
            
        extracted_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Enhanced system prompt with sectors and lead signals
        system_prompt = f"""You are an expert Indian business analyst. Extract companies from news articles with focus on private sector projects.

SECTORS TO IDENTIFY: {', '.join(self.SECTORS)}

LEAD SIGNALS TO LOOK FOR: {', '.join(self.LEAD_SIGNALS)}

PROJECT TYPES:
- GREENFIELD: New construction, new facilities, completely new projects
- BROWNFIELD: Expansion, capacity increase, modernization of existing facilities

CRITICAL: Extract companies only from PRIVATE SECTOR. Avoid government projects unless specifically private partnerships.

Return EXACT JSON format:
{{
    "companies": [
        {{
            "company_name": "extracted company name",
            "core_intent": "specific project description",
            "stage": "current stage with timeline if mentioned",
            "project_type": "Greenfield/Brownfield",
            "sector": "match to provided sectors list",
            "confidence": "high/medium/low",
            "is_private_sector": true/false
        }}
    ]
}}

If no private sector companies found, return: {{"companies": []}}"""
        
        processed_count = 0
        for i, article in enumerate(articles):
            try:
                status_text.text(f" Analyzing article {i+1}/{len(articles)}...")
                progress_bar.progress((i + 1) / len(articles))
                
                content = article['content']
                if len(content) > 2500:  # Slightly reduced for better token usage
                    content = content[:2500]
                
                user_prompt = f"""
                Analyze this Indian business news article for PRIVATE SECTOR companies with construction/expansion projects:

                TITLE: {article['title']}
                CONTENT: {content}

                Extract ALL private sector companies. Focus on companies in: {', '.join(self.SECTORS)}.
                Look for signals like: {', '.join(self.LEAD_SIGNALS[:5])}.
                """
                
                # Use chat completion with retry logic
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        chat_completion = self.groq_client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            model="llama-3.1-70b-versatile",
                            temperature=0.1,
                            max_tokens=2000,  # Increased for comprehensive analysis
                            response_format={"type": "json_object"}
                        )
                        
                        response_text = chat_completion.choices[0].message.content
                        break
                        
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise e
                        time.sleep(1)  # Wait before retry
                
                # Parse and validate response
                try:
                    data = json.loads(response_text.strip())
                    companies = data.get('companies', [])
                    
                    for company in companies:
                        # Validate required fields
                        if (company.get('company_name') and 
                            company.get('company_name') != 'null' and
                            company.get('is_private_sector', False)):
                            
                            extracted_data.append({
                                'Company Name': company['company_name'],
                                'Source Link': article['link'],
                                'Core Intent': company.get('core_intent', 'Private Sector Project'),
                                'Stage': company.get('stage', 'Under Development'),
                                'Project Type': company.get('project_type', 'Unknown'),
                                'Sector': company.get('sector', 'Private Sector'),
                                'Confidence': company.get('confidence', 'medium'),
                                'Article Title': article['title'],
                                'Source': article['source'],
                                'Date': article.get('date', '2024+'),
                                'Private Sector': company.get('is_private_sector', True)
                            })
                            processed_count += 1
                            
                except json.JSONDecodeError as e:
                    st.warning(f"Failed to parse JSON from article {i+1}: {str(e)}")
                    continue
                    
            except Exception as e:
                st.warning(f"Error processing article {i+1}: {str(e)}")
                continue
        
        progress_bar.empty()
        status_text.empty()
        
        if processed_count > 0:
            st.success(f" Successfully processed {processed_count} company entries")
        
        return extracted_data

    def filter_and_rank_companies(self, companies):
        """Filter and rank companies by relevance with sector focus"""
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
            
            # Project type scoring
            if company['Project Type'] in ['Greenfield', 'Brownfield']:
                score += 2
            
            # Lead signal matching in stage
            stage = company['Stage'].lower()
            if any(signal in stage for signal in self.LEAD_SIGNALS):
                score += 2
            
            # Sector priority (higher scores for key sectors)
            sector = company['Sector'].lower()
            high_priority_sectors = ['manufacturing', 'warehouse', 'logistics park', 'data centre', 'industrial park']
            medium_priority_sectors = ['hospital', 'it park', 'corporate campus', 'office tower']
            
            if any(priority in sector for priority in high_priority_sectors):
                score += 3
            elif any(priority in sector for priority in medium_priority_sectors):
                score += 2
            else:
                score += 1
            
            # Private sector bonus
            if company.get('Private Sector', True):
                score += 1
            
            company['Relevance Score'] = score
        
        # Sort by relevance
        companies.sort(key=lambda x: x['Relevance Score'], reverse=True)
        
        # Remove duplicates based on company name + core intent
        seen_companies = set()
        unique_companies = []
        for company in companies:
            company_key = f"{company['Company Name'].lower().strip()}_{company['Core Intent'][:30]}"
            if company_key not in seen_companies:
                seen_companies.add(company_key)
                unique_companies.append(company)
        
        return unique_companies

    def generate_tsv_output(self, companies):
        """Generate TSV output with all enhanced fields"""
        if not companies:
            return "No private sector companies found"
        
        tsv_lines = ["Company Name\tSource Link\tCore Intent\tStage\tProject Type\tSector\tConfidence\tPrivate Sector"]
        for company in companies:
            company_name = str(company['Company Name']).replace('\t', ' ').replace('\n', ' ')
            source_link = str(company['Source Link']).replace('\t', ' ')
            core_intent = str(company['Core Intent']).replace('\t', ' ').replace('\n', ' ')
            stage = str(company['Stage']).replace('\t', ' ').replace('\n', ' ')
            project_type = str(company['Project Type']).replace('\t', ' ')
            sector = str(company['Sector']).replace('\t', ' ')
            confidence = str(company['Confidence']).replace('\t', ' ')
            private_sector = str(company.get('Private Sector', True))
            
            tsv_line = f"{company_name}\t{source_link}\t{core_intent}\t{stage}\t{project_type}\t{sector}\t{confidence}\t{private_sector}"
            tsv_lines.append(tsv_line)
        
        return "\n".join(tsv_lines)

def main():
    st.title(" AI Company Scout - Multi-Sector Private Edition")
    st.markdown("### Comprehensive Private Sector Project Discovery Across All Industries")
    
    if not st.secrets.get("GROQ_API_KEY"):
        st.error(" Groq API key required (free at https://console.groq.com)")

        return
    
    scout = MultiSectorCompanyScout()
    
    with st.sidebar:
        st.header(" Search Configuration")
        
        st.subheader("Project Types")
        project_types = st.multiselect(
            "Select Project Types:",
            ["Greenfield Projects", "Brownfield Projects"],
            default=["Greenfield Projects", "Brownfield Projects"]
        )
        
        st.subheader("Target Sectors")
        selected_sectors = st.multiselect(
            "Select Sectors (Private Sector Focus):",
            scout.SECTORS,
            default=["manufacturing", "warehouse", "hospital", "it park", "logistics park"]
        )
        
        st.subheader("Search Settings")
        max_articles = st.slider("Articles to Analyze", 10, 50, 25)
        max_per_source = st.slider("Results per Search", 5, 20, 10)
        
        st.info("""
        **Enhanced Features:**
        - 40+ private sector categories
        - 25+ lead signal detection
        - Date range: Jan 2024 onwards
        - Private sector focus only
        - Multi-source hybrid search
        """)
    
    st.header("Multi-Sector Private Company Discovery")
    
    if st.button(" Start Comprehensive Search", type="primary", use_container_width=True):
        if not selected_sectors:
            st.error(" Please select at least one sector")
            return
            
        if not project_types:
            st.error(" Please select at least one project type")
            return
        
        # Generate targeted search queries
        search_queries = scout.get_search_queries(selected_sectors, project_types)
        
        st.info(f" Using {len(search_queries)} targeted queries across {len(selected_sectors)} sectors")
        
        with st.spinner(" Comprehensive multi-source search in progress..."):
            # Perform hybrid search
            articles = scout.hybrid_search(search_queries, max_per_source)
            
            if not articles:
                st.error("""
                 No articles found. Possible issues:
                - Internet connectivity
                - Search engines temporarily unavailable
                - Try different sectors or reduce query complexity
                """)
                return
            
            st.success(f" Found {len(articles)} articles from multiple sources",articles[:])
            
            # Show search summary
            col1, col2 = st.columns(2)
            with col1:
                google_count = len([a for a in articles if a['source'] == 'Google News'])
                st.metric("Google News", google_count)
            with col2:
                ddg_count = len([a for a in articles if a['source'] == 'DuckDuckGo'])
                st.metric("DuckDuckGo", ddg_count)
        
        with st.spinner(" AI analyzing for private sector companies..."):
            # Extract companies using enhanced Groq processing
            companies_data = scout.extract_companies_with_enhanced_groq(articles[:max_articles])
            
            if not companies_data:
                st.error("""
                 No private sector companies extracted. This could mean:
                - Articles are about government projects
                - News doesn't contain specific company information
                - Try expanding sector selection
                - Increase number of articles analyzed
                """)
                return
            
            # Filter and rank companies
            ranked_companies = scout.filter_and_rank_companies(companies_data)
            
            st.success(f"Found {len(ranked_companies)} private sector companies across {len(set(c['Sector'] for c in ranked_companies))} sectors!")
        
        # Display comprehensive results
        st.header(" Private Sector Discovery Results")
        
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
            
            st.subheader("Sector Distribution")
            sector_df = pd.DataFrame(list(sectors_count.items()), columns=['Sector', 'Count'])
            st.bar_chart(sector_df.set_index('Sector'))
        
        # Company details table
        st.subheader("Company Details (Private Sector Only)")
        df = pd.DataFrame(ranked_companies)
        
        # Enhanced color coding
        def color_project_type(val):
            if val == 'Greenfield':
                return 'background-color: #90EE90; color: black; font-weight: bold;'
            elif val == 'Brownfield':
                return 'background-color: #FFB6C1; color: black; font-weight: bold;'
            return ''
        
        def color_confidence(val):
            if val == 'high':
                return 'color: green; font-weight: bold'
            elif val == 'medium':
                return 'color: orange'
            else:
                return 'color: red'
        
        def color_sector(val):
            priority_sectors = ['manufacturing', 'warehouse', 'data centre', 'logistics park']
            if any(priority in val.lower() for priority in priority_sectors):
                return 'background-color: #FFD700; color: black; font-weight: bold;'
            return ''
        
        styled_df = df.style.map(color_confidence, subset=['Confidence'])\
                          .map(color_project_type, subset=['Project Type'])\
                          .map(color_sector, subset=['Sector'])
        
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
            hide_index=True,
            height=600
        )
        
        # TSV Output
        st.subheader(" TSV Output - Copy Ready")
        tsv_output = scout.generate_tsv_output(ranked_companies)
        st.code(tsv_output, language='text')
        
        # Download button
        st.download_button(
            label=" Download Complete TSV",
            data=tsv_output,
            file_name=f"private_sector_companies_{datetime.now().strftime('%Y%m%d_%H%M')}.tsv",
            mime="text/tab-separated-values",
            use_container_width=True
        )
        
        # Business insights
        if ranked_companies:
            st.header(" Business Insights for WiFi Sales")
            
            # Top companies by relevance
            top_companies = ranked_companies[:5]
            
            st.subheader(" Top 5 Private Sector Prospects")
            for i, company in enumerate(top_companies):
                with st.expander(f"{i+1}. {company['Company Name']} - {company['Sector']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Project:** {company['Core Intent']}")
                        st.write(f"**Type:** {company['Project Type']}")
                        st.write(f"**Stage:** {company['Stage']}")
                    with col2:
                        st.write(f"**Confidence:** {company['Confidence']}")
                        st.write(f"**Relevance Score:** {company['Relevance Score']}/10")
                        st.write(f"**Source:** [View Article]({company['Source Link']})")
                    
                    # WiFi sales insight
                    st.info(f"**WiFi Opportunity:** {company['Company Name']} is perfect for your {company['Project Type'].lower()} WiFi solutions in the {company['Sector']} sector.")

    else:
        # Enhanced instructions
        st.markdown("""
   
        """)

if __name__ == "__main__":
    main()
