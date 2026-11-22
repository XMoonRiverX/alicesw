# Novel Spider - Chrome Extension

Discover novels on the current page, select the ones you want, and download them as text files.

## Supported Website

- Alice's Library (https://www.alicesw.com)

## Installation

The manifest references `popup.html`, but that file is not included in this checkout. The popup interface must be restored before the extension can be used as described below.

1. Open Chrome.
2. Navigate to `chrome://extensions/`.
3. Enable **Developer mode**.
4. Click **Load unpacked**.
5. Select the `novel-spider-extension` directory.

## Usage

1. Open a supported novel page or search results page.
2. Click the Novel Spider icon in the browser toolbar.
3. The extension automatically scans the current page for novels.
4. Select the novels to download in the popup.
5. Click **Download Selected**.
6. The novels are saved as `.txt` files.

Interface messages and exported metadata labels are in English. Novel titles, author names, and chapter text remain in their original language.

## Extension Structure

```text
novel-spider-extension/
├── manifest.json        # Extension configuration
├── background.js        # Background service worker
├── content.js           # Content script
├── popup.html           # Popup page (not included)
├── popup.js             # Popup logic
└── README.md            # Usage instructions
```

## Development

### Permissions

- `activeTab`: access the active tab.
- `scripting`: execute scripts.
- `downloads`: save downloaded files.

### Features

1. **Automatic scanning**: scan the current page when the popup opens.
2. **Multiple selection**: download several novels at once.
3. **Page detection**: recognize supported novel detail and search results pages.
4. **One-click download**: download selected novels with a single button.

### Supporting Additional Websites

Add page extraction logic in `content.js` and `popup.js`, and implement the corresponding download handling in `background.js`.

## Responsible Use

1. Avoid excessive requests.
2. Follow the website's terms of use and applicable laws.
3. Use this extension for learning and research only.
4. Copyright in downloaded content remains with the original authors.

## Technology

- HTML5
- CSS3
- JavaScript
- Chrome Extension API

## Version History

### v1.0

- Initial release.
- Support for Alice's Library.
- Basic page scanning and novel downloads.
