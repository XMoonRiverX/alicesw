// content.js

function crawlPage() {
    const novels = [];
    
    // Extract novels from Alice Library
    if (window.location.hostname === 'www.alicesw.com') {
        // Extract from the novel detail page
        if (window.location.pathname.includes('/novel/')) {
            const title = document.querySelector('h1, .novel_title')?.textContent?.trim() || 'Unknown Title';
            const author = document.querySelector('a[href*="/search\?q=.*&f=author"]')?.textContent?.trim() || 'Unknown Author';
            
            novels.push({
                title: title,
                author: author,
                url: window.location.href,
                source: 'alicesw'
            });
        }
        
        // Extract from the search results page
        else if (window.location.pathname.includes('/search')) {
            const novelItems = document.querySelectorAll('.list-group-item');
            novelItems.forEach(item => {
                const titleElem = item.querySelector('h5 a');
                const authorElem = item.querySelector('a[href*="/search\?q=.*&f=author"]');
                
                if (titleElem) {
                    const title = titleElem.textContent.trim();
                    const url = titleElem.href;
                    const author = authorElem?.textContent?.trim() || 'Unknown Author';
                    
                    novels.push({
                        title: title,
                        author: author,
                        url: url,
                        source: 'alicesw'
                    });
                }
            });
        }
    }
    
    // Add extraction logic for other websites here
    // else if (window.location.hostname === 'example.com') {
    //     // Extraction logic for another website
    // }
    
    return novels;
}

// Expose for external calls
window.crawlPage = crawlPage;
