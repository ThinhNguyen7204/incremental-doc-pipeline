from markdownify import markdownify as md
from bs4 import BeautifulSoup
import re
import json
import os
from typing import List, Dict

class MarkdownConverter:
    """Convert HTML articles to clean Markdown format"""
    
    def __init__(self):
        self.base_url = "https://support.optisigns.com"
    
    def clean_html(self, html_content: str) -> str:
        """Remove unwanted HTML elements before conversion"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove common unwanted elements
        unwanted_tags = ['script', 'style', 'nav', 'footer', 'aside', 'iframe']
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements by class (common in help centers)
        unwanted_classes = ['social-share', 'advertisement', 'feedback', 'banner']
        for class_name in unwanted_classes:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):
                element.decompose()
        
        return str(soup)
    
    def html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to Markdown with clean formatting"""
        if not html_content:
            return ""
        
        # Clean HTML first
        clean_html = self.clean_html(html_content)
        
        # Convert to Markdown with proper settings
        markdown = md(
            clean_html,
            heading_style="ATX",           # Use ### style headers
            code_language="",               # Don't add language to code blocks
            bullets="-",                    # Use - for bullets
            strong_em_symbol="**",          # Use ** for bold
            strip=['script', 'style']       # Strip these tags
        )
        
        # Post-process the markdown
        markdown = self.post_process(markdown)
        
        return markdown
    
    def post_process(self, markdown: str) -> str:
        """Clean up and normalize the markdown"""
        # Remove excessive newlines (3+ → 2)
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Remove leading/trailing whitespace on each line
        lines = [line.rstrip() for line in markdown.split('\n')]
        markdown = '\n'.join(lines)
        
        # Ensure proper spacing around headers
        markdown = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', markdown)
        
        # Ensure proper spacing after headers
        markdown = re.sub(r'(#{1,6} .+)\n([^\n#])', r'\1\n\n\2', markdown)
        
        # Fix spacing around code blocks
        markdown = re.sub(r'([^\n])\n```', r'\1\n\n```', markdown)
        markdown = re.sub(r'```\n([^\n])', r'```\n\n\1', markdown)
        
        # Trim final whitespace
        markdown = markdown.strip()
        
        return markdown
    
    def generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title"""
        slug = title.lower()
        # Remove special characters
        slug = re.sub(r'[^\w\s-]', '', slug)
        # Replace spaces with hyphens
        slug = re.sub(r'[-\s]+', '-', slug)
        # Limit length
        slug = slug[:100]
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug
    
    def convert_article(self, article: Dict) -> Dict:
        """Convert a single article to markdown"""
        markdown_content = self.html_to_markdown(article['html_content'])
        
        # Add metadata header
        header = f"# {article['title']}\n\n"
        header += f"**Source**: {article['url']}\n"
        
        if article.get('updated_at'):
            header += f"**Updated**: {article['updated_at']}\n"
        
        if article.get('labels'):
            labels = ', '.join(article['labels'])
            header += f"**Labels**: {labels}\n"
        
        header += "\n---\n\n"
        
        full_content = header + markdown_content
        
        return {
            'slug': self.generate_slug(article['title']),
            'title': article['title'],
            'url': article['url'],
            'markdown': full_content,
            'original_id': article['id']
        }
    
    def convert_all(self, 
                   raw_articles_path='data/raw_articles.json', 
                   output_dir='data/articles') -> List[Dict]:
        """Convert all raw articles to Markdown files"""
        print("=" * 60)
        print("[*] Converting HTML to Markdown")
        print("=" * 60)
        
        # Load raw articles
        if not os.path.exists(raw_articles_path):
            print(f"[ERROR] Error: {raw_articles_path} not found!")
            print("   Run fetch_articles.py first to scrape articles.")
            return []
        
        with open(raw_articles_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        print(f"[+] Loaded {len(articles)} articles from {raw_articles_path}")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert each article
        converted = []
        for i, article in enumerate(articles, 1):
            try:
                print(f"[{i}/{len(articles)}] Converting: {article['title'][:50]}...")
                
                result = self.convert_article(article)
                
                # Save to file
                filename = f"{result['slug']}.md"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result['markdown'])
                
                converted.append({
                    'filename': filename,
                    'title': result['title'],
                    'url': result['url'],
                    'slug': result['slug']
                })
                
                print(f"   [OK] Saved to: {filename}")
                
            except Exception as e:
                print(f"   [ERROR] Error converting article: {e}")
                continue
        
        print("\n" + "=" * 60)
        print(f"[DONE] Conversion complete!")
        print(f"[INFO] Successfully converted: {len(converted)}/{len(articles)} articles")
        print(f"[INFO] Output directory: {output_dir}")
        print("=" * 60)
        
        return converted


def main():
    """Main execution"""
    converter = MarkdownConverter()
    converted = converter.convert_all()
    
    if converted:
        print(f"\n[OK] {len(converted)} articles ready for Gemini File API / local RAG")
        return 0
    else:
        print("\n[ERROR] Conversion failed")
        return 1


if __name__ == "__main__":
    exit(main())
