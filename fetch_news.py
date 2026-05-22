import os
import requests
import json
from datetime import datetime

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

def fetch_positive_news():
    api_key = os.getenv('NEWS_API_KEY')

    if not api_key:
        print("Erro: NEWS_API_KEY não encontrada.")
        return

    # Estratégia: buscar notícias positivas em português de TODO o mundo
    # A NewsAPI com language=pt inclui fontes internacionais que escrevem em pt
    # Usamos também domains específicos para cobrir Brasil, Angola, Moçambique
    
    all_articles = []

    # Query 1: Palavras-chave positivas em português (Portugal + Brasil + África)
    positive_keywords = (
        '("cura" OR "avanço" OR "solidariedade" OR "vitória" OR "sustentabilidade" OR '
        '"descoberta" OR "inovação" OR "esperança" OR "conquista" OR "sucesso" OR '
        '"premiado" OR "recorde" OR "celebração" OR "inauguração" OR "renovável" OR '
        '"boas notícias" OR "inspiração" OR "exemplo" OR "progresso")'
    )

    # Lista de termos negativos para filtrar
    negative_keywords = 'NOT (morte OR crime OR guerra OR crise OR bloqueio OR erro OR falha OR opinião OR colunista)'

    queries = [
        # Notícias positivas gerais em português
        {
            'url': f'https://newsapi.org/v2/everything?q={positive_keywords} {negative_keywords}&language=pt&sortBy=publishedAt&pageSize=40&apiKey={api_key}',
            'desc': 'positivas em português'
        },
        # Fontes brasileiras
        {
            'url': f'https://newsapi.org/v2/everything?q={positive_keywords} {negative_keywords}&domains=globo.com,folha.uol.com.br,g1.globo.com,estadao.com.br,veja.abril.com.br&sortBy=publishedAt&pageSize=20&apiKey={api_key}',
            'desc': 'fontes brasileiras'
        },
        # Fontes portuguesas
        {
            'url': f'https://newsapi.org/v2/everything?q={positive_keywords} {negative_keywords}&domains=publico.pt,observador.pt,expresso.pt,rtp.pt,tsf.pt,sicnoticias.pt,dn.pt&sortBy=publishedAt&pageSize=20&apiKey={api_key}',
            'desc': 'fontes portuguesas'
        },
    ]

    seen_titles = set()

    for q in queries:
        try:
            print(f"A pesquisar: {q['desc']}...")
            response = requests.get(q['url'], timeout=10)
            data = response.json()

            if data.get('status') == 'ok':
                for art in data.get('articles', []):
                    title = art.get('title', '')
                    if not title or title in seen_titles or '[Removed]' in title:
                        continue
                    seen_titles.add(title)

                    source_name = art.get('source', {}).get('name', 'Desconhecido')
                    description = art.get('description', '')
                    category = detect_category(title, description, source_name)

                    all_articles.append({
                        'title': title,
                        'summary': description or title,
                        'url': art.get('url', '#'),
                        'img': art.get('urlToImage'),
                        'source': source_name,
                        'cat': category,
                        'date': art.get('publishedAt', datetime.now().isoformat()),
                        'score': round(0.80 + (hash(title) % 18) / 100, 2),  # Score entre 0.80 e 0.98
                    })
            else:
                print(f"Erro na API ({q['desc']}): {data.get('message')}")

        except Exception as e:
            print(f"Erro ao pesquisar '{q['desc']}': {e}")

    # Limitar a 12 notícias, priorizando variedade de categorias
    final_articles = select_diverse(all_articles, 12)

    if not final_articles:
        print("Sem notícias novas. Mantendo dados existentes.")
        return

    output = {
        'last_update': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'news': final_articles
    }

    with open('noticias.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Sucesso! {len(final_articles)} notícias guardadas em noticias.json")
    cats = [a['cat'] for a in final_articles]
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
