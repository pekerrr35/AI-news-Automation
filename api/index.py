import os
import feedparser
import google.generativeai as genai
from http.server import BaseHTTPRequestHandler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import re

# --- Enhanced Core Functions ---
def fetch_news_articles():
    """Optimized RSS fetching with parallel processing for sub-30 second execution"""
    import socket
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    start_time = time.time()
    
    # Fast and reliable RSS feeds (6 sources for better coverage)
    RSS_FEEDS = [
        "https://singularityhub.com/feed/",
        "https://longevity.technology/feed/",
        "https://www.artificialintelligence-news.com/feed/",
        "https://www.nocodereport.com/rss",
        "https://www.realt.co/feed/",
        "https://www.darkreading.com/rss.xml",
        "https://www.entrepreneur.com/topic/artificial-intelligence.rss",
        "https://www.nichepursuits.com/feed/",
        "https://decrypt.co/news/technology/rss",
        "https://venturebeat.com/category/ai/feed/"
    ]
    
    def fetch_single_feed(url):
        """Fetch articles from single RSS feed with aggressive timeout"""
        articles = []
        original_timeout = socket.getdefaulttimeout()
        
        try:
            socket.setdefaulttimeout(3)  # 3-second timeout per feed
            feed = feedparser.parse(url)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                return articles
                
            today = datetime.utcnow().date()
            two_days_ago = today - timedelta(days=2)
            
            # Process only first 6 entries per feed for speed
            for entry in feed.entries[:6]:
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        article_date = datetime(*entry.published_parsed[:6]).date()
                    except (TypeError, ValueError):
                        continue
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    try:
                        article_date = datetime(*entry.updated_parsed[:6]).date()
                    except (TypeError, ValueError):
                        continue
                
                if article_date and article_date >= two_days_ago:
                    articles.append({
                        'title': getattr(entry, 'title', 'No Title'),
                        'link': getattr(entry, 'link', ''),
                        'summary': getattr(entry, 'summary', '')[:300],
                        'date': article_date,
                        'source': extract_domain(url)
                    })
                    
        except Exception as e:
            print(f"Error fetching feed {url}: {e}")
        finally:
            socket.setdefaulttimeout(original_timeout)
            
        return articles
    
    all_articles = []
    
    # Parallel RSS fetching with 15-second total timeout for 6 feeds
    try:
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_url = {executor.submit(fetch_single_feed, url): url for url in RSS_FEEDS}
            
            for future in as_completed(future_to_url, timeout=15):
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Feed fetch exception: {e}")
                    
    except Exception as e:
        print(f"Parallel fetch timeout or error: {e}")
    
    # Quick deduplication
    unique_articles = remove_duplicates(all_articles)
    
    fetch_time = time.time() - start_time
    print(f"RSS fetch completed in {fetch_time:.2f}s with {len(unique_articles)} articles")
    
    return unique_articles[:18]  # Limit to 18 articles for processing (6 feeds × 3 articles avg)

def extract_domain(url):
    """Extract clean, readable domain name from URL for source attribution"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        # Clean up domain name
        domain = domain.replace('www.', '').replace('feeds.', '').replace('feed.', '')
        
        # Create more readable source names (updated for 6 feeds)
        source_mapping = {
            'technologyreview.com': 'MIT Technology Review',
            'venturebeat.com': 'VentureBeat',
            'marktechpost.com': 'MarkTechPost',
            'research.google': 'Google Research',
            'techcrunch.com': 'TechCrunch',
            'artificialintelligence-news.com': 'AI News',
            # Legacy mappings (in case feeds change)
            'feedburner.com': 'AI News',
            'wired.com': 'Wired',
            'ai-techpark.com': 'AI TechPark',
            'bair.berkeley.edu': 'Berkeley AI Research',
            '404media.co': '404 Media'
        }
        
        # Return mapped name if available, otherwise cleaned domain
        return source_mapping.get(domain, domain.capitalize())
        
    except:
        return "Unknown"

def remove_duplicates(articles):
    """Remove duplicate articles based on title similarity"""
    unique_articles = []
    seen_titles = set()
    
    for article in articles:
        # Create a normalized version of the title for comparison
        normalized_title = re.sub(r'[^a-zA-Z0-9\s]', '', article['title'].lower()).strip()
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            unique_articles.append(article)
    
    return unique_articles

def summarize_with_gemini(articles):
    """Optimized AI summarization for sub-120 second execution"""
    import time
    
    start_time = time.time()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not articles: 
        return []
    if not gemini_api_key: 
        return articles[:12]  # Return articles without AI summaries
    
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')  # Use Gemini 2.5 Flash for better quality
        
        # Process 10-12 articles for better coverage with 6 RSS feeds
        articles_to_process = articles[:12]
        summarized_articles = []
        
        print(f"Processing {len(articles_to_process)} articles with Gemini 2.5 Flash...")
        
        for i, article in enumerate(articles_to_process):
            try:
                # Balanced prompt for detailed but focused summaries
                prompt = f"""Sen dünyanın en iyi küratör ve stratejistisin. Aşağıdaki makaleyi şu 5 niş alandan biriyle ilişkilendirerek (Agentic AI, Longevity, No-Code, AI Security, Future Investing) profesyonel ve milyoner vizyonuyla Türkçe özetle:

Makale Başlığı: {article['title']}
İçerik: {article.get('summary', '')[:300]}

Özeti şu yapıda hazırla:
1. Hangi kategoriye giriyor? (Belirt)
2. Bu haber neden önemli? (1-2 cümle)
3. Milyoner vizyonuyla aksiyon adımı ne olmalı? (Kısa bir tavsiye)
Dili profesyonel ve etkileyici olsun."""
                
                response = model.generate_content(prompt)
                
                if response and response.text and response.text.strip():
                    ai_summary = response.text.strip()
                    if len(ai_summary) > 50:
                        enhanced_article = article.copy()
                        enhanced_article['ai_summary'] = ai_summary
                        summarized_articles.append(enhanced_article)
                        print(f"✅ {i+1}/12: {article['title'][:40]}...")
                        continue
                
                # Quick fallback
                enhanced_article = article.copy()
                enhanced_article['ai_summary'] = create_quick_fallback_summary(article)
                summarized_articles.append(enhanced_article)
                
            except Exception as e:
                print(f"Error summarizing article {i+1}: {e}")
                enhanced_article = article.copy()
                enhanced_article['ai_summary'] = create_quick_fallback_summary(article)
                summarized_articles.append(enhanced_article)
        
        ai_time = time.time() - start_time
        print(f"AI summarization completed in {ai_time:.2f}s for {len(summarized_articles)} articles")
        return summarized_articles
        
    except Exception as e:
        print(f"Gemini AI error: {e}")
        # Quick fallback articles
        fallback_articles = []
        for article in articles[:12]:
            enhanced_article = article.copy()
            enhanced_article['ai_summary'] = create_quick_fallback_summary(article)
            fallback_articles.append(enhanced_article)
        return fallback_articles

def create_quick_fallback_summary(article):
    """Create fast fallback summary for speed optimization"""
    title = article['title']
    original_summary = article.get('summary', '')
    source = article.get('source', 'Unknown Source')
    
    if original_summary and len(original_summary) > 50:
        # Use first 2 sentences of original summary
        sentences = original_summary.split('. ')[:2]
        summary_text = '. '.join(sentences) + '.'
        if len(summary_text) > 200:
            summary_text = summary_text[:200] + '...'
    else:
        # Generate based on title
        summary_text = f"This article from {source} discusses developments in {title.lower()}."
    
    return summary_text

def create_detailed_fallback_summary(article):
    """Create a comprehensive fallback summary when AI fails"""
    title = article['title']
    original_summary = article.get('summary', '')
    source = article.get('source', 'Unknown Source')
    
    if original_summary and len(original_summary) > 100:
        # Clean and use the original summary
        # Remove HTML tags if present
        import re
        clean_summary = re.sub(r'<[^>]+>', '', original_summary)
        
        # Split into sentences and take the most informative ones
        sentences = clean_summary.split('. ')
        if len(sentences) >= 4:
            summary_text = '. '.join(sentences[:4]) + '.'
        elif len(sentences) >= 2:
            summary_text = '. '.join(sentences[:2]) + '.'
        else:
            summary_text = clean_summary[:400] + '...' if len(clean_summary) > 400 else clean_summary
            
        if not summary_text.endswith('.'):
            summary_text += '.'
            
        return summary_text
    else:
        # Create a more detailed summary based on title analysis
        title_lower = title.lower()
        
        # Try to extract key topics from title
        if any(word in title_lower for word in ['breakthrough', 'announces', 'launches', 'releases']):
            context = "This major announcement"
        elif any(word in title_lower for word in ['research', 'study', 'findings']):
            context = "This research development"
        elif any(word in title_lower for word in ['model', 'ai', 'algorithm']):
            context = "This AI advancement"
        else:
            context = "This technology development"
            
        return f"{context} focuses on {title.lower()}. The article from {source} covers important innovations and insights in the artificial intelligence sector."

def create_fallback_summary(article):
    """Legacy fallback - redirects to detailed version"""
    return create_detailed_fallback_summary(article)

def create_daily_email(articles):
    """Create clean, professional email template"""
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    weekday = datetime.utcnow().strftime("%A")
    
    # Create articles HTML
    articles_html = ""
    
    for i, article in enumerate(articles, 1):
        # Clean and format article data
        title = article.get('title', 'Untitled Article').strip()
        link = article.get('link', '#').strip()
        source = article.get('source', 'Unknown Source').strip()
        
        # Format the article date
        article_date = article.get('date')
        if article_date:
            if hasattr(article_date, 'strftime'):
                date_str = article_date.strftime("%B %d, %Y")
            else:
                date_str = str(article_date)
        else:
            date_str = "Date not available"
        
        # Get AI summary and clean it
        summary_text = article.get('ai_summary', '')
        if not summary_text:
            summary_text = "This article covers important developments in artificial intelligence and technology that are shaping the industry today."
        
        # Clean summary text - remove markdown formatting but keep content readable
        summary_text = summary_text.replace('**', '').replace('*', '').strip()
        
        # Ensure summary is concise but informative
        if len(summary_text) > 500:
            sentences = summary_text.split('. ')
            summary_text = '. '.join(sentences[:3]) + '.'
        
        articles_html += f"""
        <div style="margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #e0e0e0;">
            <h2 style="color: #333333; font-size: 18px; font-weight: 600; margin: 0 0 8px 0; line-height: 1.4;">
                {i}. {title}
            </h2>
            
            <div style="margin-bottom: 15px;">
                <span style="color: #888888; font-size: 13px; font-weight: 500;">
                    {date_str} | Source: {source}
                </span>
            </div>
            
            <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0 0 15px 0; text-align: justify;">
                {summary_text}
            </p>
            
            <p style="margin: 0;">
                <a href="{link}" style="background-color: #0066cc; color: white; padding: 8px 16px; text-decoration: none; font-size: 13px; font-weight: 500; border-radius: 4px; display: inline-block;">
                    Read Full Article
                </a>
            </p>
        </div>
        """
    
    # Create clean, professional email
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Technology News - {weekday}, {current_date}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333; background-color: #f8f9fa; margin: 0; padding: 20px;">
    
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        
        <!-- Header -->
        <div style="background-color: #ffffff; padding: 30px 30px 20px 30px; border-bottom: 2px solid #f0f0f0;">
            <h1 style="color: #2c3e50; font-size: 24px; font-weight: 700; margin: 0 0 8px 0; text-align: center;">
                AI Technology News
            </h1>
            <p style="color: #7f8c8d; font-size: 16px; margin: 0; text-align: center; font-weight: 500;">
                {weekday}, {current_date} • {len(articles)} Articles
            </p>
        </div>
        
        <!-- Articles -->
        <div style="padding: 30px;">
            {articles_html}
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 20px 30px; border-top: 1px solid #e0e0e0; text-align: center;">
            <p style="color: #6c757d; font-size: 12px; margin: 0; line-height: 1.4;">
                AI-generated summaries • Delivered daily
            </p>
        </div>
        
    </div>
    
</body>
</html>
    """

def send_gmail(articles):
    """Send single daily email with all articles using Gmail SMTP"""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_PASSWORD")
    recipient_emails_str = os.getenv("RECIPIENT_EMAILS")

    if not all([gmail_user, gmail_password, recipient_emails_str]):
        raise ValueError("Gmail environment variables not fully set (GMAIL_USER, GMAIL_PASSWORD, RECIPIENT_EMAILS).")

    recipients = [email.strip() for email in recipient_emails_str.split(',')]
    
    # Create daily email content with all articles
    html_content = create_daily_email(articles)
    
    # Create dynamic subject line
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    weekday = datetime.utcnow().strftime("%A")
    subject = f"AI Technology News - {weekday}, {current_date} ({len(articles)} articles)"
    
    # Setup the MIME
    message = MIMEMultipart()
    message["From"] = gmail_user
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(html_content, "html"))

    try:
        # Connect to Gmail's SMTP server
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        raise e

if __name__ == "__main__":
    print("🚀 Otomasyon başlatılıyor...")
    articles = fetch_news_articles()
    print(f"📰 {len(articles)} haber bulundu.")
    summarized = summarize_with_gemini(articles)
    print("🤖 Haberler özetlendi.")
    if send_gmail(summarized):
        print("✅ Bulten basariyla gonderildi!")
    else:
        print("❌ E-posta gonderilemedi. Ayarlari kontrol et.")
