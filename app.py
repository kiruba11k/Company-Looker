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
import feedparser

# Page configuration
st.set_page_config(
    page_title=" AI Company Scout",
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
            "mall", "multiplex", "theatre", "hospital",
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
        
        # Additional press release and news sites
        self.NEWS_SOURCES = {
            'Google News': self.search_google_news_rss,
            'DuckDuckGo': self.search_duckduckgo_news,
            'Bing News': self.search_bing_news,
            'Yahoo News': self.search_yahoo_news,
            'Reuters RSS': self.search_reuters_rss,
            'PR Newswire': self.search_pr_newswire,
            'Business Wire': self.search_business_wire,
            'Indian Business News': self.search_indian_business_news
        }
    
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

    def search_bing_news(self, query, max_results=15):
        """Bing News search"""
        try:
            base_url = "https://www.bing.com/news/search"
            params = {
                'q': f"{query} India",
                'qft': 'sortbydate="1"',  # Sort by date
                'form': 'YFNR'
            }
            
            response = self.session.get(base_url, params=params, timeout=15)
            articles = []
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                news_cards = soup.find_all('div', class_='news-card')
                
                for card in news_cards[:max_results]:
                    try:
                        title_elem = card.find('a', class_='title')
                        description_elem = card.find('div', class_='snippet')
                        source_elem = card.find('div', class_='source')
                        time_elem = card.find('span', class_='time')
                        
                        if title_elem:
                            title = title_elem.text.strip()
                            link = title_elem.get('href')
                            description = description_elem.text.strip() if description_elem else ""
                            source = source_elem.text.strip() if source_elem else "Bing News"
                            date = time_elem.text.strip() if time_elem else "2024+"
                            
                            articles.append({
                                'title': title,
                                'link': link,
                                'description': description,
                                'source': source,
                                'date': date,
                                'content': f"{title}. {description}"
                            })
                    except Exception:
                        continue
                
                return articles
            return []
        except Exception as e:
            st.warning(f"Bing News search limited: {str(e)}")
            return []

    def search_yahoo_news(self, query, max_results=10):
        """Yahoo News search"""
        try:
            base_url = "https://news.search.yahoo.com/search"
            params = {
                'p': f"{query} India",
                'fr': 'uh3_news_web_gs',
                'fr2': 'p:news,m:news'
            }
            
            response = self.session.get(base_url, params=params, timeout=15)
            articles = []
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                results = soup.find_all('div', class_='NewsArticle')
                
                for result in results[:max_results]:
                    try:
                        title_elem = result.find('h4').find('a') if result.find('h4') else None
                        if title_elem:
                            title = title_elem.text.strip()
                            link = title_elem.get('href')
                            description_elem = result.find('p', class_='s-desc')
                            description = description_elem.text.strip() if description_elem else ""
                            
                            articles.append({
                                'title': title,
                                'link': link,
                                'description': description,
                                'source': 'Yahoo News',
                                'date': '2024+',
                                'content': f"{title}. {description}"
                            })
                    except Exception:
                        continue
                
                return articles
            return []
        except Exception as e:
            st.warning(f"Yahoo News search limited: {str(e)}")
            return []

    def search_reuters_rss(self, query, max_results=10):
        """Reuters RSS feed search"""
        try:
            # Reuters business news RSS
            rss_url = "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"
            feed = feedparser.parse(rss_url)
            
            articles = []
            for entry in feed.entries[:max_results]:
                # Check if query terms are in title or summary
                if any(term.lower() in (entry.title + ' ' + entry.summary).lower() for term in query.split()):
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'description': entry.summary,
                        'source': 'Reuters',
                        'date': entry.published if hasattr(entry, 'published') else '2024+',
                        'content': f"{entry.title}. {entry.summary}"
                    })
            
            return articles
        except Exception as e:
            st.warning(f"Reuters RSS search limited: {str(e)}")
            return []

    def search_pr_newswire(self, query, max_results=10):
        """PR Newswire style search"""
        try:
            # Using Google search for PR Newswire content
            base_url = "https://www.google.com/search"
            params = {
                'q': f"{query} site:prnewswire.com OR site:prnewswire.co.in",
                'tbm': 'nws',
                'tbs': 'qdr:y'  # Past year
            }
            
            response = self.session.get(base_url, params=params, timeout=15)
            articles = []
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                results = soup.find_all('div', class_='SoaBEf')
                
                for result in results[:max_results]:
                    try:
                        title_elem = result.find('div', role='heading')
                        link_elem = result.find('a')
                        description_elem = result.find('div', class_='Y3v8qd')
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem.get('href')
                            description = description_elem.text.strip() if description_elem else ""
                            
                            articles.append({
                                'title': title,
                                'link': link,
                                'description': description,
                                'source': 'PR Newswire',
                                'date': '2024+',
                                'content': f"{title}. {description}"
                            })
                    except Exception:
                        continue
                
                return articles
            return []
        except Exception as e:
            st.warning(f"PR Newswire search limited: {str(e)}")
            return []

    def search_business_wire(self, query, max_results=10):
        """Business Wire style search"""
        try:
            base_url = "https://www.google.com/search"
            params = {
                'q': f"{query} site:businesswire.com OR site:businesswireindia.com",
                'tbm': 'nws',
                'tbs': 'qdr:y'
            }
            
            response = self.session.get(base_url, params=params, timeout=15)
            articles = []
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                results = soup.find_all('div', class_='SoaBEf')
                
                for result in results[:max_results]:
                    try:
                        title_elem = result.find('div', role='heading')
                        link_elem = result.find('a')
                        description_elem = result.find('div', class_='Y3v8qd')
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem.get('href')
                            description = description_elem.text.strip() if description_elem else ""
                            
                            articles.append({
                                'title': title,
                                'link': link,
                                'description': description,
                                'source': 'Business Wire',
                                'date': '2024+',
                                'content': f"{title}. {description}"
                            })
                    except Exception:
                        continue
                
                return articles
            return []
        except Exception as e:
            st.warning(f"Business Wire search limited: {str(e)}")
            return []

    def search_indian_business_news(self, query, max_results=15):
        """Search Indian business news sources"""
        try:
            # Target Indian business publications
            indian_sources = [
                "thehindubusinessline.com",
                "economictimes.indiatimes.com",
                "business-standard.com",
                "moneycontrol.com",
                "livemint.com"
            ]
            
            source_query = " OR ".join([f"site:{source}" for source in indian_sources])
            full_query = f"{query} ({source_query})"
            
            base_url = "https://www.google.com/search"
            params = {
                'q': full_query,
                'tbm': 'nws',
                'tbs': 'qdr:y'
            }
            
            response = self.session.get(base_url, params=params, timeout=15)
            articles = []
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                results = soup.find_all('div', class_='SoaBEf')
                
                for result in results[:max_results]:
                    try:
                        title_elem = result.find('div', role='heading')
                        link_elem = result.find('a')
                        description_elem = result.find('div', class_='Y3v8qd')
                        source_elem = result.find('span', class_='r0bn4c')
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem.get('href')
                            description = description_elem.text.strip() if description_elem else ""
                            source = source_elem.text.strip() if source_elem else "Indian Business"
                            
                            articles.append({
                                'title': title,
                                'link': link,
                                'description': description,
                                'source': source,
                                'date': '2024+',
                                'content': f"{title}. {description}"
                            })
                    except Exception:
                        continue
                
                return articles
            return []
        except Exception as e:
            st.warning(f"Indian business news search limited: {str(e)}")
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

    def hybrid_search(self, search_terms, max_results_per_source=15, selected_sources=None):
        """Hybrid search across multiple free sources"""
        if selected_sources is None:
            selected_sources = list(self.NEWS_SOURCES.keys())
        
        all_articles = []
        
        for term in search_terms:
            for source_name in selected_sources:
                if source_name in self.NEWS_SOURCES:
                    try:
                        st.info(f" Searching {source_name} for: {term}")
                        articles = self.NEWS_SOURCES[source_name](term, max_results_per_source)
                        all_articles.extend(articles)
                        time.sleep(1)  # Rate limiting
                    except Exception as e:
                        st.warning(f"Error searching {source_name}: {str(e)}")
                        continue
        
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

    def display_found_articles(self, articles):
        """Display all found articles in an organized way"""
        if not articles:
            st.warning("No articles found to display")
            return
        
        st.header(" All Found Articles")
        st.info(f"Total articles found: {len(articles)}")
        
        # Create a DataFrame for better display
        articles_df = pd.DataFrame(articles)
        
        # Display articles in an expandable table
        with st.expander(" View All Articles Details", expanded=True):
            # Show summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Articles", len(articles))
            with col2:
                sources = articles_df['source'].value_counts()
                st.metric("Sources", len(sources))
            with col3:
                st.metric("Date Range", "Jan 2024 - Present")
            
            # Display sources breakdown
            st.subheader(" Sources Breakdown")
            source_counts = articles_df['source'].value_counts()
            st.bar_chart(source_counts)
            
            # Display articles in a detailed table
            st.subheader(" Article Details")
            
            # Create a formatted table with clickable links
            display_df = articles_df[['title', 'source', 'date', 'link']].copy()
            display_df['Article'] = display_df.apply(
                lambda x: f'<a href="{x["link"]}" target="_blank">{x["title"][:80]}...</a>', 
                axis=1
            )
            
            # Use HTML to display clickable links
            st.markdown(
                display_df[['Article', 'source', 'date']].to_html(escape=False, index=False), 
                unsafe_allow_html=True
            )
            
            # Also show raw data for debugging
            with st.expander(" Raw Article Data (for debugging)"):
                st.dataframe(articles_df[['title', 'source', 'date', 'link']], use_container_width=True)

    def extract_companies_with_enhanced_groq(self, articles, start_index=0, end_index=None):
        """Use Groq with enhanced prompts for better extraction including timeline details"""
        if not articles:
            return []
            
        if end_index is None:
            end_index = len(articles)
            
        articles_to_analyze = articles[start_index:end_index]
        
        if not articles_to_analyze:
            st.warning("No articles in the selected range to analyze")
            return []
            
        extracted_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Enhanced system prompt with timeline extraction
        system_prompt = f"""You are an expert Indian business analyst. Extract companies from news articles with focus on private sector projects.

SECTORS TO IDENTIFY: {', '.join(self.SECTORS)}

LEAD SIGNALS TO LOOK FOR: {', '.join(self.LEAD_SIGNALS)}

PROJECT TYPES:
- GREENFIELD: New construction, new facilities, completely new projects
- BROWNFIELD: Expansion, capacity increase, modernization of existing facilities

TIMELINE EXTRACTION: Extract specific timeline information including:
- Months (e.g., "June 2024", "Q3 2024", "by December 2024")
- Years (e.g., "2024", "2025", "next year")
- Specific dates (e.g., "15th August 2024")
- Relative timelines (e.g., "in 6 months", "within next quarter")
- If no specific timeline, estimate based on project stage

CRITICAL: Extract companies only from PRIVATE SECTOR. Avoid government projects unless specifically private partnerships.

Return EXACT JSON format:
{{
    "companies": [
        {{
            "company_name": "extracted company name",
            "core_intent": "specific project description",
            "stage": "current stage with timeline if mentioned",
            "detailed_timeline": "specific timeline details with months/years when available",
            "project_type": "Greenfield/Brownfield",
            "sector": "match to provided sectors list",
            "confidence": "high/medium/low",
            "is_private_sector": true/false
        }}
    ]
}}

If no private sector companies found, return: {{"companies": []}}"""
        
        processed_count = 0
        for i, article in enumerate(articles_to_analyze):
            try:
                status_text.text(f" Analyzing article {start_index + i + 1}/{end_index}...")
                progress_bar.progress((i + 1) / len(articles_to_analyze))
                
                content = article['content']
                if len(content) > 2500:  # Slightly reduced for better token usage
                    content = content[:2500]
                
                user_prompt = f"""
                Analyze this Indian business news article for PRIVATE SECTOR companies with construction/expansion projects:

                TITLE: {article['title']}
                CONTENT: {content}

                Extract ALL private sector companies. Focus on companies in: {', '.join(self.SECTORS)}.
                Look for signals like: {', '.join(self.LEAD_SIGNALS[:5])}.
                PAY SPECIAL ATTENTION TO TIMELINE INFORMATION: Extract months, years, quarters, specific dates when mentioned.
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
                            model="llama-3.3-70b-versatile",
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
                                'Detailed Timeline': company.get('detailed_timeline', 'Timeline not specified'),
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
                    st.warning(f"Failed to parse JSON from article {start_index + i + 1}: {str(e)}")
                    continue
                    
            except Exception as e:
                st.warning(f"Error processing article {start_index + i + 1}: {str(e)}")
                continue
        
        progress_bar.empty()
        status_text.empty()
        
        if processed_count > 0:
            st.success(f" Successfully processed {processed_count} company entries from articles {start_index + 1} to {end_index}")
        
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
            
            # Timeline scoring - higher score for specific timelines
            timeline = company.get('Detailed Timeline', '').lower()
            if any(time_indicator in timeline for time_indicator in ['2024', '2025', 'q1', 'q2', 'q3', 'q4', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']):
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
        """Generate TSV output with all enhanced fields including timeline"""
        if not companies:
            return "No private sector companies found"
        
        tsv_lines = ["Company Name\tSource Link\tCore Intent\tStage\tDetailed Timeline\tProject Type\tSector\tConfidence\tPrivate Sector"]
        for company in companies:
            company_name = str(company['Company Name']).replace('\t', ' ').replace('\n', ' ')
            source_link = str(company['Source Link']).replace('\t', ' ')
            core_intent = str(company['Core Intent']).replace('\t', ' ').replace('\n', ' ')
            stage = str(company['Stage']).replace('\t', ' ').replace('\n', ' ')
            detailed_timeline = str(company.get('Detailed Timeline', '')).replace('\t', ' ').replace('\n', ' ')
            project_type = str(company['Project Type']).replace('\t', ' ')
            sector = str(company['Sector']).replace('\t', ' ')
            confidence = str(company['Confidence']).replace('\t', ' ')
            private_sector = str(company.get('Private Sector', True))
            
            tsv_line = f"{company_name}\t{source_link}\t{core_intent}\t{stage}\t{detailed_timeline}\t{project_type}\t{sector}\t{confidence}\t{private_sector}"
            tsv_lines.append(tsv_line)
        
        return "\n".join(tsv_lines)

def main():
    st.title(" AI Company Scout ")
    
    # Initialize session state
    if 'articles' not in st.session_state:
        st.session_state.articles = None
    if 'search_complete' not in st.session_state:
        st.session_state.search_complete = False
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'ranked_companies' not in st.session_state:
        st.session_state.ranked_companies = None
    
    if not st.secrets.get("GROQ_API_KEY"):
        st.error("Groq API key required (free at https://console.groq.com)")
        st.info("""
        **Get free API key:**
        1. Go to https://console.groq.com
        2. Sign up for free account  
        3. Get your API key
        4. Add to Streamlit secrets: `GROQ_API_KEY = "your_key"`
        """)
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
        
        st.subheader("News Sources")
        selected_sources = st.multiselect(
            "Select News Sources:",
            list(scout.NEWS_SOURCES.keys()),
            default=list(scout.NEWS_SOURCES.keys())[:4]  # Default to first 4 sources
        )
        
        st.subheader("Search Settings")
        max_per_source = st.slider("Results per Search", 5, 20, 10)
        
        st.info("""
        **Enhanced Features:**
        - 8+ news sources including press release sites
        - Range-based article analysis
        - Detailed timeline extraction (months/years)
        - 40+ private sector categories
        - 25+ lead signal detection
        - Date range: Jan 2024 onwards
        - Private sector focus only
        - Multi-source hybrid search
        """)
    
    st.header(" Company Discovery")
    
    # Search section
    if not st.session_state.search_complete:
        if st.button(" Start Comprehensive Search", type="primary", use_container_width=True):
            if not selected_sectors:
                st.error(" Please select at least one sector")
                return
                
            if not project_types:
                st.error("Please select at least one project type")
                return
            
            if not selected_sources:
                st.error("Please select at least one news source")
                return
            
            # Generate targeted search queries
            search_queries = scout.get_search_queries(selected_sectors, project_types)
            
            st.info(f" Using {len(search_queries)} targeted queries across {len(selected_sectors)} sectors and {len(selected_sources)} sources")
            
            with st.spinner(" Comprehensive multi-source search in progress..."):
                # Perform hybrid search
                articles = scout.hybrid_search(search_queries, max_per_source, selected_sources)
                
                if not articles:
                    st.error("""
                     No articles found. Possible issues:
                    - Internet connectivity
                    - Search engines temporarily unavailable
                    - Try different sectors or reduce query complexity
                    """)
                    return
                
                # Store articles in session state
                st.session_state.articles = articles
                st.session_state.search_complete = True
                
                st.success(f" Found {len(articles)} articles from {len(selected_sources)} sources")
                
                # Display ALL found articles before AI analysis
                scout.display_found_articles(articles)
                
                # Show search summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    source_counts = pd.DataFrame(articles)['source'].value_counts()
                    st.metric("Total Sources", len(source_counts))
                with col2:
                    st.metric("Total Articles", len(articles))
                with col3:
                    st.metric("Date Range", "Jan 2024+")
            
            # Rerun to show the analysis section
            st.rerun()
    
    # Show analysis section if search is complete
    if st.session_state.search_complete and st.session_state.articles is not None:
        # Add a separator before AI analysis
        st.markdown("---")
        st.header("🤖 AI Analysis Phase")
        
        # Range selection for article analysis
        st.subheader(" Article Analysis Range")
        total_articles = len(st.session_state.articles)
        
        col1, col2 = st.columns(2)
        with col1:
            start_index = st.number_input(
                "Start analysis from article:", 
                min_value=0, 
                max_value=total_articles-1, 
                value=0,
                help="Starting index of articles to analyze"
            )
        with col2:
            end_index = st.number_input(
                "End analysis at article:", 
                min_value=1, 
                max_value=total_articles, 
                value=min(50, total_articles),  # Default to 50 or total articles if less
                help="Ending index of articles to analyze (exclusive)"
            )
        
        if start_index >= end_index:
            st.error("Start index must be less than end index")
        else:
            articles_to_analyze = end_index - start_index
            st.info(f"Will analyze {articles_to_analyze} articles ({start_index + 1} to {end_index})")
            
            # Analysis button
            if st.button(" Start AI Analysis", type="primary", key="analyze"):
                with st.spinner(f" AI analyzing {articles_to_analyze} articles for private sector companies..."):
                    # Extract companies using enhanced Groq processing with range
                    companies_data = scout.extract_companies_with_enhanced_groq(
                        st.session_state.articles, 
                        start_index=start_index, 
                        end_index=end_index
                    )
                    
                    if not companies_data:
                        st.error("""
                         No private sector companies extracted. This could mean:
                        - Articles are about government projects
                        - News doesn't contain specific company information
                        - Try expanding sector selection
                        - Increase number of articles analyzed
                        """)
                    else:
                        # Filter and rank companies
                        ranked_companies = scout.filter_and_rank_companies(companies_data)
                        st.session_state.ranked_companies = ranked_companies
                        st.session_state.analysis_complete = True
                        
                        st.success(f" Found {len(ranked_companies)} private sector companies across {len(set(c['Sector'] for c in ranked_companies))} sectors!")
                        
                        # Rerun to show results
                        st.rerun()
    
    # Show results if analysis is complete
    if st.session_state.analysis_complete and st.session_state.ranked_companies is not None:
        # Display comprehensive results
        st.header(" Private Sector Discovery Results")
        
        ranked_companies = st.session_state.ranked_companies
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Articles Analyzed", articles_to_analyze)
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
        st.subheader(" Company Details (Private Sector Only)")
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
        
        def color_timeline(val):
            if any(time_indicator in str(val).lower() for time_indicator in ['2024', '2025', 'q1', 'q2', 'q3', 'q4']):
                return 'background-color: #ADD8E6; color: black; font-weight: bold;'
            return ''
        
        styled_df = df.style.map(color_confidence, subset=['Confidence'])\
                          .map(color_project_type, subset=['Project Type'])\
                          .map(color_sector, subset=['Sector'])\
                          .map(color_timeline, subset=['Detailed Timeline'])
        
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
                        st.write(f"**Timeline:** {company.get('Detailed Timeline', 'Not specified')}")
                    with col2:
                        st.write(f"**Confidence:** {company['Confidence']}")
                        st.write(f"**Relevance Score:** {company['Relevance Score']}/10")
                        st.write(f"**Source:** [View Article]({company['Source Link']})")
                    
                    # WiFi sales insight
                    st.info(f"**WiFi Opportunity:** {company['Company Name']} is perfect for your {company['Project Type'].lower()} WiFi solutions in the {company['Sector']} sector. Timeline: {company.get('Detailed Timeline', 'To be determined')}")
        
        # Reset button
        if st.button(" Start New Search", type="secondary"):
            st.session_state.articles = None
            st.session_state.search_complete = False
            st.session_state.analysis_complete = False
            st.session_state.ranked_companies = None
            st.rerun()

    else:
        # Enhanced instructions
        st.markdown("""

        """)

if __name__ == "__main__":
    main()
