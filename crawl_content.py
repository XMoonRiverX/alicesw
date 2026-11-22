from novel_spider import NovelSpider
import argparse

parser = argparse.ArgumentParser(description='Retrieve novel chapter content')
parser.add_argument('novel_url', type=str, help='Novel chapter-list page URL')
args = parser.parse_args()

spider = NovelSpider()


chapters = spider.get_novel_chapters(novels[0][args.novel_url])
print(f"Found {len(chapters)} chapters")

    # Retrieve chapter content
if chapters:
    content = spider.get_chapter_content(chapters[0][args.novel_url])
    print(f"Content length: {len(content)} characters")
