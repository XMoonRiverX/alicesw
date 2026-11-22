# Alice's Library Novel Downloader

A Python toolkit for searching and downloading novels from Alice's Library (ALICESW.COM), with command-line, desktop GUI, web, and Chrome extension interfaces.

The source interfaces and documentation are in English. Novel titles, author names, search keywords, and downloaded chapter content remain in their original language. Website-specific selectors and parsing patterns are also preserved.

## Features

- Search by title, author, tag, or keyword.
- Retrieve chapter lists and extract chapter text.
- Download selected novels or an entire set of search results using the batch interface.
- Save an entire novel to one text file or save each chapter separately.
- Use the desktop GUI to search, download, and manage downloaded files.

## Requirements

- Python 3
- `requests`
- `beautifulsoup4`
- `lxml`
- `flask` (web interface only)
- Tkinter (desktop GUI only; included with many Python installations)

```bash
pip install requests beautifulsoup4 lxml
```

For the web interface, also install Flask:

```bash
pip install flask
```

## Usage

### Interactive command line

```bash
python novel_spider.py
```

Choose a search type and enter a keyword when prompted. Search keywords must match the website's content, which is primarily Chinese.

### Batch downloads

```bash
python spider_batch.py
```

Search for novels, choose which results to download, and select either a single text file per novel or a separate file for each chapter. Files are saved under `downloads` next to the script.

### Download by URL

```bash
python download_by_url.py "https://www.alicesw.com/novel/123.html"
python download_by_url.py "https://www.alicesw.com/novel/123.html" --format chapter
```

Replace the example URL with an actual novel or chapter-list URL. Use `--title` or `--author` to override the detected metadata.

### Desktop GUI

```bash
python spider_simple_gui.py
```

### Web interface

```bash
python web_spider.py
```

The web interface expects `templates/index.html` and supporting assets, which are not included in this checkout. Likewise, the Chrome extension references a `popup.html` file that is not included. See [the extension README](novel-spider-extension/README.md) for details.

### Prebuilt applications

The `dist` directory contains the original Windows executable (`小说爬虫工具_批量版.exe`) and Android package (`app-debug.apk`). These existing binaries have not been rebuilt or translated; run the Python scripts to use the English interfaces.

### Python API

```python
from novel_spider import NovelSpider

spider = NovelSpider()

novels = spider.search_novels("example", "_all")
print(f"Found {len(novels)} novels")

if novels:
    chapters = spider.get_novel_chapters(novels[0]["url"])
    print(f"Found {len(chapters)} chapters")

    if chapters:
        content = spider.get_chapter_content(chapters[0]["url"])
        print(f"Content length: {len(content)} characters")
```

Replace `example` with a keyword found on the website.

## Search Result Metadata

All Python search interfaces return the following fields for each novel:

| Field | HTML source / meaning |
| --- | --- |
| `title` | Text of the title link inside `h5` |
| `url` | Absolute URL of that title link |
| `author` | Link with the query parameter `f=author` |
| `intro` | Full text of `.content-txt`, without the previous 100-character limit |
| `status` | Muted status inside the heading, without surrounding brackets |
| `word_count` | Value labeled `字數` or `字数` in muted text |
| `views` | Value labeled `瀏覽` or `浏览` in muted text |
| `tags` | Tag names from links with `f=tag`, without leading `#` |
| `text_muted` | List of normalized text from every `.text-muted` element |
| `published_at` | Publication time labeled `發布時間` or `发布时间` in `.timedesc` |
| `updated_at` | Latest update time labeled `更新時間` or `更新时间` in `.timedesc` |

Missing text fields are empty strings; missing lists are empty lists. Counts retain their original units (for example, `496.10萬`), and timestamps retain the website's displayed format without assuming a timezone.

Search-based CLI and GUI downloads preserve this metadata. New text exports and `novel_info.txt` files include the description, status, counts, tags, and timestamps when available. Existing downloaded files are not rewritten.

For direct URL downloads, these fields are extracted when the supplied page contains the same metadata elements. The web `/download` endpoint optionally accepts a `novel_metadata` array of search result records aligned with `novel_urls` to preserve metadata from the search page.

## Main Class and Methods

- `NovelSpider`: main crawler class.
- `search_novels(keyword, search_type)`: search for novels.
- `get_novel_chapters(novel_url)`: retrieve a novel's chapter list.
- `get_chapter_content(chapter_url)`: extract chapter text.
- `get_novel_content_by_search(keyword, search_type)`: search and retrieve the first matching novel.
- `save_novel_to_file(novel_data, filename)`: save a novel to a text file.

## How It Works

1. Search using `https://www.alicesw.com/search.html?q={keyword}&f={type}`.
2. Retrieve the novel's chapter list from its chapter-list or detail page.
3. Extract text from the `read-content` container, with fallback selectors where supported.

## Responsible Use

1. Avoid excessive requests and respect the website's rate limits.
2. Follow the website's `robots.txt`, terms of use, and applicable laws.
3. This tool is intended for learning and research, not commercial use.
4. Copyright in downloaded content remains with the original authors.
5. The target website contains adult content; access it only if you meet the applicable age requirements.
