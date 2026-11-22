// background.js

// Listen for messages
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === 'downloadNovels') {
        downloadNovels(request.novels).then(success => {
            sendResponse({success: success});
        });
        return true; // Respond asynchronously
    }
});

// Download novels
async function downloadNovels(novels) {
    for (const novel of novels) {
        try {
            // Use site-specific extraction logic
            if (novel.source === 'alicesw') {
                await downloadAliceNovel(novel);
            }
        } catch (error) {
            console.error('Failed to download novel:', error);
            return false;
        }
    }
    return true;
}

// Download novels from Alice Library
async function downloadAliceNovel(novel) {
    return new Promise(async (resolve, reject) => {
        try {
            // Extract novel content
            const novelContent = await crawlNovelContent(novel.url);
            
            // Build the file contents
            let content = `Novel title: ${novel.title}\n`;
            content += `Author: ${novel.author}\n`;
            content += `URL: ${novel.url}\n`;
            content += '='.repeat(50) + '\n\n';
            
            for (const [chapterIndex, chapter] of novelContent.chapters.entries()) {
                content += `Chapter ${chapterIndex + 1}: ${chapter.title}\n`;
                content += '-'.repeat(30) + '\n';
                content += chapter.content + '\n\n';
            }
            
            // Sanitize the filename
            const cleanTitle = novel.title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_');
            const filename = `${cleanTitle}.txt`;
            
            // Download using a data URL
            const encoder = new TextEncoder();
            const data = encoder.encode(content);
            const blob = new Blob([data], {type: 'text/plain;charset=utf-8'});
            
            // Read the blob with FileReader and create a data URL
            const reader = new FileReader();
            reader.onload = function(e) {
                const dataUrl = e.target.result;
                
                chrome.downloads.download({
                    url: dataUrl,
                    filename: filename,
                    saveAs: false
                }, function(downloadId) {
                    if (downloadId) {
                        resolve(true);
                    } else {
                        reject(new Error('Download failed'));
                    }
                });
            };
            reader.onerror = function() {
                reject(new Error('Failed to create file'));
            };
            reader.readAsDataURL(blob);
        } catch (error) {
            reject(error);
        }
    });
}

// Extract novel content
async function crawlNovelContent(url) {
    return new Promise((resolve, reject) => {
        // Extract the novel ID and build the chapter-list page URL
        let chaptersUrl = url;
        const novelIdMatch = url.match(/\/novel\/(\d+)\.html/);
        if (novelIdMatch) {
            const novelId = novelIdMatch[1];
            chaptersUrl = `https://www.alicesw.com/other/chapters/id/${novelId}.html`;
        }
        
        console.log(`Chapter-list page: ${chaptersUrl}`);
        
        fetch(chaptersUrl)
            .then(response => response.text())
            .then(html => {
                // Extract chapters using the equivalent of the .mulu_list li a selector
                const chapters = [];
                
                // Prefer the chapter-list page with a more precise pattern for .mulu_list li a
                const muluListRegex = /<div\s+class="mulu_list"[^>]*>([\s\S]*?)<\/div>/;
                const muluMatch = html.match(muluListRegex);
                
                if (muluMatch) {
                    const muluContent = muluMatch[1];
                    const chapterRegex = /<li[^>]*><a[^>]+href="([^"]+)"[^>]*>([^<]+)<\/a><\/li>/g;
                    let match;
                    
                    while ((match = chapterRegex.exec(muluContent)) !== null) {
                        const chapterUrl = match[1];
                        const chapterTitle = match[2].trim();
                        
                        if (chapterTitle) {
                            chapters.push({
                                title: chapterTitle,
                                url: chapterUrl.startsWith('http') ? chapterUrl : new URL(chapterUrl, chaptersUrl).href
                            });
                        }
                    }
                }
                
                // Fall back to the original page if the chapter-list page has no chapters
                if (chapters.length === 0) {
                    console.log('Extract chapters from the original page');
                    // Try alternative chapter extraction methods
                    const chapterRegexes = [
                        /<li[^>]*><a[^>]+href="([^"]+)"[^>]*>([^<]+)<\/a><\/li>/g,
                        /<a[^>]+href="([^"\s]+\/book\/[^"\s]+)"[^>]*>([^<]+)<\/a>/g
                    ];
                    
                    chapterRegexes.forEach(regex => {
                        let match;
                        while ((match = regex.exec(html)) !== null) {
                            const chapterUrl = match[1];
                            const chapterTitle = match[2].trim();
                            
                            if (chapterUrl.includes('/book/') && chapterTitle && !chapters.some(c => c.url === chapterUrl)) {
                                chapters.push({
                                    title: chapterTitle,
                                    url: chapterUrl.startsWith('http') ? chapterUrl : new URL(chapterUrl, chaptersUrl).href
                                });
                            }
                        }
                    });
                }
                
                console.log(`Found ${chapters.length} chapters`);
                
                // Retrieve content for each chapter
                const chapterPromises = chapters.map(chapter => {
                    return fetch(chapter.url)
                        .then(response => response.text())
                        .then(chapterHtml => {
                            // Extract chapter content using the same approach as the Python implementation
                            let content = '';
                            
                            // Try matching the read-content class
                            let contentMatch = chapterHtml.match(/<div\s+class="read-content"[^>]*>([\s\S]*?)<\/div>/);
                            
                            // Fall back to classes containing both read and content
                            if (!contentMatch) {
                                contentMatch = chapterHtml.match(/<div\s+class="[^"]*read[^"]*content[^"]*"[^>]*>([\s\S]*?)<\/div>/);
                            }
                            
                            // Try other possible content containers as a final fallback
                            if (!contentMatch) {
                                contentMatch = chapterHtml.match(/<div\s+class="[^"]*content[^"]*"[^>]*>([\s\S]*?)<\/div>/);
                            }
                            
                            if (contentMatch && contentMatch[1]) {
                                // Remove unwanted elements such as scripts, styles, and ads
                                let contentHtml = contentMatch[1];
                                // Remove script tags
                                contentHtml = contentHtml.replace(/<script[^>]*>[\s\S]*?<\/script>/g, '');
                                // Remove style tags
                                contentHtml = contentHtml.replace(/<style[^>]*>[\s\S]*?<\/style>/g, '');
                                // Remove ad elements
                                contentHtml = contentHtml.replace(/<div[^>]*class="[^"]*ad[^"]*"[^>]*>[\s\S]*?<\/div>/g, '');
                                contentHtml = contentHtml.replace(/<p[^>]*class="[^"]*ad[^"]*"[^>]*>[\s\S]*?<\/p>/g, '');
                                contentHtml = contentHtml.replace(/<span[^>]*class="[^"]*ad[^"]*"[^>]*>[\s\S]*?<\/span>/g, '');
                                // Remove all HTML tags
                                content = contentHtml.replace(/<[^>]+>/g, '').trim();
                                // Collapse consecutive newlines
                                content = content.replace(/\n+/g, '\n');
                                // Trim leading and trailing whitespace
                                content = content.trim();
                            } else {
                                // Try extracting text directly from the page
                                const textMatch = chapterHtml.match(/<body[^>]*>([\s\S]*?)<\/body>/);
                                if (textMatch) {
                                    let textContent = textMatch[1];
                                    // Remove HTML tags
                                    textContent = textContent.replace(/<[^>]+>/g, '').trim();
                                    // Collapse consecutive newlines
                                    textContent = textContent.replace(/\n+/g, '\n');
                                    // Limit the extracted content length
                                    content = textContent.substring(0, 10000) || 'Chapter content not found';
                                } else {
                                    content = 'Chapter content not found';
                                }
                            }
                            
                            return {
                                title: chapter.title,
                                content: content
                            };
                        })
                        .catch(error => {
                            console.error(`Failed to retrieve chapter content: ${chapter.title}`, error);
                            return {
                                title: chapter.title,
                                content: 'Failed to retrieve content'
                            };
                        });
                });
                
                Promise.all(chapterPromises)
                    .then(chaptersWithContent => {
                        resolve({chapters: chaptersWithContent});
                    })
                    .catch(error => reject(error));
            })
            .catch(error => reject(error));
    });
}
