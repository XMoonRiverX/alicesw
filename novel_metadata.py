import re
from urllib.parse import parse_qs, urljoin, urlparse


def _text(element):
    return " ".join(element.get_text().split()) if element else ""


def _search_links(container, search_type):
    return [
        link for link in container.select('a[href]')
        if parse_qs(urlparse(link['href']).query).get('f') == [search_type]
    ]


def extract_novel_metadata(container):
    """Extract full descriptions, muted metadata, tags, and timestamps."""
    author_links = _search_links(container, 'author')
    muted_text = [_text(element) for element in container.select('.text-muted')]
    metadata_text = " ".join(muted_text)
    status_element = container.select_one('h5 .text-muted, small.text-muted')
    time_text = " ".join(_text(element) for element in container.select('.timedesc'))
    word_count_match = re.search(r'(?:字數|字数)\s*[:：]\s*([\d,.]+\s*[萬万億亿千]?)', metadata_text)
    views_match = re.search(r'(?:瀏覽|浏览)\s*[:：]\s*([\d,.]+\s*[萬万億亿千]?)', metadata_text)
    timestamp_pattern = r'\s*[:：]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)'
    published_match = re.search(r'(?:發布時間|发布时间)' + timestamp_pattern, time_text)
    updated_match = re.search(r'(?:更新時間|更新时间)' + timestamp_pattern, time_text)
    tags = [_text(link).lstrip('#').strip() for link in _search_links(container, 'tag')]

    return {
        'author': _text(author_links[0]) if author_links else '',
        'intro': _text(container.select_one('.content-txt')),
        'status': _text(status_element).strip('[]【】'),
        'word_count': word_count_match.group(1).strip() if word_count_match else '',
        'views': views_match.group(1).strip() if views_match else '',
        'tags': list(dict.fromkeys(tag for tag in tags if tag)),
        'text_muted': muted_text,
        'published_at': published_match.group(1) if published_match else '',
        'updated_at': updated_match.group(1) if updated_match else '',
    }


def parse_search_result(item, base_url):
    """Parse one search result, skipping entries without a title link."""
    title_element = item.select_one('h5 a[href]')
    if not title_element:
        return None

    return {
        'title': _text(title_element),
        'url': urljoin(base_url, title_element['href']),
        **extract_novel_metadata(item),
    }


def format_novel_metadata(novel_data):
    """Format optional metadata for text exports without changing novel text."""
    fields = (
        ('Synopsis', 'intro'),
        ('Status', 'status'),
        ('Word count', 'word_count'),
        ('Views', 'views'),
        ('Tags', 'tags'),
        ('Published at', 'published_at'),
        ('Updated at', 'updated_at'),
    )
    lines = []
    for label, key in fields:
        value = novel_data.get(key)
        if isinstance(value, list):
            value = ', '.join(value)
        if value:
            lines.append(f'{label}: {value}\n')
    return ''.join(lines)
