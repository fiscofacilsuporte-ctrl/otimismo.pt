#!/usr/bin/env python3
"""
fetch_news.py — Gerador de noticias.json para otimismo.pt
Executa via GitHub Actions (diariamente ou manualmente).

Fontes priorizadas para notícias positivas em português:
  • Good News Network (EN) — especializada em boas notícias, alta qualidade
  • Positive News UK (EN) — jornalismo construtivo
  • Público (PT) — ciência, sociedade, ambiente
  • Observador (PT) — tecnologia, inovação, economia
  • Jornal de Negócios (PT) — economia positiva
  • Eco.pt (PT) — sustentabilidade, ambiente
  • TSF (PT) — cultura, sociedade
  • RTP Notícias (PT) — geral, desporto
  • Shifter (PT) — tecnologia, startups
  • Diário de Notícias (PT) — sociedade, cultura
  • Solutions Journalism Network — jornalismo de soluções
  • BBC Good News — positivo internacional

Categorias suportadas: ciencia, tecnologia, ambiente, saude, sociedade, economia, desporto, cultura
"""

import json
import time
import re
import hashlib
import ssl
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET

# ── CONFIGURAÇÃO ─────────────────────────────────────────

OUTPUT_FILE   = "noticias.json"
MAX_NEWS      = 30      # máximo de notícias no JSON final
MIN_SCORE     = 0.60    # score mínimo para incluir
FETCH_TIMEOUT = 12      # segundos por feed

# ── FONTES RSS / ATOM ────────────────────────────────────
# Formato: (url, source_name, default_category, is_english)
FEEDS = [
    # ── PORTUGUÊS ─────────────────────────────────────────
    ("https://feeds.feedburner.com/PublicoCienciaETecnologia",
     "Público", "ciencia", False),
    ("https://www.publico.pt/api/rss/ambiente",
     "Público", "ambiente", False),
    ("https://www.publico.pt/api/rss/economia",
     "Público", "economia", False),
    ("https://observador.pt/tag/tecnologia/feed/",
     "Observador", "tecnologia", False),
    ("https://observador.pt/tag/ciencia/feed/",
     "Observador", "ciencia", False),
    ("https://observador.pt/tag/saude/feed/",
     "Observador", "saude", False),
    ("https://observador.pt/seccao/desporto/feed/",
     "Observador", "desporto", False),
    ("https://www.jornaldenegocios.pt/rss",
     "Jornal de Negócios", "economia", False),
    ("https://www.tsf.pt/rss/",
     "TSF", "sociedade", False),
    ("https://www.rtp.pt/noticias/rss/desporto",
     "RTP", "desporto", False),
    ("https://eco.pt/feed/",
     "ECO", "ambiente", False),
    ("https://www.dn.pt/rss/",
     "Diário de Notícias", "sociedade", False),
    ("https://shifter.sapo.pt/feed/",
     "Shifter", "tecnologia", False),

    # ── INGLÊS (notícias positivas especializadas) ────────
    ("https://www.goodnewsnetwork.org/feed/",
     "Good News Network", "sociedade", True),
    ("https://www.positive.news/feed/",
     "Positive News", "sociedade", True),
    ("http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
     "BBC News", "ciencia", True),
    ("http://feeds.bbci.co.uk/news/health/rss.xml",
     "BBC News", "saude", True),
    ("https://feeds.reuters.com/reuters/scienceNews",
     "Reuters", "ciencia", True),
    ("https://www.sciencedaily.com/rss/top/science.xml",
     "ScienceDaily", "ciencia", True),
]

# ── PALAVRAS-CHAVE POSITIVAS ─────────────────────────────

POSITIVE_KEYWORDS_PT = [
    "recorde","conquista","vitória","primeiro","pioneiro","sucesso","inovação",
    "descoberta","cura","avanço","melhoria","crescimento","renovável","sustentável",
    "positivo","esperança","histórico","prémio","galardão","campeão","celebração",
    "progresso","transformação","revolução","recuperação","protegido","salvo",
    "tratamento","vacina","solução","investimento","criação","emprego","lançamento",
    "aprovado","aprovação","recordista","medalha","ouro","prata","bronze",
    "parceria","acordo","colaboração","doação","voluntário","solidariedade",
    "sustentabilidade","carbono neutro","energia limpa","biodiversidade",
    "preservação","restauração","conservação","habitat","espécie","população",
    "pesquisa","investigação","estudo","publicação","nature","science",
]

POSITIVE_KEYWORDS_EN = [
    "record","breakthrough","discover","cure","advance","improvement","growth",
    "renewable","sustainable","positive","hope","historic","prize","award",
    "champion","celebrate","progress","transform","recovery","protected","save",
    "treatment","vaccine","solution","investment","create","launch","approve",
    "medal","gold","silver","bronze","partnership","agreement","collaborate",
    "donate","volunteer","solidarity","clean energy","biodiversity","preserve",
    "restore","conservation","habitat","species","research","study","nature",
    "science","first","pioneer","success","innovate","revive","green",
    "solar","wind","electric","zero emission","carbon neutral","thriving","flourish",
]

NEGATIVE_KEYWORDS = [
    "morte","morto","assassin","homicídio","acidente","crise","colapso","falência",
    "desastre","tragédia","conflito","guerra","ataque","terrorismo","corrupção",
    "escândalo","fraud","crime","roubo","violência","abuso","vitima","vítima",
    "dead","death","kill","murder","crash","disaster","collapse","bankrupt",
    "tragedy","conflict","war","attack","terrorism","corruption","scandal",
    "robbery","violence","abuse","victim","crisis","fail",
]

CATEGORY_KEYWORDS = {
    "ciencia":    ["ciência","científ","investigação","descoberta","estudo","pesquisa",
                   "nature","science","research","discover","study","laboratory"],
    "tecnologia": ["tecnologia","tech","digital","inteligência artificial","ia","ai",
                   "robot","startup","software","hardware","app","internet","5g","drone"],
    "ambiente":   ["ambiente","clima","carbono","energia","renovável","solar","vento",
                   "oceano","floresta","biodiversidade","espécie","ecosystem","climate",
                   "renewable","green","sustainable","nature","wildlife","ocean","forest"],
    "saude":      ["saúde","saude","médico","hospital","vacina","doença","cura","tratamento",
                   "cancer","vírus","medicina","health","vaccine","cure","treatment","medical"],
    "economia":   ["economia","económic","pib","emprego","investimento","mercado","empresa",
                   "exportação","crescimento","economic","gdp","employment","investment","market"],
    "desporto":   ["desporto","futebol","basquete","natação","atletismo","olimp","campeão",
                   "sport","football","soccer","basketball","swimming","champion","gold medal"],
    "cultura":    ["cultura","arte","música","cinema","teatro","literatura","museu","festival",
                   "culture","art","music","film","theater","literature","museum","festival"],
    "sociedade":  ["sociedade","comunidade","educação","escola","família","voluntário","solidar",
                   "society","community","education","school","family","volunteer","solidar"],
}

# ── UTILITÁRIOS ──────────────────────────────────────────

def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:8]

def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def detect_category(title: str, summary: str, default_cat: str) -> str:
    text = (title + " " + summary).lower()
    best_cat = default_cat
    best_count = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_cat = cat
    return best_cat

def score_article(title: str, summary: str, is_english: bool) -> float:
    """Calcula um score de positividade entre 0.0 e 1.0"""
    text = (title + " " + summary).lower()
    pos_kw = POSITIVE_KEYWORDS_EN if is_english else POSITIVE_KEYWORDS_PT
    pos_score = sum(1 for kw in pos_kw if kw in text)
    neg_score = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

    if neg_score > 0:
        base = 0.40 - (neg_score * 0.05)
    else:
        base = 0.70

    bonus = min(pos_score * 0.03, 0.28)
    final = min(base + bonus, 0.99)
    return round(final, 2)

def find_image(item) -> str | None:
    """Tenta extrair imagem do item RSS"""
    ns = {"media": "http://search.yahoo.com/mrss/"}
    for tag in ["media:thumbnail", "media:content"]:
        el = item.find(tag, ns)
        if el is not None:
            url = el.get("url")
            if url:
                return url

    enc = item.find("enclosure")
    if enc is not None:
        if "image" in enc.get("type", ""):
            return enc.get("url")

    desc = item.findtext("description") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
    if m:
        return m.group(1)

    return None

def fetch_feed(url: str, source: str, default_cat: str, is_english: bool) -> list:
    """Faz fetch de um feed RSS e retorna lista de artigos normalizados"""
    articles = []
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = Request(url, headers={"User-Agent": "otimismo.pt-bot/1.0"})
        with urlopen(req, timeout=FETCH_TIMEOUT, context=ctx) as r:
            raw = r.read()
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"  ⚠️  Erro ao carregar {source} ({url[:60]}): {e}")
        return articles

    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for item in items[:10]:
        title = strip_html(
            item.findtext("title") or
            item.findtext("{http://www.w3.org/2005/Atom}title") or ""
        )
        if not title:
            continue

        link = item.findtext("link") or ""
        atom_link = item.find("{http://www.w3.org/2005/Atom}link")
        if not link and atom_link is not None:
            link = atom_link.get("href", "")
        if not link:
            continue

        summary = strip_html(
            item.findtext("description") or
            item.findtext("{http://www.w3.org/2005/Atom}summary") or
            item.findtext("{http://www.w3.org/2005/Atom}content") or ""
        )[:300]

        pub_date = (
            item.findtext("pubDate") or
            item.findtext("{http://www.w3.org/2005/Atom}published") or
            item.findtext("{http://www.w3.org/2005/Atom}updated") or
            datetime.now(timezone.utc).isoformat()
        )

        img = find_image(item)
        s = score_article(title, summary, is_english)
        cat = detect_category(title, summary, default_cat)

        if s >= MIN_SCORE:
            articles.append({
                "id":      make_id(link),
                "cat":     cat,
                "title":   title[:200],
                "summary": summary,
                "source":  source,
                "date":    pub_date,
                "url":     link,
                "img":     img,
                "score":   s,
            })

    print(f"  ✅  {source}: {len(articles)} artigos positivos")
    return articles

# ── MAIN ─────────────────────────────────────────────────

def main():
    print("🚀 A iniciar fetch de notícias positivas...")
    all_articles = []
    seen_urls = set()

    for feed_url, source, default_cat, is_english in FEEDS:
        print(f"\n📡 {source} — {feed_url[:60]}...")
        articles = fetch_feed(feed_url, source, default_cat, is_english)
        for a in articles:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                all_articles.append(a)
        time.sleep(0.5)

    all_articles.sort(key=lambda x: x["score"], reverse=True)
    final = all_articles[:MAX_NEWS]

    output = {
        "last_update": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "total":       len(final),
        "news":        final,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✨ noticias.json gerado com {len(final)} notícias positivas!")
    if final:
        print(f"   Score médio: {sum(a['score'] for a in final)/len(final):.2f}")

if __name__ == "__main__":
    main()
