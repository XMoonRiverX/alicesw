import argparse
import os
from spider_batch import NovelSpider, BASE_DIR

def main():
    parser = argparse.ArgumentParser(description="Download an entire novel from its chapter-list or detail page URL")
    parser.add_argument('url', help='Novel chapter-list or detail page URL')
    parser.add_argument('-f', '--format', choices=['single', 'chapter'], default='single', help='Save format: single or chapter')
    parser.add_argument('--title', help='Optional novel title to override automatic detection')
    parser.add_argument('--author', help='Optional author to override automatic detection')
    args = parser.parse_args()

    spider = NovelSpider()
    novel = spider.get_novel_content_by_url(args.url, novel_title=args.title, novel_author=args.author)
    if not novel or not novel.get('chapters'):
        print("Could not retrieve novel content")
        return 1

    download_dir = os.path.join(BASE_DIR, "downloads")
    spider.save_novel_to_file(novel, download_dir=download_dir, save_format=args.format)
    print(f"Output directory: {download_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
