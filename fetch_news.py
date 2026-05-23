import os
import requests
import json
from datetime import datetime
import feedparser
from dateutil import parser
import re
from urllib.parse import quote

# Mapeamento de fontes para categorias
SOURCE_CATEGORY_MAP = {
    'expresso': 'economia', 'observador': 'sociedade', 'publico': 'ciencia',
    'rtp': 'sociedade', 'tsf': 'sociedade', 'record': 'desporto',
    'jornal de negócios': 'economia', 'dinheiro vivo': 'economia',
    'jornal de notícias': 'sociedade', 'correio da manhã': 'sociedade',
    'folha de s.paulo': 'sociedade', 'globo': 'sociedade', 'g1': 'sociedade',
    'uol': 'cultura', 'estadão': 'economia', 'veja': 'sociedade',
    'valor econômico': 'economia', 'carta capital': 'sociedade',
    'jornal de angola': 'sociedade', 'o país': 'sociedade',
    'o país moçambique': 'sociedade', 'savana': 'sociedade',
    'sic notícias': 'sociedade', 'diário de notícias': 'sociedade',
    'bola': 'desporto', 'ojogo': 'desporto',
}

KEYWORD_CATEGORY_MAP = {
    'cienc': 'ciencia', 'pesquis': 'ciencia', 'descobert': 'ciencia',
    'investigaç': 'ciencia', 'estudo': 'ciencia', 'universidade': 'ciencia',
    'saúde': 'saude', 'medic': 'saude', 'hospital': 'saude',
    'vacinaç': 'saude', 'doença': 'saude', 'tratamento': 'saude',
    'tecnolog': 'tecnologia', 'inovaç': 'tecnologia', 'startup': 'tecnologia',
    'digital': 'tecnologia', 'inteligência artificial': 'tecnologia', 'software': 'tecnologia',
    'ambiente': 'ambiente', 'clima': 'ambiente', 'energi': 'ambiente',
    'renovável': 'ambiente', 'floresta': 'ambiente', 'oceano': 'ambiente',
    'desport': 'desporto', 'futebol': 'desporto', 'campeão': 'desporto',
    'olimp': 'desporto', 'atleta': 'desporto', 'medalh': 'desporto',
    'econom': 'economia', 'emprego': 'economia', 'crescimento': 'economia',
    'invest': 'economia', 'mercado': 'economia', 'exportaç': 'economia',
    'cultur': 'cultura', 'arte': 'cultura', 'música': 'cultura',
    'cinema': 'cultura', 'teatro': 'cultura', 'patrimônio': 'cultura',
    'festival': 'cultura', 'exposição': 'cultura',
}

# Palavras-chave POSITIVAS (para aumentar score)
POSITIVE_KEYWORDS = [
    'sucesso', 'vitória', 'triunfo', 'conquista', 'avanço', 'progresso',
    'inovação', 'melhoria', 'desenvolvimento', 'crescimento', 'esperança',
    'inspirador', 'incrível', 'fantástico', 'maravilhoso', 'extraordinário',
    'positivo', 'bom', 'excelente', 'ótimo', 'magnífico',
    'ajuda', 'solidariedade', 'humanitário', 'voluntário', 'caridade',
    'descoberta', 'pesquisa', 'científico', 'estudo', 'investigação',
    'preservação', 'conservação', 'sustentável', 'renovável', 'ambiental',
    'saúde', 'bem-estar', 'cura', 'tratamento', 'vacinação',
    'educação', 'aprendizado', 'conhecimento', 'cultura', 'arte',
    'paz', 'acordo', 'cooperação', 'união', 'comunidade',
    'recorde', 'melhor', 'primeira vez', 'novo', 'inédito',
    'resgate', 'salvação', 'proteção', 'segurança', 'defesa',
    'prêmio', 'reconhecimento', 'homenagem', 'celebração', 'festividade',
    'oportunidade', 'chance', 'possibilidade', 'potencial', 'promessa',
    'liberdade', 'direitos', 'justiça', 'igualdade', 'inclusão',
]

# Palavras-chave NEGATIVAS (para diminuir score)
NEGATIVE_KEYWORDS = [
    'morte', 'crime', 'guerra', 'crise', 'bloqueio', 'erro', 'falha',
    'opinião', 'colunista', 'death', 'war', 'crisis', 'murder', 'attack',
    'violência', 'acidente', 'desastre', 'catástrofe', 'tragédia',
    'doença', 'epidemia', 'pandemia', 'contaminação', 'poluição',
    'corrupção', 'fraude', 'escândalo', 'roubo', 'assalto',
    'pobreza', 'miséria', 'fome', 'desemprego', 'recessão',
    'depressão', 'ansiedade', 'suicídio', 'automutilação', 'droga',
    'conflito', 'disputa', 'tensão', 'ameaça', 'perigo',
    'perda', 'luto', 'sofrimento', 'dor', 'angústia',
    'fechamento', 'encerramento', 'cancelamento', 'suspensão', 'adiamento',
]

def detect_category(title, description, source_name):
    """Detecta categoria com base no título, descrição e fonte."""
    text = (title + ' ' + (description or '')).lower()
    src = source_name.lower()

    # Primeiro tenta pela fonte
    for key, cat in SOURCE_CATEGORY_MAP.items():
        if key in src:
            return cat

    # Depois pelo conteúdo
    for keyword, cat in KEYWORD_CATEGORY_MAP.items():
        if keyword in text:
            return cat

    return 'sociedade'

def calculate_sentiment_score(title, summary):
    """
    Calcula um score de sentimento (0-1) baseado em palavras-chave.
    Quanto mais próximo de 1, mais positivo é o conteúdo.
    """
    text = (title + ' ' + (summary or '')).lower()
    
    # Contar palavras positivas
    positive_count = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text)
    
    # Contar palavras negativas
    negative_count = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text)
    
    # Calcular score
    if positive_count + negative_count == 0:
        # Se não há palavras-chave, usar um score neutro
        score = 0.6
    else:
        score = positive_count / (positive_count + negative_count)
    
    return score

def fetch_rss_articles(rss_url, category, min_sentiment_score=0.5):
    """Obtém artigos de um feed RSS com filtragem de sentimento."""
    articles = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title = entry.title
            summary = entry.summary if hasattr(entry, 'summary') else entry.title
            
            url = entry.link
            published_date = parser.parse(entry.published).isoformat() if hasattr(entry, 'published') else datetime.now().isoformat()
            
            # Calcular score de sentimento
            sentiment_score = calculate_sentiment_score(title, summary)
            
            # Filtrar por score de sentimento
            if sentiment_score >= min_sentiment_score:
                articles.append({
                    'title': title,
                    'summary': summary,
                    'url': url,
                    'img': entry.media_content[0]['url'] if hasattr(entry, 'media_content') and len(entry.media_content) > 0 else None,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else 'Desconhecido',
                    'cat': category,
                    'date': published_date,
                    'score': sentiment_score,
                })
    except Exception as e:
        print(f"Erro ao buscar RSS de {rss_url}: {e}")
    return articles

def fetch_google_news(query, category, num_results=10):
    """
    Obtém notícias do Google News via RSS.
    Nota: O Google News RSS é limitado, mas funciona para queries específicas.
    """
    articles = []
    try:
        # URL do Google News RSS para a query específica
        google_news_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=pt-PT&gl=PT&ceid=PT:pt"
        
        feed = feedparser.parse(google_news_url)
        
        for entry in feed.entries[:num_results]:
            title = entry.title
            summary = entry.summary if hasattr(entry, 'summary') else entry.title
            
            url = entry.link
            published_date = parser.parse(entry.published).isoformat() if hasattr(entry, 'published') else datetime.now().isoformat()
            
            # Calcular score de sentimento
            sentiment_score = calculate_sentiment_score(title, summary)
            
            # Filtrar por score de sentimento
            if sentiment_score >= 0.55:
                articles.append({
                    'title': title,
                    'summary': summary,
                    'url': url,
                    'img': None,
                    'source': 'Google News',
                    'cat': category,
                    'date': published_date,
                    'score': sentiment_score,
                })
    except Exception as e:
        print(f"Erro ao buscar Google News para '{query}': {e}")
    
    return articles

def fetch_positive_news():
    """Obtém notícias positivas de múltiplas fontes."""
    all_articles = []

    # RSS Feeds de notícias positivas (curadas)
    rss_feeds = [
        {"url": "https://razoesparaacreditar.com/feed/", "cat": "sociedade", "min_score": 0.5},
        {"url": "https://news.un.org/pt/news/topic/health/feed/rss.xml", "cat": "saude", "min_score": 0.5},
        {"url": "https://news.un.org/pt/news/topic/culture-and-education/feed/rss.xml", "cat": "cultura", "min_score": 0.5},
        {"url": "https://news.un.org/pt/news/topic/economic-development/feed/rss.xml", "cat": "economia", "min_score": 0.5},
        {"url": "https://www.goodnewsnetwork.org/feed/", "cat": "sociedade", "min_score": 0.5},
        {"url": "https://www.positive.news/feed/", "cat": "sociedade", "min_score": 0.5},
        {"url": "https://reasonstobecheerful.world/feed/", "cat": "sociedade", "min_score": 0.5},
        {"url": "https://www.optimistdaily.com/feed/", "cat": "sociedade", "min_score": 0.5},
    ]

    print("=== Obtendo notícias de feeds RSS ===")
    for feed_info in rss_feeds:
        min_score = feed_info.get("min_score", 0.5)
        articles = fetch_rss_articles(feed_info["url"], feed_info["cat"], min_sentiment_score=min_score)
        print(f"Feed {feed_info['url']}: {len(articles)} artigos encontrados")
        all_articles.extend(articles)

    # Google News queries
    print("\n=== Obtendo notícias do Google News ===")
    google_news_queries = [
        {"query": "notícias positivas Portugal", "cat": "sociedade"},
        {"query": "inovação tecnológica", "cat": "tecnologia"},
        {"query": "descoberta científica", "cat": "ciencia"},
        {"query": "sustentabilidade ambiente", "cat": "ambiente"},
        {"query": "saúde bem-estar", "cat": "saude"},
        {"query": "educação desenvolvimento", "cat": "cultura"},
        {"query": "economia crescimento", "cat": "economia"},
    ]

    for query_info in google_news_queries:
        articles = fetch_google_news(query_info["query"], query_info["cat"], num_results=5)
        print(f"Google News '{query_info['query']}': {len(articles)} artigos encontrados")
        all_articles.extend(articles)

    # Remover duplicatas
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article['url'] not in seen_urls:
            seen_urls.add(article['url'])
            unique_articles.append(article)

    # Limitar a 12 notícias
    final_articles = select_diverse(unique_articles, 12)

    if not final_articles:
        print("Sem notícias novas.")
        return

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    output = {
        "last_update": now,
        "news": final_articles
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "noticias.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Sucesso! {len(final_articles)} notícias guardadas.")

def select_diverse(articles, limit):
    """Seleciona notícias garantindo variedade de categorias."""
    if not articles:
        return []
    articles = sorted(articles, key=lambda x: x['score'], reverse=True)
    selected = []
    cat_count = {}
    max_per_cat = 3
    for art in articles:
        cat = art['cat']
        if cat_count.get(cat, 0) == 0:
            selected.append(art)
            cat_count[cat] = 1
            if len(selected) >= limit:
                break
    for art in articles:
        if art in selected:
            continue
        cat = art['cat']
        if cat_count.get(cat, 0) < max_per_cat:
            selected.append(art)
            cat_count[cat] = cat_count.get(cat, 0) + 1
            if len(selected) >= limit:
                break
    return selected[:limit]

if __name__ == "__main__":
    fetch_positive_news()
