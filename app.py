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

# Page configuration
st.set_page_config(
    page_title=" AI Company Scout ",
    page_icon="",
    layout="wide"
)

class FreeCompanyScout:
    def __init__(self):
        self.groq_client = Groq(api_key=st.secrets.get("GROQ_API_KEY"))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_google_news_rss(self, query, max_results=20):
        """Free Google News RSS search"""
        try:
            base_url = "https://news.google.com/rss"
            search_url = f"{base_url}/search?q={query.replace(' ', '%20')}&hl=en-IN&gl=IN&ceid=IN:en"
            
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

    def search_indian_business_sites(self):
        """Search multiple Indian business news sites"""
        all_articles = []
        
        # Search queries for different sites
        search_terms = [
            "construction completion India",
            "inauguration new building India", 
            "project completion timeline India",
            "new factory opening India",
            "commercial complex inauguration",
            "infrastructure project completion"
        ]
        
        for term in search_terms:
            articles = self.search_google_news_rss(term, 10)
            all_articles.extend(articles)
            time.sleep(1)  # Be respectful
            
        return all_articles

    def extract_companies_from_articles(self, articles):
        """Use Groq to intelligently extract company information"""
        if not articles:
            return []
            
        extracted_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, article in enumerate(articles):
            try:
                status_text.text(f" Analyzing article {i+1}/{len(articles)}...")
                progress_bar.progress((i + 1) / len(articles))
                
                content = article['content']
                if len(content) > 3000:
                    content = content[:3000]
                
                system_prompt = """You are an expert Indian business analyst. Extract ALL companies mentioned in news articles about construction, inaugurations, or project completions in India.

                IMPORTANT: Extract ANY company doing construction, infrastructure, building projects in India.
                Look for companies with projects that are:
                - Completing soon (any timeline)
                - Recently inaugurated  
                - In construction phase
                - Planning new buildings/factories/complexes

                Return JSON format:
                {
                    "companies": [
                        {
                            "company_name": "extracted company name",
                            "core_intent": "what they are building/doing",
                            "stage": "completion stage/timeline if mentioned, else 'Under Construction'",
                            "confidence": "high/medium/low based on how clear the info is"
                        }
                    ]
                }

                If no companies found, return: {"companies": []}"""
                
                user_prompt = f"""
                Analyze this Indian business/construction news article and extract ALL companies involved in construction, infrastructure, or building projects:

                TITLE: {article['title']}
                CONTENT: {content}

                Extract every company mentioned that is involved in construction, infrastructure, buildings, factories, or projects in India.
                """
                
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model="mixtral-8x7b-32768",
                    temperature=0.1,
                    max_tokens=1000,
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
                                'Confidence': company.get('confidence', 'medium'),
                                'Article Title': article['title'],
                                'Source': article['source'],
                                'Date': article.get('date', 'Recent')
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
        
        # Score companies based on confidence and keywords
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
            
            # Intent keywords boost
            intent = company['Core Intent'].lower()
            project_keywords = ['construction', 'building', 'project', 'factory', 'complex', 'infrastructure']
            if any(keyword in intent for keyword in project_keywords):
                score += 1
            
            company['Relevance Score'] = score
        
        # Sort by relevance and remove duplicates
        companies.sort(key=lambda x: x['Relevance Score'], reverse=True)
        
        # Remove duplicates based on company name
        seen_companies = set()
        unique_companies = []
        for company in companies:
            company_key = company['Company Name'].lower().strip()
            if company_key not in seen_companies:
                seen_companies.add(company_key)
                unique_companies.append(company)
        
        return unique_companies

    def generate_tsv_output(self, companies):
        """Generate TSV output"""
        if not companies:
            return "No companies found"
        
        tsv_lines = ["Company Name\tSource Link\tCore Intent\tStage\tConfidence"]
        for company in companies:
            company_name = str(company['Company Name']).replace('\t', ' ').replace('\n', ' ')
            source_link = str(company['Source Link']).replace('\t', ' ')
            core_intent = str(company['Core Intent']).replace('\t', ' ').replace('\n', ' ')
            stage = str(company['Stage']).replace('\t', ' ').replace('\n', ' ')
            confidence = str(company['Confidence']).replace('\t', ' ')
            tsv_line = f"{company_name}\t{source_link}\t{core_intent}\t{stage}\t{confidence}"
            tsv_lines.append(tsv_line)
        
        return "\n".join(tsv_lines)

def main():
    st.title(" AI Company Scout ")
    st.markdown("### Automatically finds Indian companies with construction projects & inaugurations")
    
    if not st.secrets.get("GROQ_API_KEY"):
        st.error(" Groq API key required (free at https://console.groq.com)")
        st.info("""
        
        """)
        return
    
    scout = FreeCompanyScout()
    
    with st.sidebar:
        st.header("⚙️ Search Settings")
        
        st.subheader("Search Scope")
        search_types = st.multiselect(
            "Project Types to Find:",
            ["Construction Completions", "New Inaugurations", "Factory Openings", 
             "Infrastructure Projects", "Commercial Buildings", "Residential Complexes"],
            default=["Construction Completions", "New Inaugurations"]
        )
        
        st.subheader("Results Settings")
        max_articles = st.slider("Articles to Analyze", 10, 50, 25)
        
        st.info("""
        **This AI Agent:**
        - Searches real-time Indian business news
        - Automatically extracts company names
        - Identifies construction/inauguration projects
        - Provides source links for verification
        - Completely FREE to use
        """)
    
    st.header("Start Company Discovery")
    
    if st.button(" Find Companies Automatically", type="primary", use_container_width=True):
        with st.spinner(" Searching Indian business news..."):
            # Search for relevant articles
            articles = scout.search_indian_business_sites()
            
            if not articles:
                st.error("""
                 No articles found. Possible issues:
                - Internet connection problem
                - Google News temporarily unavailable
                - Try again in a few minutes
                """)
                return
            
            st.success(f"📰 Found {len(articles)} recent articles about Indian construction/business")
            
            # Show sample of found articles
            with st.expander(" View Raw Articles Found"):
                for i, article in enumerate(articles[:5]):
                    st.write(f"**{i+1}. {article['title']}**")
                    st.write(f"Source: {article['source']}")
                    st.write(f"Link: {article['link']}")
                    st.write("---")
        
        with st.spinner("🤖 AI analyzing articles for companies..."):
            # Extract companies using AI
            companies_data = scout.extract_companies_from_articles(articles[:max_articles])
            
            if not companies_data:
                st.error("""
                 No companies extracted. This could mean:
                - Articles don't contain specific company names
                - News is too generic
                - Try different search terms
                """)
                return
            
            # Filter and rank companies
            ranked_companies = scout.filter_and_rank_companies(companies_data)
            
            st.success(f" Found {len(ranked_companies)} unique companies with construction projects!")
        
        # Display results
        st.header("Discovered Companies")
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Articles Analyzed", len(articles[:max_articles]))
        with col2:
            st.metric("Companies Found", len(ranked_companies))
        with col3:
            high_confidence = sum(1 for c in ranked_companies if c['Confidence'] == 'high')
            st.metric("High Confidence", high_confidence)
        with col4:
            success_rate = (len(ranked_companies) / len(articles[:max_articles])) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Company details table
        st.subheader("Company Details")
        df = pd.DataFrame(ranked_companies)
        
        # Color code confidence levels
        def color_confidence(val):
            if val == 'high':
                return 'color: green; font-weight: bold'
            elif val == 'medium':
                return 'color: orange'
            else:
                return 'color: red'
        
        styled_df = df.style.map(color_confidence, subset=['Confidence'])
        
        st.dataframe(
            styled_df,
            column_config={
                "Source Link": st.column_config.LinkColumn("Source Link"),
                "Relevance Score": st.column_config.ProgressColumn(
                    "Relevance",
                    help="How relevant this company is to your search",
                    format="%f",
                    min_value=0,
                    max_value=5,
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
            label="💾 Download TSV File",
            data=tsv_output,
            file_name=f"discovered_companies_{datetime.now().strftime('%Y%m%d_%H%M')}.tsv",
            mime="text/tab-separated-values",
            use_container_width=True
        )
        
        # Action steps
        st.header(" Next Steps for Your WiFi Business")
        
        if ranked_companies:
            st.info(f"""
            **You found {len(ranked_companies)} potential customers! Here's what to do next:**
            
            1. **Prioritize Outreach**: Start with {ranked_companies[0]['Company Name']} (highest relevance)
            2. **Research Each Company**: Visit their websites using the source links
            3. **Find Contact Info**: Look for Facilities Manager, IT Head, or Project Manager
            4. **Customize Your Pitch**: Mention their specific project: *"{ranked_companies[0]['Core Intent']}"*
            5. **Reach Out**: Contact them about your WiFi solutions for their new construction
            
            **Sample Outreach Message:**
            *"I saw your upcoming {ranked_companies[0]['Core Intent']} and thought our enterprise WiFi kits would be perfect for ensuring robust connectivity in your new facility..."*
            """)
        
        # Raw data for transparency
        with st.expander("Raw Data for Verification"):
            st.json(ranked_companies[:])  # Show first 3 as sample

    else:
        # Instructions
        st.markdown("""
        
        """)

if __name__ == "__main__":
    main()
