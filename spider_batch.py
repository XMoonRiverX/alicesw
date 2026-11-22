"""
Alice Library Novel Spider - Batch Downloader v2.0
Save as a single file or a separate file for each chapter
"""
import requests
from bs4 import BeautifulSoup
from novel_metadata import extract_novel_metadata, format_novel_metadata, parse_search_result
import urllib.parse
import time
import re
import os
import sys
from urllib.parse import urlparse

# Get the application directory
if getattr(sys, 'frozen', False):
    # Running as a packaged executable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running from source
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
                    novels.append(novel)
            
            return novels
        except Exception as e:
            print(f"Error searching for novels: {e}")
            return []

    def get_novel_chapters(self, novel_url):
        """Retrieve all chapters of a novel"""
        try:
            novel_id_match = re.search(r'/novel/(\d+)\.html', novel_url)
            if novel_id_match:
                novel_id = novel_id_match.group(1)
                chapters_url = f"{self.base_url}/other/chapters/id/{novel_id}.html"
            else:
                chapters_url = novel_url

            response = self.session.get(chapters_url)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            chapter_links = []
            chapter_elements = soup.select('.mulu_list li a')
            
            for elem in chapter_elements:
                title = elem.get_text(strip=True)
                url = urllib.parse.urljoin(self.base_url, elem.get('href'))
                chapter_links.append({
                    'title': title,
                    'url': url
                })
            
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

            content_div = soup.find('div', class_='read-content')
            if not content_div:
                content_div = soup.find('div', {'class': re.compile(r'.*read.*content.*')})
            
            if content_div:
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
            print(f"Found {len(chapters)} chapters")
            
            novel_content = {
                **novel_metadata,
                'title': novel_title,
                'author': novel_author,
                'url': novel_url,
                'chapters': []
            }
            
            for i, chapter in enumerate(chapters):
                print(f"Retrieving chapter: {chapter['title']} ({i+1}/{len(chapters)})")
                content = self.get_chapter_content(chapter['url'])
                novel_content['chapters'].append({
                    'title': chapter['title'],
                    'content': content
                })
                
                time.sleep(0.2)
            
            return novel_content
        except Exception as e:
            print(f"Error retrieving novel content: {e}")
            return {}

    def download_multiple_novels(self, novels_list, save_format="single"):
        """Download novels in batches"""
        downloaded_novels = []
        
        # Use an absolute path
        download_dir = os.path.join(BASE_DIR, "downloads")
        print(f"Download directory: {download_dir}")
        
        for i, novel in enumerate(novels_list):
            print(f"\nDownloading novel {i+1}/{len(novels_list)}: {novel['title']}")
            novel_data = self.get_novel_content_by_url(
                novel['url'], novel['title'], novel['author'], metadata=novel
            )
            
            if novel_data and novel_data.get('chapters'):
                print(f"Retrieved novel content with {len(novel_data['chapters'])} chapters")
                downloaded_novels.append(novel_data)
                self.save_novel_to_file(novel_data, download_dir, save_format)
                print(f"Downloaded: {novel_data['title']}")
            else:
                print(f"Download failed: {novel['title']} - No chapter content retrieved")
        
        print(f"\nDownloaded {len(downloaded_novels)}/{len(novels_list)} novels in this session")
        return downloaded_novels

    def save_novel_to_file(self, novel_data, download_dir="downloads", save_format="single"):
        """
        Save a novel to a file
        :param novel_data: Novel data
        :param download_dir: Download directory
        :param save_format: Save format ('single' for one file, 'chapter' for one file per chapter)
        """
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # Remove invalid filename characters
        clean_title = "".join(c for c in novel_data['title'] if c.isalnum() or c in (' ', '-', '_', '.', '(', ')', '[', ']')).rstrip()
        # Remove any remaining invalid characters
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            clean_title = clean_title.replace(char, '_')
        
        # Limit the folder name length (Windows allows up to 255 characters)
        if len(clean_title) > 100:
            clean_title = clean_title[:100]
        
        if not clean_title:
            clean_title = "Unknown Novel"
        
        if save_format == "single":
            filename = os.path.join(download_dir, f"{clean_title}.txt")
            
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
        
        elif save_format == "chapter":
            novel_folder = os.path.join(download_dir, clean_title)
            try:
                if not os.path.exists(novel_folder):
                    os.makedirs(novel_folder)
            except Exception as e:
                print(f"Failed to create novel directory: {e}")
                # Use a fallback name with only basic identifiers
                import hashlib
                hash_obj = hashlib.md5(novel_data['title'].encode('utf-8'))
                backup_title = f"novel_{hash_obj.hexdigest()[:8]}"
                novel_folder = os.path.join(download_dir, backup_title)
                if not os.path.exists(novel_folder):
                    os.makedirs(novel_folder)
                print(f"Using fallback directory: {novel_folder}")
            
            # Save novel metadata
            info_file = os.path.join(novel_folder, "novel_info.txt")
            try:
                with open(info_file, 'w', encoding='utf-8') as f:
                    f.write(f"Novel title: {novel_data['title']}\n")
                    f.write(f"Author: {novel_data['author']}\n")
                    f.write(f"Chapters: {len(novel_data['chapters'])}\n")
                    f.write(format_novel_metadata(novel_data))
            except Exception as e:
                print(f"Error saving novel metadata: {e}")
                return
            
            # Save each chapter
            for i, chapter in enumerate(novel_data['chapters'], 1):
                clean_chapter_title = "".join(c for c in chapter['title'] if c.isalnum() or c in (' ', '-', '_', '.', '(', ')', '[', ']')).rstrip()
                # Remove invalid chapter title characters
                for char in illegal_chars:
                    clean_chapter_title = clean_chapter_title.replace(char, '_')
                
                # Limit the chapter title length
                if len(clean_chapter_title) > 50:
                    clean_chapter_title = clean_chapter_title[:50]
                
                if not clean_chapter_title:
                    clean_chapter_title = f"Chapter_{i}"
                
                chapter_file = os.path.join(novel_folder, f"{i:03d}_{clean_chapter_title}.txt")
                
                try:
                    with open(chapter_file, 'w', encoding='utf-8') as f:
                        f.write(f"Chapter {i}: {chapter['title']}\n")
                        f.write("-"*30 + "\n")
                        f.write(f"{chapter['content']}\n")
                except Exception as e:
                    print(f"Error saving chapter {i}: {e}")
                
                if (i + 1) % 10 == 0 or i == len(novel_data['chapters']):
                    print(f"Saved {i}/{len(novel_data['chapters'])} chapters")
            
            print(f"Novel saved to directory: {novel_folder}")


def main():
    print("Alice Library Novel Spider - Batch Downloader v2.0")
    print("="*50)
    
    spider = NovelSpider()
    
    while True:
        print("\nChoose an action:")
        print("1. Search for novels and choose downloads")
        print("2. Exit")
        
        choice = input("\nEnter an option (1-2): ").strip()
        
        if choice == '1':
            print("\nSearch type:")
            print("1. Search by title")
            print("2. Search by author")
            print("3. Search by tag")
            print("4. Keyword search")
            
            search_choice = input("\nChoose a search type (1-4): ").strip()
            search_types = {'1': 'title', '2': 'author', '3': 'tag', '4': '_all'}
            search_type = search_types.get(search_choice, '_all')
            
            keyword = input("\nEnter a search keyword: ").strip()
            
            if not keyword:
                print("Keyword must not be empty!")
                continue
            
            print("\nSearching...")
            novels = spider.search_novels(keyword, search_type)
            
            if not novels:
                print("No matching novels found!")
                continue
            
            print(f"\nFound {len(novels)} matching novels:")
            for i, novel in enumerate(novels, 1):
                print(f"{i}. {novel['title']} - Author: {novel['author']}")
                print(f"   Synopsis: {novel['intro'][:100]}{'...' if len(novel['intro']) > 100 else ''}")
                print()
            
            print("Choose a download method:")
            print("1. Download novels by result number")
            print("2. Download the first N novels")
            print("3. Download all novels")
            
            download_choice = input("\nChoose a download method (1-3): ").strip()
            
            novels_to_download = []
            
            if download_choice == '1':
                while True:
                    print("\nEnter novel numbers separated by commas (for example: 1,3,5): ")
                    selected_nums = input().strip()
                    try:
                        nums = [int(n.strip()) - 1 for n in selected_nums.replace('，', ',').split(',') if n.strip()]
                        novels_to_download = [novels[i] for i in nums if 0 <= i < len(novels)]
                        if not novels_to_download:
                            print("No valid numbers selected. Please try again!")
                            continue
                        break
                    except ValueError:
                        print("Invalid input format. Please try again!")
                        continue
            
            elif download_choice == '2':
                while True:
                    try:
                        n = int(input(f"\nHow many novels should be downloaded (1-{len(novels)})? "))
                        if 1 <= n <= len(novels):
                            novels_to_download = novels[:n]
                            break
                        else:
                            print(f"Enter a number between 1 and {len(novels)}!")
                    except ValueError:
                        print("Please enter a valid number!")
            
            elif download_choice == '3':
                novels_to_download = novels[:]
            
            else:
                print("Invalid selection!")
                continue
            
            if not novels_to_download:
                print("No novels selected!")
                continue
            
            print(f"\nSelected {len(novels_to_download)} novels for download:")
            for novel in novels_to_download:
                print(f"- {novel['title']} - Author: {novel['author']}")
            
            # Choose the save format
            print("\nChoose a save format:")
            print("1. Single-file mode (save the entire novel as one TXT file)")
            print("2. Chapter mode (save each chapter as a TXT file in a novel directory)")
            
            format_choice = input("\nChoose a save format (1-2): ").strip()
            save_format = "single" if format_choice == '1' else "chapter"
            
            print("\nStarting downloads...")
            spider.download_multiple_novels(novels_to_download, save_format)
            
            print(f"\nDownload complete!")
            print(f"Files saved in: {os.path.join(BASE_DIR, 'downloads')}")
            
            continue_choice = input("\nContinue? (y/n): ").strip().lower()
            if continue_choice != 'y':
                break
                
        elif choice == '2':
            print("\nThanks for using Novel Spider. Goodbye!")
            break
        else:
            print("Invalid option. Please choose again!")


if __name__ == "__main__":
    main()
