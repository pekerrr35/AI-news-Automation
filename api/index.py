import os
import requests
import xml.etree.ElementTree as ET
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def fetch_news():
    RSS_FEEDS = [
        "https://singularityhub.com/feed/",
        "https://longevity.technology/feed/",
        "https://www.artificialintelligence-news.com/feed/",
        "https://www.nocodereport.com/rss",
        "https://www.realt.co/feed/",
        "https://www.darkreading.com/rss.xml",
        "https://www.entrepreneur.com/topic/artificial-intelligence.rss"
    ]
    articles = []
    for url in RSS_FEEDS:
        try:
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:2]:
                articles.append({
                    'title': item.find('title').text,
                    'link': item.find('link').text,
                    'summary': item.find('description').text[:200] if item.find('description') is not None else ""
                })
        except: continue
    return articles[:10]

def summarize(articles):
    key = os.getenv("GEMINI_API_KEY")
    if not key or not articles: return articles
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    for art in articles:
        prompt = f"Sen bir stratejistsin. Bu haberi 2026 trendleriyle (AI, Longevity, Yatırım) bağdaştırarak Türkçe özetle: {art['title']}"
        try:
            response = model.generate_content(prompt)
            art['summary'] = response.text
        except: continue
    return articles

def send_email(articles):
    user = os.getenv("SENDER_EMAIL")
    pw = os.getenv("SENDER_PASSWORD")
    target = os.getenv("RECEIVER_EMAILS")
    if not user or not pw: return False
    
    html = "<h2>The 2026 Edge Raporu</h2>"
    for a in articles:
        html += f"<h3>{a['title']}</h3><p>{a['summary']}</p><a href='{a['link']}'>Detay</a><hr>"
    
    msg = MIMEMultipart()
    msg['Subject'] = f"2026 Vizyonu - {datetime.now().strftime('%d/%m')}"
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, target.split(','), msg.as_string())
        return True
    except: return False

if __name__ == "__main__":
    print("🚀 Başlatılıyor...")
    news = fetch_news()
    print(f"📰 {len(news)} haber çekildi.")
    summarized = summarize(news)
    if send_email(summarized):
        print("✅ Başarılı! Mail gönderildi.")
    else:
        print("❌ Hata! Mail gönderilemedi.")
