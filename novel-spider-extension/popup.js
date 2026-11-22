// popup.js

let novels = [];

// Extract novels
function crawlNovels() {
    document.getElementById('status').textContent = 'Scanning...';
    document.getElementById('novelList').innerHTML = '<div class="loading">Scanning the page for novels...</div>';
    document.getElementById('downloadBtn').disabled = true;
    
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        chrome.scripting.executeScript({
            target: {tabId: tabs[0].id},
            function: function() {
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
                        // Try multiple selectors to find novel entries
                        const novelItems = document.querySelectorAll('div[class*="list-group-item"], div[class*="novel-item"], .novel-list > div');
                        
                        if (novelItems.length === 0) {
                            // Try finding elements containing novel metadata directly
                            const allElements = document.querySelectorAll('div');
                            allElements.forEach(item => {
                                const titleElem = item.querySelector('a[href*="/novel/"]');
                                if (titleElem) {
                                    const title = titleElem.textContent.trim();
                                    const url = titleElem.href;
                                    
                                    // Find author information
                                    let author = 'Unknown Author';
                                    const authorElem = item.querySelector('a[href*="/search\?q="][href*="&f=author"]');
                                    if (authorElem) {
                                        author = authorElem.textContent.trim();
                                    } else {
                                        // Try another way to find the author
                                        const textContent = item.textContent;
                                        const authorMatch = textContent.match(/作者：([^\s]+)/);
                                        if (authorMatch) {
                                            author = authorMatch[1];
                                        }
                                    }
                                    
                                    novels.push({
                                        title: title,
                                        author: author,
                                        url: url,
                                        source: 'alicesw'
                                    });
                                }
                            });
                        } else {
                            novelItems.forEach(item => {
                                const titleElem = item.querySelector('h5 a, a[href*="/novel/"]');
                                const authorElem = item.querySelector('a[href*="/search\?q=.*&f=author"], a[href*="/search\?q="][href*="&f=author"]');
                                
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
                }
                
                return novels;
            }
        }, function(results) {
            if (results && results[0]) {
                novels = results[0].result;
                displayNovels(novels);
                document.getElementById('status').textContent = `Found ${novels.length} novels`;
                document.getElementById('downloadBtn').disabled = novels.length === 0;
            } else {
                document.getElementById('status').textContent = 'No novels found';
                document.getElementById('novelList').innerHTML = '<div class="loading">No novels found on this page</div>';
            }
        });
    });
}

// Display the novel list
function displayNovels(novelList) {
    const novelListElement = document.getElementById('novelList');
    if (novelList.length === 0) {
        novelListElement.innerHTML = '<div class="loading">No novels found</div>';
        return;
    }
    
    novelListElement.innerHTML = novelList.map((novel, index) => `
        <div class="novel-item">
            <input type="checkbox" id="novel-${index}" value="${index}">
            <div>
                <div class="novel-title">${novel.title}</div>
                <div class="novel-author">Author: ${novel.author}</div>
            </div>
        </div>
    `).join('');
}

// Download selected novels
function downloadSelected() {
    const selectedCheckboxes = document.querySelectorAll('input[type="checkbox"]:checked');
    const selectedNovels = Array.from(selectedCheckboxes).map(checkbox => {
        const index = parseInt(checkbox.value);
        return novels[index];
    });
    
    if (selectedNovels.length === 0) {
        document.getElementById('status').textContent = 'Please select novels to download';
        return;
    }
    
    document.getElementById('status').textContent = `Downloading ${selectedNovels.length} novels...`;
    
    // Ask the background script to download the novels
    chrome.runtime.sendMessage({
        action: 'downloadNovels',
        novels: selectedNovels
    }, function(response) {
        if (response.success) {
            document.getElementById('status').textContent = 'Download complete!';
        } else {
            document.getElementById('status').textContent = 'Download failed';
        }
    });
}

// Bind event handlers
document.getElementById('crawlBtn').addEventListener('click', crawlNovels);
document.getElementById('downloadBtn').addEventListener('click', downloadSelected);

// Initialize
window.onload = function() {
    // Automatically scan the current page
    crawlNovels();
};
