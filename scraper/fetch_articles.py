import requests
import json
import os
import time
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class ZendeskScraper:
    """Scraper for OptiSigns Zendesk Help Center using Zendesk API"""
    
    def __init__(self):
        self.subdomain = os.getenv('ZENDESK_SUBDOMAIN', 'optisigns')
        
        # Try custom domain first (support.optisigns.com)
        # If that fails, fall back to zendesk.com subdomain
        self.base_url = f"https://support.{self.subdomain}.com/api/v2/help_center"
        
        self.session = requests.Session()
        
        # Optional: Add authentication if credentials provided
        email = os.getenv('ZENDESK_EMAIL')
        token = os.getenv('ZENDESK_TOKEN')
        if email and token:
            self.session.auth = (f"{email}/token", token)
        
        self.session.headers.update({
            'User-Agent': 'OptiBot-Scraper/1.0',
            'Accept': 'application/json'
        })
    
    def get_all_articles(self, min_articles=30) -> List[Dict]:
        """Fetch all articles from Zendesk Help Center"""
        articles = []
        page = 1
        per_page = 100  # Max per page
        
        print(f"[*] Fetching articles from Zendesk API...")
        
        while len(articles) < min_articles:
            url = f"{self.base_url}/articles.json"
            params = {
                'page': page,
                'per_page': per_page,
                'sort_by': 'updated_at',
                'sort_order': 'desc'
            }
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                page_articles = data.get('articles', [])
                
                if not page_articles:
                    print(f"[!] No more articles found. Total: {len(articles)}")
                    break
                
                articles.extend(page_articles)
                print(f"[+] Page {page}: Found {len(page_articles)} articles (Total: {len(articles)})")
                
                # Check if there's a next page
                if not data.get('next_page'):
                    break
                
                page += 1
                time.sleep(0.5)  # Be polite to API
                
            except requests.RequestException as e:
                print(f"[ERROR] Error fetching page {page}: {e}")
                break
        
        return articles[:min_articles] if len(articles) > min_articles else articles
    
    def fetch_article_details(self, article_id: int) -> Dict:
        """Fetch detailed article content including body HTML"""
        url = f"{self.base_url}/articles/{article_id}.json"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()['article']
        except requests.RequestException as e:
            print(f"[ERROR] Error fetching article {article_id}: {e}")
            return None
    
    def scrape_all(self, min_articles=30) -> List[Dict]:
        """Main scraping method - fetch articles with full content"""
        print("=" * 60)
        print("OptiSigns Zendesk Scraper")
        print("=" * 60)
        
        # Get list of articles
        articles_list = self.get_all_articles(min_articles)
        
        if not articles_list:
            print("[ERROR] No articles found!")
            return []
        
        print(f"\n[*] Fetching full content for {len(articles_list)} articles...")
        
        detailed_articles = []
        for i, article in enumerate(articles_list, 1):
            article_id = article['id']
            print(f"[{i}/{len(articles_list)}] Fetching article {article_id}: {article['title'][:50]}...")
            
            # Fetch full article details
            detailed = self.fetch_article_details(article_id)
            
            if detailed:
                # Structure the data
                article_data = {
                    'id': detailed['id'],
                    'title': detailed['title'],
                    'url': detailed['html_url'],
                    'html_content': detailed['body'],
                    'author_id': detailed.get('author_id'),
                    'created_at': detailed.get('created_at'),
                    'updated_at': detailed.get('updated_at'),
                    'labels': detailed.get('label_names', []),
                    'section_id': detailed.get('section_id')
                }
                detailed_articles.append(article_data)
            
            time.sleep(0.3)  # Rate limiting
        
        print(f"\n[OK] Successfully scraped {len(detailed_articles)} articles")
        return detailed_articles
    
    def save_to_json(self, articles: List[Dict], filepath='data/raw_articles.json'):
        """Save scraped articles to JSON file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        print(f"[SAVED] Saved {len(articles)} articles to {filepath}")


def main():
    """Main execution"""
    scraper = ZendeskScraper()
    
    # Scrape articles
    articles = scraper.scrape_all(min_articles=100)
    
    if articles:
        # Save to JSON
        scraper.save_to_json(articles)
        
        print("\n" + "=" * 60)
        print(f"[DONE] Scraping complete!")
        print(f"[INFO] Total articles: {len(articles)}")
        print(f"[SAVED] Saved to: data/raw_articles.json")
        print("=" * 60)
    else:
        print("\n[ERROR] Scraping failed - no articles retrieved")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
