"""
Webスクレイピング機能を提供するモジュール
検索結果のURLからコンテンツを取得し、テキストを抽出します。
"""

import requests
import logging
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urlparse

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ユーザーエージェントの設定
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

def scrape_url(url, max_length=3000):
    """
    URLからテキストコンテンツをスクレイピングします。
    
    Args:
        url (str): スクレイピングするURL
        max_length (int): 返すテキストの最大文字数
        
    Returns:
        dict: {
            'title': ページタイトル,
            'text': 抽出されたテキスト,
            'url': 元のURL,
            'success': 成功したかどうか,
            'error': エラーメッセージ(失敗時)
        }
    """
    result = {
        'title': '',
        'text': '',
        'url': url,
        'success': False,
        'error': None
    }
    
    try:
        # URLのドメインを確認
        domain = urlparse(url).netloc
        logger.info(f"Scraping URL: {url} (domain: {domain})")
        
        # trafilaturaを使用してコンテンツを取得
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            # メインコンテンツを抽出
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            if text:
                result['text'] = text[:max_length]
                result['success'] = True
                
                # タイトルを取得するためにBeautifulSoupも使用
                soup = BeautifulSoup(downloaded, 'lxml')
                title_tag = soup.find('title')
                if title_tag:
                    result['title'] = title_tag.text.strip()
                return result
        
        # trafilaturaが失敗した場合は、通常のRequests + BeautifulSoupを使用
        logger.info(f"Trafilatura failed, trying with BeautifulSoup for {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # タイトルを取得
        title_tag = soup.find('title')
        if title_tag:
            result['title'] = title_tag.text.strip()
        
        # メタ説明を取得
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'] if meta_desc and 'content' in meta_desc.attrs else ''
        
        # 本文コンテンツを取得
        # 一般的なコンテンツエリアを探す
        content_tags = []
        for tag in ['article', 'main', 'div[role="main"]', '.content', '#content', '.main', '#main']:
            if tag.startswith('.'):
                elements = soup.select(tag)
            elif tag.startswith('#'):
                elements = soup.select(tag)
            else:
                elements = soup.find_all(tag)
            content_tags.extend(elements)
        
        # コンテンツが見つからない場合は、body全体を使用
        if not content_tags and soup.body:
            content_tags = [soup.body]
        
        # テキストを抽出
        texts = []
        for tag in content_tags:
            # 不要な要素を除外
            for s in tag.select('script, style, nav, footer, header, aside'):
                s.extract()
            
            # テキストを取得
            text = tag.get_text(separator='\n', strip=True)
            if text:
                texts.append(text)
        
        # 結果を結合
        if description:
            texts.insert(0, description)
        
        combined_text = '\n\n'.join(texts)
        result['text'] = combined_text[:max_length]
        result['success'] = True if combined_text else False
        
        if not result['success']:
            result['error'] = "コンテンツを抽出できませんでした"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {str(e)}")
        result['error'] = f"リクエストエラー: {str(e)}"
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        result['error'] = f"スクレイピングエラー: {str(e)}"
    
    return result


def scrape_multiple_urls(urls, max_urls=3, max_length_per_url=2000):
    """
    複数のURLをスクレイピングし、結果を結合します。
    
    Args:
        urls (list): スクレイピングするURLのリスト
        max_urls (int): 処理するURLの最大数
        max_length_per_url (int): URLごとの最大文字数
        
    Returns:
        list: スクレイピング結果のリスト
    """
    results = []
    
    # 最大URL数を制限
    urls = urls[:max_urls]
    
    for url in urls:
        result = scrape_url(url, max_length=max_length_per_url)
        results.append(result)
    
    return results


# テスト用コード
if __name__ == "__main__":
    test_url = "https://news.yahoo.co.jp/"
    result = scrape_url(test_url)
    if result['success']:
        print(f"Title: {result['title']}")
        print(f"Content length: {len(result['text'])} characters")
        print(f"Preview: {result['text'][:200]}...")
    else:
        print(f"Error: {result['error']}")
