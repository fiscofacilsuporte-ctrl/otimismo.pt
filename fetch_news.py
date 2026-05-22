import os
import requests
import json
from datetime import datetime
import feedparser
from dateutil import parser


# Mapeamento de fontes para categorias (melhor que depender do newsapi)
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

def translate_text(text, target_lang='pt'):
    # Simplified translation using a public API (MyMemory)
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair=en|{target_lang}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get('responseStatus') == 200:
            return data.get('responseData').get('translatedText')
    except:
        pass
    return text

def fetch_rss_articles(rss_url, category, translate=False):
    articles = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title = entry.title
            summary = entry.summary if hasattr(entry, 'summary') else entry.title
            
            if translate:
                title = translate_text(title)
                summary = translate_text(summary[:500]) # Limit summary length for translation
                
            url = entry.link
            published_date = parser.parse(entry.published).isoformat() if hasattr(entry, 'published') else datetime.now().isoformat()
            
            # Since these are curated positive feeds, we can be more lenient or trust them
            positive_keywords_check = ["bom", "positivo", "sucesso", "avanço", "esperança", "inspiração", "progresso", "good", "positive", "success", "hope", "inspire"]
            negative_keywords_check = ["morte", "crime", "guerra", "crise", "bloqueio", "erro", "falha", "opinião", "colunista", "death", "war", "crisis"]

            is_positive = any(kw in title.lower() or kw in summary.lower() for kw in positive_keywords_check)
            is_negative = any(kw in title.lower() or kw in summary.lower() for kw in negative_keywords_check)

            # For specialized feeds like Razões para Acreditar, we trust more
            if "razoesparaacreditar" in rss_url or (is_positive and not is_negative):
                articles.append({
                    'title': title,
                    'summary': summary,
                    'url': url,
                    'img': entry.media_content[0]['url'] if hasattr(entry, 'media_content') and len(entry.media_content) > 0 else None,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else 'Desconhecido',
                    'cat': category,
                    'date': published_date,
                    'score': 0.98 if "razoesparaacreditar" in rss_url else 0.95,
                })
    except Exception as e:
        print(f"Erro ao buscar RSS de {rss_url}: {e}")
    return articles

def fetch_positive_news():


    all_articles = []

    # RSS Feeds de notícias positivas
    rss_feeds = [
        {"url": "https://razoesparaacreditar.com/feed/", "cat": "sociedade", "translate": False},
        {"url": "https://news.un.org/pt/news/topic/health/feed/rss.xml", "cat": "saude", "translate": False},
        {"url": "https://news.un.org/pt/news/topic/culture-and-education/feed/rss.xml", "cat": "cultura", "translate": False},
        {"url": "https://news.un.org/pt/news/topic/economic-development/feed/rss.xml", "cat": "economia", "translate": False},
        {"url": "https://www.goodnewsnetwork.org/feed/", "cat": "sociedade", "translate": True},
        {"url": "https://www.positive.news/feed/", "cat": "sociedade", "translate": True},
        {"url": "https://reasonstobecheerful.world/feed/", "cat": "sociedade", "translate": True},
        {"url": "https://www.optimistdaily.com/feed/", "cat": "sociedade", "translate": True},
    ]

    for feed_info in rss_feeds:
        translate = feed_info.get("translate", False)
        # Fetch only top 5 articles from each feed to keep it fast
        all_articles.extend(fetch_rss_articles(feed_info["url"], feed_info["cat"], translate=translate)[:5])

    # Limitar a 12 notícias, priorizando variedade de categorias
    final_articles = select_diverse(all_articles, 12)

    if not final_articles:
        print("Sem notícias novas. Mantendo dados existentes.")
        return

    output = {
        "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "news": final_articles
    }

    with open("noticias.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Sucesso! {len(final_articles)} notícias guardadas em noticias.json")
    cats = [a["cat"] for a in final_articles]
    print(f"Categorias: {dict((c, cats.count(c)) for c in set(cats))}")


def select_diverse(articles, limit):
    """Seleciona notícias garantindo variedade de categorias."""
    if not articles:
        return []

    selected = []
    cat_count = {}
    max_per_cat = 3  # Máximo de 3 notícias por categoria

    # Primeira passagem: uma de cada categoria
    for art in articles:
        cat = art['cat']
        if cat_count.get(cat, 0) == 0:
            selected.append(art)
            cat_count[cat] = 1
            if len(selected) >= limit:
                break

    # Segunda passagem: preencher até ao limite
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
