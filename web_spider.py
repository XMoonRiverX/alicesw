"""
Alice Library Novel Spider - Web Edition
"""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, send_from_directory
import requests
from bs4 import BeautifulSoup
from novel_metadata import extract_novel_metadata, format_novel_metadata, parse_search_result
import urllib.parse
import time
import re
import os
import threading
from urllib.parse import urlparse
import json
from io import BytesIO
import zipfile

app = Flask(__name__)

class NovelSpider:
    def __init__(self):
        self.base_url = "https://www.alicesw.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

    def search_novels(self, keyword, search_type='_all'):
        """Search for novels"""
        if search_type == 'tag':
            search_url = f"{self.base_url}/search.html?q={urllib.parse.quote(keyword)}&f=tag"
        elif search_type == 'author':
            search_url = f"{self.base_url}/search.html?q={urllib.parse.quote(keyword)}&f=author"
        else:
            search_url = f"{self.base_url}/search.html?q={urllib.parse.quote(keyword)}&f=_all"

        try:
            response = self.session.get(search_url)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            novels = []
            list_items = soup.find_all('div', class_='list-group-item')
            
            for item in list_items:
                novel = parse_search_result(item, self.base_url)
                if novel:
                    novel['id'] = len(novels) + 1
                    novels.append(novel)
            
            return novels
        except Exception as e:
            print(f"Error searching for novels: {e}")
            return []

    def get_novel_chapters(self, novel_url):
        """Retrieve all chapters of a novel"""
        try:
            # Extract the novel ID from novel_url
            novel_id_match = re.search(r'/novel/(\d+)\.html', novel_url)
            if novel_id_match:
                novel_id = novel_id_match.group(1)
                # Use the chapter-list page URL
                chapters_url = f"{self.base_url}/other/chapters/id/{novel_id}.html"
            else:
                # Use the original URL if the ID cannot be extracted
                chapters_url = novel_url

            response = self.session.get(chapters_url)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            # Retrieve all chapters using the chapter-list page selector
            chapter_links = []
            chapter_elements = soup.select('.mulu_list li a')
            
            for elem in chapter_elements:
                title = elem.get_text(strip=True)
                url = urllib.parse.urljoin(self.base_url, elem.get('href'))
                chapter_links.append({
                    'title': title,
                    'url': url
                })
            
            # Fall back to the original novel page if the chapter-list page has no chapters
            if not chapter_links:
                response = self.session.get(novel_url)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                chapter_elements = soup.select('.mulu_list li a')
                for elem in chapter_elements:
                    title = elem.get_text(strip=True)
                    url = urllib.parse.urljoin(self.base_url, elem.get('href'))
                    chapter_links.append({
                        'title': title,
                        'url': url
                    })
            
            return chapter_links
        except Exception as e:
            print(f"Error retrieving chapters: {e}")
            return []

    def get_chapter_content(self, chapter_url):
        """Retrieve chapter content"""
        try:
            response = self.session.get(chapter_url)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the content container
            content_div = soup.find('div', class_='read-content')
            if not content_div:
                # Try alternative selectors
                content_div = soup.find('div', {'class': re.compile(r'.*read.*content.*')})
            
            if content_div:
                # Clean up the content by removing unwanted tags
                for unwanted in content_div(["script", "style", "div.ad", "p.ad", "span.ad"]):
                    unwanted.decompose()
                
                content = content_div.get_text(separator='\n', strip=True)
                return content
            else:
                return "Chapter content not found"
        except Exception as e:
            print(f"Error retrieving chapter content: {e}")
            return ""

    def get_novel_content_by_url(self, novel_url, novel_title=None, novel_author=None, metadata=None):
        """Retrieve novel content by URL"""
        try:
            novel_metadata = dict(metadata or {})
            novel_title = novel_title or novel_metadata.get('title')
            novel_author = novel_author or novel_metadata.get('author')
            if metadata is None or not novel_title or not novel_author:
                response = self.session.get(novel_url)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                for key, value in extract_novel_metadata(soup).items():
                    if not novel_metadata.get(key):
                        novel_metadata[key] = value

                if not novel_title:
                    title_elem = soup.find('div', class_='novel_title')
                    novel_title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

                if not novel_author:
                    novel_author = novel_metadata.get('author') or "Unknown Author"
            chapters = self.get_novel_chapters(novel_url)
            
            # Retrieve content for each chapter
            novel_content = {
                **novel_metadata,
                'title': novel_title,
                'author': novel_author,
                'url': novel_url,
                'chapters': []
            }
            
            for i, chapter in enumerate(chapters):
                content = self.get_chapter_content(chapter['url'])
                novel_content['chapters'].append({
                    'title': chapter['title'],
                    'content': content
                })
                
                # Add a delay to avoid sending requests too quickly
                time.sleep(0.2)
            
            return novel_content
        except Exception as e:
            print(f"Error retrieving novel content: {e}")
            return {}


# Global crawler instance
spider = NovelSpider()


@app.route('/')
def index():
    return render_template('index.html')


# Static file routes
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('.', 'manifest.json')


@app.route('/service-worker.js')
def serve_service_worker():
    return send_from_directory('.', 'service-worker.js')


@app.route('/icons/<path:filename>')
def serve_icon(filename):
    return send_from_directory('icons', filename)


@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    keyword = data.get('keyword', '')
    search_type = data.get('search_type', '_all')
    
    if not keyword:
        return jsonify({'error': 'Keyword must not be empty'}), 400
    
    novels = spider.search_novels(keyword, search_type)
    return jsonify({'novels': novels})


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    novel_ids = data.get('novel_ids', [])
    
    if not novel_ids:
        return jsonify({'error': 'Please select novels to download'}), 400
    
    # Resolve novel URLs from IDs here; adapt this to the actual data source
    # Assume URLs are passed directly for now
    novel_urls = data.get('novel_urls', [])
    novel_titles = data.get('novel_titles', [])
    novel_authors = data.get('novel_authors', [])
    novel_metadata = data.get('novel_metadata', [])
    
    # Create an in-memory ZIP archive
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, url in enumerate(novel_urls):
            if i < len(novel_titles) and i < len(novel_authors):
                title = novel_titles[i]
                author = novel_authors[i]
                
                metadata = novel_metadata[i] if i < len(novel_metadata) else None
                novel_data = spider.get_novel_content_by_url(url, title, author, metadata=metadata)
                
                if novel_data:
                    # Generate the file contents
                    content = f"Novel title: {novel_data['title']}\n"
                    content += f"Author: {novel_data['author']}\n"
                    content += f"URL: {novel_data['url']}\n"
                    content += format_novel_metadata(novel_data)
                    content += "="*50 + "\n\n"
                    
                    for chapter_number, chapter in enumerate(novel_data['chapters'], start=1):
                        content += f"Chapter {chapter_number}: {chapter['title']}\n"
                        content += "-"*30 + "\n"
                        content += f"{chapter['content']}\n\n"
                    
                    # Add to the ZIP archive
                    clean_title = "".join(c for c in novel_data['title'] if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                    if not clean_title:
                        clean_title = "Unknown Novel"
                    
                    filename = f"{clean_title}.txt"
                    zip_file.writestr(filename, content)
    
    zip_buffer.seek(0)
    
    # Return the ZIP archive
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='novels.zip'
    )


if __name__ == '__main__':
    # Create the templates directory
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
