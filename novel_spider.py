import requests
from bs4 import BeautifulSoup
from novel_metadata import format_novel_metadata, parse_search_result
import urllib.parse
import time
import re


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
        """
        Search for novels
        :param keyword: Search keyword
        :param search_type: Search type ('title', 'author', 'tag', '_all')
        :return: Novel records with full descriptions, metadata, tags, and timestamps
        """
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
                    novels.append(novel)
            
            return novels
        except Exception as e:
            print(f"Error searching for novels: {e}")
            return []

    def get_novel_chapters(self, novel_url):
        """
        Retrieve all chapters of a novel
        :param novel_url: Novel detail page URL
        :return: List of chapters [{'title': '', 'url': ''}]
        """
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
        """
        Retrieve chapter content
        :param chapter_url: Chapter URL
        :return: Chapter content
        """
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

    def get_novel_content_by_search(self, keyword, search_type='_all'):
        """
        Retrieve novel content by searching
        :param keyword: Search keyword
        :param search_type: Search type
        :return: Dictionary containing novel metadata and content
        """
        print(f"Searching for keyword: {keyword}")
        novels = self.search_novels(keyword, search_type)
        
        if not novels:
            print("No matching novels found")
            return {}
        
        # Use the first result
        novel = novels[0]
        print(f"Found novel: {novel['title']}, Author: {novel['author']}")
        
        # Retrieve chapters
        chapters = self.get_novel_chapters(novel['url'])
        print(f"Found {len(chapters)} chapters")
        
        # Retrieve content for each chapter
        novel_content = {
            **novel,
            'chapters': []
        }
        
        for i, chapter in enumerate(chapters):
            print(f"Retrieving chapter: {chapter['title']} ({i+1}/{len(chapters)})")
            content = self.get_chapter_content(chapter['url'])
            novel_content['chapters'].append({
                'title': chapter['title'],
                'content': content
            })
            
            # Add a delay to avoid sending requests too quickly
            time.sleep(1)
        
        return novel_content

    def save_novel_to_file(self, novel_data, filename=None):
        """
        Save a novel to a file
        :param novel_data: Novel data
        :param filename: Filename
        """
        if not filename:
            filename = f"{novel_data['title']}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Novel title: {novel_data['title']}\n")
            f.write(f"Author: {novel_data['author']}\n")
            f.write(format_novel_metadata(novel_data))
            f.write("="*50 + "\n\n")
            for chapter_number, chapter in enumerate(novel_data['chapters'], start=1):
                f.write(f"Chapter {chapter_number}: {chapter['title']}\n")
                f.write("-"*30 + "\n")
                f.write(f"{chapter['content']}\n\n")
        
        print(f"Novel saved to: {filename}")


def main():
    spider = NovelSpider()
    
    print("Welcome to Novel Spider")
    print("1. Search by title")
    print("2. Search by author")
    print("3. Search by tag")
    print("4. Keyword search")
    
    choice = input("Choose a search type (1-4): ").strip()
    search_types = {'1': 'title', '2': 'author', '3': 'tag', '4': '_all'}
    search_type = search_types.get(choice, '_all')
    
    keyword = input("Enter a search keyword: ").strip()
    
    if not keyword:
        print("Keyword must not be empty")
        return
    
    print("\nRetrieving novel content...")
    novel_data = spider.get_novel_content_by_search(keyword, search_type)
    
    if novel_data:
        print(f"\nRetrieved novel: {novel_data['title']}")
        print(f"Chapters: {len(novel_data['chapters'])}")
        
        save_choice = input("\nSave to a file? (y/n): ").strip().lower()
        if save_choice == 'y':
            filename = input("Enter a filename (default: novel title.txt): ").strip()
            if not filename:
                filename = None
            spider.save_novel_to_file(novel_data, filename)

    else:
        print("Could not retrieve novel content")


if __name__ == "__main__":
    main()
