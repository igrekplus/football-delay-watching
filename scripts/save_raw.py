import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, unquote

def normalize_url(url):
    # 1. Parse
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if ':' in netloc:
        host, port = netloc.split(':')
        if (scheme == 'http' and port == '80') or (scheme == 'https' and port == '443'):
            netloc = host
    
    path = unquote(parsed.path)
    # Collapse slashes
    while '//' in path:
        path = path.replace('//', '/')
    # Resolve . and .. (simple approx)
    path_parts = []
    for part in path.split('/'):
        if part == '.' or part == '': continue
        if part == '..':
            if path_parts: path_parts.pop()
        else:
            path_parts.append(part)
    path = '/' + '/'.join(path_parts)
    # Remove trailing slash if not root
    if path != '/' and path.endswith('/'):
        path = path[:-1]

    # Query
    query = parsed.query
    if query:
        q_list = parse_qsl(query)
        # Filter exclusions
        exclusions = ['utm_', 'gclid', 'fbclid']
        filtered_q = []
        for k, v in q_list:
            if any(k.startswith(ex) for ex in exclusions): continue
            filtered_q.append((k, v))
        # Sort
        filtered_q.sort()
        query = urlencode(filtered_q)
    
    return f"{scheme}://{netloc}{path}{'?' + query if query else ''}"

def main():
    if len(sys.argv) < 9:
        print("Usage: script.py entity_type entity_key url source_type title published_at original_path translated_path")
        sys.exit(1)

    entity_type = sys.argv[1]
    entity_key = sys.argv[2]
    url = sys.argv[3]
    source_type = sys.argv[4]
    title = sys.argv[5]
    published_at = sys.argv[6]
    original_path = sys.argv[7]
    translated_path = sys.argv[8]

    # IDs
    normalized_url = normalize_url(url)
    
    # Generate readable url_id (slug) instead of hash
    parsed = urlparse(normalized_url)
    domain = parsed.netloc.replace('www.', '')
    path_slug = parsed.path.strip('/').replace('/', '_').replace('-', '_')
    if not path_slug:
        path_slug = 'index'
    
    # Simple sanitization
    safe_domain = "".join(c if c.isalnum() or c in '._-' else '_' for c in domain)
    safe_path = "".join(c if c.isalnum() or c in '._-' else '_' for c in path_slug)
    
    url_id = f"{safe_domain}_{safe_path}"
    # Truncate if too long
    if len(url_id) > 100:
        url_id = url_id[:100]

    now_str = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    raw_id = f"{url_id}_{now_str}"
    entity_id = f"{entity_type}-{entity_key}"

    # Paths
    base_dir = f"knowledge/raw/{entity_type}/{entity_key}/{url_id}/{raw_id}"
    os.makedirs(base_dir, exist_ok=True)

    # Save Text
    shutil.copy(original_path, os.path.join(base_dir, "text_before_transfer.txt"))
    shutil.copy(translated_path, os.path.join(base_dir, "text.txt"))

    # Meta
    meta = {
        "raw_id": raw_id,
        "url_id": url_id,
        "entity_id": entity_id,
        "source_url": url,
        "fetched_at": datetime.now().isoformat(),
        "status_code": 200,
        "content_type": "text/html", # Assumed
        "title": title,
        "published_at": published_at if published_at != "null" else None,
        "extract_method": "playwright_mcp", # As instructed
        "query_profile": "club_history",
        "search_queries": [], # Simplified
        "source_type": source_type,
        "notes": "Acquired via antigravity agent"
    }

    with open(os.path.join(base_dir, "meta.json"), "w", encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Saved raw data to {base_dir}")

if __name__ == "__main__":
    main()
