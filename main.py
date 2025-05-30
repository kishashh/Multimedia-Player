from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright
import re

app = Flask(__name__)

def extract_embed_url(url):
    # Attempts to extract an embeddable video URL from the provided page URL.
    
    # Supports:
    # - YouTube videos and live streams (manually constructs the embed URL)
    # - Other sites with iframe or Open Graph <meta property="og:video"> tags

    # Parameters:
    #     url (str): The media page URL

    # Returns:
    #     str | None: A direct embeddable URL if found, else None
    try:
        # Handle YouTube URLs manually using regex to extract video ID
        youtube_match = re.match(
            r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|live/)?(?P<id>[a-zA-Z0-9_-]{11})',
            url
        )
        if youtube_match:
            video_id = youtube_match.group('id')
            return f'https://www.youtube.com/embed/{video_id}'

        # For non-YouTube URLs, use Playwright to visit and parse page content
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.wait_for_timeout(4000)  # Allow JavaScript to load content

            # Attempt to find the first iframe tag and return its src

            # TODO: Make this able to be used on other sites that dont have iframe src in the first iteration of iframe.
            # TODO: Make faster (Pref as fast as YouTube works)
            iframe = page.query_selector('iframe')
            if iframe:
                src = iframe.get_attribute('src')
                if src:
                    browser.close()
                    return src

            # Attempt to find og:video meta tag
            og_video = page.query_selector('meta[property="og:video"]')
            if og_video:
                content = og_video.get_attribute('content')
                if content:
                    browser.close()
                    return content

            browser.close()
    except Exception as e:
        print(f"[ERROR] While extracting from {url}: {e}")

    return None


@app.route('/')
def index():
    # Serves the main HTML page that allows users to input media URLs
    # and view them in an embedded multi-stream viewer.
    return render_template('main.html')


@app.route('/embed', methods=['POST'])
def get_embed():
    # API endpoint to extract an embeddable media URL from a given link.
    
    # Expects JSON body: { "url": "https://example.com/media" }
    
    # Returns:
    #     JSON: { "embed_url": "https://..." } on success
    #           { "error": "..." } on failure
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    embed_url = extract_embed_url(url.strip())
    if embed_url:
        print(embed_url)  # Log for debugging
        return jsonify({'embed_url': embed_url})
    else:
        return jsonify({'error': 'Could not extract embed URL'}), 400


if __name__ == '__main__':
    # Start the Flask development server with debug mode enabled
    app.run(debug=True)
