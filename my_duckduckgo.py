"""
DuckDuckGo検索機能のモジュール
最新のduckduckgo-searchパッケージ(v8.0.1)に対応
検索結果のURLからコンテンツを取得する機能も提供
"""

# Webスクレイピングモジュールをインポート

try:
    from web_scraper import scrape_url, scrape_multiple_urls
    SCRAPING_AVAILABLE = True
except ImportError:
    print("[WARNING] web_scraper module not available. URL content extraction will be disabled.")
    SCRAPING_AVAILABLE = False

def duckduckgo_search(query: str):
    """
    DuckDuckGo公式HTMLを直接パースして検索結果（タイトル・スニペット・URL）最大5件を返す超シンプルな関数。
    例: [{'title': ..., 'body': ..., 'href': ...}, ...]
    エラー時は空リスト。
    """
    print('duckduckgo_search called')
    import requests
    from bs4 import BeautifulSoup
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = {"q": query}
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result"):
            title_tag = r.select_one("a.result__a")
            snippet_tag = r.select_one(".result__snippet")
            href = title_tag["href"] if title_tag and title_tag.has_attr("href") else None
            title = title_tag.get_text(strip=True) if title_tag else None
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if title and href:
                results.append({"title": title, "body": snippet, "href": href})
            if len(results) >= 5:
                break
        print(f"[DEBUG] DuckDuckGo parsed results for query '{query}': {results}")
        return results
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] duckduckgo_search exception: {e}\n{tb}")
        return []

def extract_content_from_urls(search_results, max_urls=2, max_length_per_url=2000):
    """
    検索結果のURLからコンテンツを取得します。
    
    Args:
        search_results (list): duckduckgo_searchの結果リスト
        max_urls (int): 処理するURLの最大数
        max_length_per_url (int): URLごとの最大文字数
        
    Returns:
        list: 抽出されたコンテンツを含む検索結果のリスト
    """
    if not SCRAPING_AVAILABLE:
        print("[ERROR] Web scraping is not available")
        return search_results
    
    # エラーチェック
    if not search_results or isinstance(search_results, list) and 'error' in search_results[0]:
        return search_results
    
    # URLを取得
    urls = [result['href'] for result in search_results if 'href' in result][:max_urls]
    
    if not urls:
        return search_results
    
    try:
        # URLからコンテンツを取得
        scraped_results = scrape_multiple_urls(urls, max_urls=max_urls, max_length_per_url=max_length_per_url)
        
        # 検索結果にコンテンツを追加
        for i, scraped in enumerate(scraped_results):
            if i < len(search_results):
                url = scraped['url']
                # 対応するURLを探す
                for j, result in enumerate(search_results):
                    if result.get('href') == url:
                        # コンテンツを追加
                        search_results[j]['content'] = scraped['text'] if scraped['success'] else ''
                        break
        
        return search_results
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] extract_content_from_urls exception: {e}\n{tb}")
        return search_results  # エラー時は元の検索結果をそのまま返す
