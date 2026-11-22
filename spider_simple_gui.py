"""
Alice Library Novel Spider - Simple GUI
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from bs4 import BeautifulSoup
from novel_metadata import extract_novel_metadata, format_novel_metadata, parse_search_result
import urllib.parse
import time
import re
import os
import threading
from urllib.parse import urlparse
import webbrowser


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


class NovelSpiderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Alice Library Novel Spider - Simple Edition")
        self.root.geometry("800x600")
        
        self.spider = NovelSpider()
        self.downloaded_files = []  # Track downloaded files
        
        # Build the interface
        self.create_widgets()
    
    def create_widgets(self):
        # Search panel
        search_frame = ttk.Frame(self.root)
        search_frame.pack(pady=10, padx=10, fill=tk.X)
        
        ttk.Label(search_frame, text="Search keyword:").pack(side=tk.LEFT)
        
        self.keyword_entry = ttk.Entry(search_frame, width=30)
        self.keyword_entry.pack(side=tk.LEFT, padx=5)
        self.keyword_entry.bind('<Return>', lambda event: self.search_novels())
        
        ttk.Label(search_frame, text="Search type:").pack(side=tk.LEFT, padx=(20, 5))
        
        self.search_type_var = tk.StringVar(value="Keyword search")
        search_type_combo = ttk.Combobox(
            search_frame, 
            textvariable=self.search_type_var,
            values=["Title", "Author", "Tag", "Keyword search"],
            state="readonly",
            width=18
        )
        search_type_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="Search", command=self.search_novels).pack(side=tk.LEFT, padx=5)
        
        # Results panel
        result_frame = ttk.Frame(self.root)
        result_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # Create a tree view for search results
        columns = ('No.', 'Title', 'Author', 'Synopsis')
        self.tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Button panel
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10, padx=10, fill=tk.X)
        
        ttk.Button(button_frame, text="Download Selected", command=self.download_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Download All", command=self.download_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Manage Downloads", command=self.manage_downloads).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode='determinate')
        self.progress.pack(pady=5, padx=10, fill=tk.X)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def search_novels(self):
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("Warning", "Please enter a search keyword")
            return
        
        # Map search types
        type_map = {"Title": "title", "Author": "author", "Tag": "tag", "Keyword search": "_all"}
        search_type = type_map.get(self.search_type_var.get(), "_all")
        
        self.status_var.set("Searching...")
        self.root.update()
        
        try:
            # Clear existing results
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            novels = self.spider.search_novels(keyword, search_type)
            
            for i, novel in enumerate(novels, 1):
                self.tree.insert('', 'end', values=(i, novel['title'], novel['author'], novel['intro']))
            
            self.status_var.set(f"Search complete: found {len(novels)} novels")
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {str(e)}")
            self.status_var.set("Search failed")
    
    def download_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select novels to download first")
            return
        
        novels_to_download = []
        for item in selected_items:
            values = self.tree.item(item, 'values')
            # Build a placeholder novel object; search again to retrieve its URL
            keyword = self.keyword_entry.get().strip()
            type_map = {"Title": "title", "Author": "author", "Tag": "tag", "Keyword search": "_all"}
            search_type = type_map.get(self.search_type_var.get(), "_all")
            
            novels = self.spider.search_novels(keyword, search_type)
            # Find the novel matching the result number
            idx = int(values[0]) - 1
            if 0 <= idx < len(novels):
                novels_to_download.append(novels[idx])
        
        if novels_to_download:
            self.download_novels_thread(novels_to_download)
    
    def download_all(self):
        all_items = self.tree.get_children()
        if not all_items:
            messagebox.showwarning("Warning", "No novels available to download")
            return
        
        novels_to_download = []
        keyword = self.keyword_entry.get().strip()
        type_map = {"Title": "title", "Author": "author", "Tag": "tag", "Keyword search": "_all"}
        search_type = type_map.get(self.search_type_var.get(), "_all")
        
        novels = self.spider.search_novels(keyword, search_type)
        
        novels_to_download = novels
        
        if novels_to_download:
            self.download_novels_thread(novels_to_download)
    
    def download_novels_thread(self, novels_list):
        thread = threading.Thread(target=self.download_novels, args=(novels_list,))
        thread.daemon = True
        thread.start()
    
    def download_novels(self, novels_list):
        try:
            total = len(novels_list)
            self.progress['maximum'] = total
            self.progress['value'] = 0
            
            for i, novel in enumerate(novels_list):
                self.status_var.set(f"Downloading novel {i+1}/{total}: {novel['title']}")
                self.root.update()
                
                novel_data = self.spider.get_novel_content_by_url(
                    novel['url'], novel['title'], novel['author'], metadata=novel
                )
                
                if novel_data:
                    # Get the system Downloads directory
                    download_path = os.path.join(os.path.expanduser("~"), "Downloads")
                    if not os.path.exists(download_path):
                        download_path = os.path.join(os.path.expanduser("~"), "Download")
                        if not os.path.exists(download_path):
                            download_path = os.getcwd()  # Fall back to the current directory
                    
                    # Save the file
                    clean_title = "".join(c for c in novel_data['title'] if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                    if not clean_title:
                        clean_title = "Unknown Novel"
                    
                    filename = os.path.join(download_path, f"{clean_title}.txt")
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"Novel title: {novel_data['title']}\n")
                        f.write(f"Author: {novel_data['author']}\n")
                        f.write(f"URL: {novel_data['url']}\n")
                        f.write(format_novel_metadata(novel_data))
                        f.write("="*50 + "\n\n")
                        
                        for chapter_number, chapter in enumerate(novel_data['chapters'], start=1):
                            f.write(f"Chapter {chapter_number}: {chapter['title']}\n")
                            f.write("-"*30 + "\n")
                            f.write(f"{chapter['content']}\n\n")
                    
                    self.downloaded_files.append(filename)
                
                self.progress['value'] = i + 1
                self.root.update()
            
            self.status_var.set(f"Download complete! Downloaded {len(novels_list)} novels")
            messagebox.showinfo("Complete", f"Download complete!\nDownloaded {len(novels_list)} novels\nSaved in the system Downloads directory")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error during download: {str(e)}")
        finally:
            self.progress['value'] = 0
    
    def manage_downloads(self):
        if not self.downloaded_files:
            messagebox.showinfo("Information", "No download history yet")
            return
        
        # Create the download manager window
        manage_window = tk.Toplevel(self.root)
        manage_window.title("Download Manager")
        manage_window.geometry("600x400")
        
        # Create a list box for downloaded files
        listbox_frame = ttk.Frame(manage_window)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        listbox = tk.Listbox(listbox_frame)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        for file in self.downloaded_files:
            listbox.insert(tk.END, os.path.basename(file))
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        btn_frame = ttk.Frame(manage_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        def open_file():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a file to open")
                return
            idx = selection[0]
            filepath = self.downloaded_files[idx]
            os.startfile(filepath)
        
        def copy_path():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a file to copy its path")
                return
            idx = selection[0]
            filepath = self.downloaded_files[idx]
            self.root.clipboard_clear()
            self.root.clipboard_append(filepath)
            messagebox.showinfo("Information", "Path copied to the clipboard")
        
        def online_view():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a file to view")
                return
            idx = selection[0]
            filepath = self.downloaded_files[idx]
            # View the downloaded file locally
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create the text viewer window
            viewer = tk.Toplevel(self.root)
            viewer.title(f"View Text - {os.path.basename(filepath)}")
            viewer.geometry("700x500")
            
            text_frame = ttk.Frame(viewer)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD)
            scrollbar_v = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar_h = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
            text_widget.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
            
            text_widget.insert(tk.END, content)
            text_widget.config(state=tk.DISABLED)  # Set to read-only
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
            scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(btn_frame, text="Open File", command=open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Copy Path", command=copy_path).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="View Text", command=online_view).pack(side=tk.LEFT, padx=5)


def main():
    root = tk.Tk()
    app = NovelSpiderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
