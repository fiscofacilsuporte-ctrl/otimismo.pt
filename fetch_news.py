import os
import requests
import json
from datetime import datetime

def fetch_positive_news():
    # Obter a API Key das variáveis de ambiente (GitHub Secrets)
    api_key = os.getenv('NEWS_API_KEY')
    
    if not api_key:
        print("Erro: NEWS_API_KEY não encontrada.")
        return

    # Palavras-chave que remetem para notícias positivas
    keywords = '(cura OR avanço OR solidariedade OR vitória OR sustentabilidade OR descoberta OR inovação OR alegria OR esperança)'
    
    # URL da NewsAPI (usando a chave fornecida)
    # Filtramos por língua portuguesa (language=pt)
    url = f'https://newsapi.org/v2/everything?q={keywords}&language=pt&sortBy=publishedAt&apiKey={api_key}'

    try:
        response = requests.get(url)
        data = response.json()

        if data.get('status') == 'ok':
            articles = data.get('articles', [])
            
            # Limitar a 12 notícias para manter o site leve
            news_list = []
            for art in articles[:12]:
                news_list.append({
                    'title': art.get('title'),
                    'description': art.get('description'),
                    'url': art.get('url'),
                    'image': art.get('urlToImage'),
                    'source': art.get('source', {}).get('name'),
                    'date': art.get('publishedAt')
                })

            # Guardar os dados num ficheiro JSON
            output = {
                'last_update': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'news': news_list
            }

            with open('noticias.json', 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=4)
            
            print(f"Sucesso! {len(news_list)} notícias guardadas em noticias.json")
        else:
            print(f"Erro na API: {data.get('message')}")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    fetch_positive_news()
