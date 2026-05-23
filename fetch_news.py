import os, requests, json, feedparser, re
from datetime import datetime
from dateutil import parser
from urllib.parse import quote
from bs4 import BeautifulSoup

# Mapeamento de fontes para categorias
SOURCE_CATEGORY_MAP = {'expresso': 'economia', 'observador': 'sociedade', 'publico': 'ciencia', 'rtp': 'sociedade', 'tsf': 'sociedade', 'record': 'desporto', 'jornal de negócios': 'economia', 'dinheiro vivo': 'economia', 'jornal de notícias': 'sociedade', 'correio da manhã': 'sociedade', 'folha de s.paulo': 'sociedade', 'globo': 'sociedade', 'g1': 'sociedade', 'uol': 'cultura', 'estadão': 'economia', 'veja': 'sociedade', 'valor econômico': 'economia', 'carta capital': 'sociedade', 'jornal de angola': 'sociedade', 'o país': 'sociedade', 'o país moçambique': 'sociedade', 'savana': 'sociedade', 'sic notícias': 'sociedade', 'diário de notícias': 'sociedade', 'bola': 'desporto', 'ojogo': 'desporto'}
KEYWORD_CATEGORY_MAP = {'cienc': 'ciencia', 'pesquis': 'ciencia', 'descobert': 'ciencia', 'investigaç': 'ciencia', 'estudo': 'ciencia', 'universidade': 'ciencia', 'saúde': 'saude', 'medic': 'saude', 'hospital': 'saude', 'vacinaç': 'saude', 'doença': 'saude', 'tratamento': 'saude', 'tecnolog': 'tecnologia', 'inovaç': 'tecnologia', 'startup': 'tecnologia', 'digital': 'tecnologia', 'inteligência artificial': 'tecnologia', 'software': 'tecnologia', 'ambiente': 'ambiente', 'clima': 'ambiente', 'energi': 'ambiente', 'renovável': 'ambiente', 'floresta': 'ambiente', 'oceano': 'ambiente', 'desport': 'desporto', 'futebol': 'desporto', 'campeão': 'desporto', 'olimp': 'desporto', 'atleta': 'desporto', 'medalh': 'desporto', 'econom': 'economia', 'emprego': 'economia', 'crescimento': 'economia', 'invest': 'economia', 'mercado': 'economia', 'exportaç': 'economia', 'cultur': 'cultura', 'arte': 'cultura', 'música': 'cultura', 'cinema': 'cultura', 'teatro': 'cultura', 'patrimônio': 'cultura', 'festival': 'cultura', 'exposição': 'cultura'}

# Palavras-chave POSITIVAS
POSITIVE_KEYWORDS = ['sucesso', 'vitória', 'triunfo', 'conquista', 'avanço', 'progresso', 'inovação', 'melhoria', 'desenvolvimento', 'crescimento', 'esperança', 'inspirador', 'incrível', 'fantástico', 'maravilhoso', 'extraordinário', 'positivo', 'bom', 'excelente', 'ótimo', 'magnífico', 'solidariedade', 'ajuda', 'humanitário', 'voluntário', 'caridade', 'descoberta', 'pesquisa', 'científico', 'estudo', 'investigação', 'preservação', 'conservação', 'sustentável', 'renovável', 'ambiental', 'saúde', 'bem-estar', 'cura', 'tratamento', 'vacinação', 'educação', 'aprendizado', 'conhecimento', 'paz', 'acordo', 'cooperação', 'união', 'comunidade', 'recorde', 'melhor', 'primeira vez', 'novo', 'inédito', 'resgate', 'salvação', 'proteção', 'segurança', 'prêmio', 'reconhecimento', 'homenagem', 'celebração', 'oportunidade', 'chance', 'possibilidade', 'potencial', 'liberdade', 'direitos', 'justiça', 'igualdade', 'inclusão', 'generosidade', 'gentileza']

# Palavras-chave NEGATIVAS
NEGATIVE_KEYWORDS = ['morte', 'crime', 'guerra', 'crise', 'bloqueio', 'erro', 'falha', 'opinião', 'colunista', 'death', 'war', 'crisis', 'murder', 'attack', 'violência', 'acidente', 'desastre', 'catástrofe', 'tragédia', 'doença', 'epidemia', 'pandemia', 'corrupção', 'fraude', 'escândalo', 'roubo', 'assalto', 'pobreza', 'miséria', 'fome', 'desemprego', 'recessão', 'depressão', 'ansiedade', 'suicídio', 'automutilação', 'conflito', 'disputa', 'tensão', 'ameaça', 'perigo', 'perda', 'luto', 'sofrimento', 'dor', 'angústia', 'fechamento', 'encerramento', 'cancelamento', 'suspensão', 'adiamento', 'assassinato', 'tiroteio', 'vítima', 'ferido', 'ataque', 'terrorismo', 'mortalidade', 'letalidade']

# LISTA NEGRA ABSOLUTA
BLACKLIST_KEYWORDS = ['hantavírus', 'ebola', 'ébola', 'dengue', 'malária', 'surto', 'contágio', 'infecção', 'infectado', 'morto', 'falecido', 'homicídio', 'violação', 'guerra', 'bombardeio', 'míssil', 'exército', 'combate', 'inflação', 'dívida', 'falência', 'corte', 'greve', 'protesto', 'manifestação', 'preso', 'detido', 'tribunal', 'julgamento', 'pena', 'prisão']

def extract_image(entry):
    if hasattr(entry, 'media_content') and len(entry.media_content) > 0: return entry.media_content[0]['url']
    if hasattr(entry, 'links'):
        for link in entry.links:
            if 'image' in link.get('type', ''): return link.get('href')
    content = (entry.summary if hasattr(entry, 'summary') else "") + (entry.content[0].value if hasattr(entry, 'content') else "")
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'): return img.get('src')
    return None

def calculate_sentiment_score(title, summary):
    text = (title + ' ' + (summary or '')).lower()
    for black in BLACKLIST_KEYWORDS:
        if black in text: return -1.0
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    if neg > 0: return (pos / (pos + (neg * 3))) if pos + neg > 0 else 0.0
    return pos / (pos + neg) if pos + neg > 0 else 0.6

def fetch_rss_articles(rss_url, category, source_name=None):
    articles = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title, summary = entry.title, (entry.summary if hasattr(entry, 'summary') else entry.title)
            score = calculate_sentiment_score(title, summary)
            if score >= 0.55:
                articles.append({
                    'title': title, 
                    'summary': BeautifulSoup(summary, "html.parser").get_text()[:300] + "...", 
                    'url': entry.link, 
                    'img': extract_image(entry), 
                    'source': source_name or (feed.feed.title if hasattr(feed.feed, 'title') else 'Fonte'), 
                    'cat': category, 
                    'date': parser.parse(entry.published).isoformat() if hasattr(entry, 'published') else datetime.now().isoformat(), 
                    'score': score
                })
    except: pass
    return articles

def fetch_google_news(query, category):
    articles = []
    try:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=pt-PT&gl=PT&ceid=PT:pt"
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            title, summary = entry.title, (entry.summary if hasattr(entry, 'summary') else entry.title)
            score = calculate_sentiment_score(title, summary)
            if score >= 0.6:
                articles.append({'title': title, 'summary': BeautifulSoup(summary, "html.parser").get_text()[:250] + "...", 'url': entry.link, 'img': None, 'source': 'Google News', 'cat': category, 'date': parser.parse(entry.published).isoformat() if hasattr(entry, 'published') else datetime.now().isoformat(), 'score': score})
    except: pass
    return articles

def fetch_positive_news():
    all_articles = []
    
    # 1. Fontes Curadas de Notícias Positivas
    feeds = [
        {"url": "https://razoesparaacreditar.com/feed/", "cat": "sociedade", "name": "Razões para Acreditar"},
        {"url": "https://www.goodnewsnetwork.org/feed/", "cat": "sociedade", "name": "Good News Network"},
        {"url": "https://www.positive.news/feed/", "cat": "sociedade", "name": "Positive News"},
        {"url": "https://reasonstobecheerful.world/feed/", "cat": "sociedade", "name": "Reasons to be Cheerful"},
        {"url": "https://news.un.org/pt/news/topic/health/feed/rss.xml", "cat": "saude", "name": "ONU News"},
        {"url": "https://news.un.org/pt/news/topic/culture-and-education/feed/rss.xml", "cat": "cultura", "name": "ONU News"},
        {"url": "https://news.un.org/pt/news/topic/economic-development/feed/rss.xml", "cat": "economia", "name": "ONU News"}
    ]
    
    # 2. Novas Fontes Específicas (Portugal e Internacionais)
    specific_feeds = [
        {"url": "https://lifestyle.sapo.pt/rss/saude", "cat": "saude", "name": "SAPO Lifestyle"},
        {"url": "https://p3.publico.pt/rss", "cat": "cultura", "name": "Público P3"},
        {"url": "https://www.sicnoticias.pt/rss/boas-noticias", "cat": "sociedade", "name": "SIC Notícias"},
        {"url": "https://www.theguardian.com/world/series/the-upside/rss", "cat": "sociedade", "name": "The Guardian (Upside)"}
    ]
    
    for f in feeds + specific_feeds:
        all_articles.extend(fetch_rss_articles(f["url"], f["cat"], f.get("name")))
    
    # 3. Google News (Queries Refinadas)
    queries = [
        {"query": "inovação tecnológica portugal", "cat": "tecnologia"},
        {"query": "sustentabilidade ambiental sucesso", "cat": "ambiente"},
        {"query": "ciência descoberta fantástica", "cat": "ciencia"},
        {"query": "desporto vitória inspiradora portugal", "cat": "desporto"},
        {"query": "economia crescimento positivo portugal", "cat": "economia"}
    ]
    for q in queries:
        all_articles.extend(fetch_google_news(q["query"], q["cat"]))
    
    seen, unique = set(), []
    for a in all_articles:
        if a['url'] not in seen: seen.add(a['url']); unique.append(a)
    
    final = sorted(unique, key=lambda x: x['score'], reverse=True)[:24]
    
    if final:
        with open("noticias.json", "w", encoding="utf-8") as f: 
            json.dump({"last_update": datetime.now().strftime("%d/%m/%Y %H:%M"), "news": final}, f, ensure_ascii=False, indent=2)
        print(f"Sucesso! {len(final)} notícias otimistas guardadas de múltiplas fontes.")

if __name__ == "__main__":
    fetch_positive_news()
