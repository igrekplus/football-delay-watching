
from bs4 import BeautifulSoup
import json
import re

with open("temp_reference_report.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

def extract_images():
    images = {}
    
    # Try to find player images in formation or lineup sections
    # Look for img tags with player names nearby or specific classes if known
    # Since I don't know the exact class structure, I'll dump all images with alt text
    
    for img in soup.find_all("img"):
        src = img.get("src")
        alt = img.get("alt")
        if src and alt:
            images[alt] = src
            
    # Also look for background-image styles if used
    for div in soup.find_all("div", style=True):
        style = div.get("style")
        if "background-image" in style:
            match = re.search(r'url\((.*?)\)', style)
            if match:
                url = match.group(1).strip("'\"")
                # Try to find associated name
                text = div.get_text(strip=True)
                if text:
                    images[text] = url

    print(json.dumps(images, indent=2, ensure_ascii=False))

extract_images()
