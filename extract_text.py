
from bs4 import BeautifulSoup
import json

with open("temp_reference_report.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

section_map = {}

# Find "Pre-Match Interview" sections
# The structure might be: <h3>Home Team Interview</h3> ... <p>...</p>
# Or look for specific keywords if headers aren't clear.
# Based on common structures, let's dump all h3 and following p text to identify fields.

def get_section_text(header_text):
    header = soup.find(lambda tag: tag.name in ["h3", "h4", "h5"] and header_text in tag.get_text())
    if header:
        content = []
        curr = header.find_next_sibling()
        while curr and curr.name != "h3" and curr.name != "h4" and curr.name != "h5":
            if curr.name == "p":
                 content.append(curr.get_text(strip=True))
            elif curr.name == "ul":
                 for li in curr.find_all("li"):
                     content.append("- " + li.get_text(strip=True))
            curr = curr.find_next_sibling()
        return "\n\n".join(content)
    return ""

extracted = {}

# Extract based on specific headers found
home_interview_headers = [
    '新戦力アントワーヌ・セメニョについて', 
    '攻撃陣の現状とセメニョ獲得の背景', 
    '負傷者の状況', 
    '対戦相手エクセター・シティについて'
]
away_interview_headers = [
    'FAカップ3回戦、マンチェスター・シティ戦に向けて', 
    '7,800人のサポーターとともに', 
    'マンチェスター・ユナイテッドの施設を利用して準備', 
    'チームの最新情報', 
    '相手チームの状況'
]

home_interview_text = []
for h in home_interview_headers:
    text = get_section_text(h)
    if text:
        home_interview_text.append(f"### {h}\n{text}")

away_interview_text = []
for h in away_interview_headers:
    text = get_section_text(h)
    if text:
        away_interview_text.append(f"### {h}\n{text}")

extracted["home_interview"] = "\n\n".join(home_interview_text)
extracted["away_interview"] = "\n\n".join(away_interview_text)

# Transfer news likely under '🆕 獲得・加入 (In)' which appears twice.
# We need to distinguish home and away based on position in file or preceding headers.
# Simplification: Find 'Manchester City' header then look for transfer sections until 'Exeter City'
# But headers list shows flat structure.
# Let's try to grab text under '🆕 獲得・加入 (In)', '💬 噂・動向 (Rumors)'
# The list shows: ... '🆕 獲得・加入 (In)', '💬 噂・動向 (Rumors)', 'その他', '🆕 獲得・加入 (In)', '👋 放出・退団 (Out)', '💬 噂・動向 (Rumors)' ...
# First group is likely Home (City), Second is Away (Exeter) or vice versa.
# Report order is usually Home then Away.

transfer_headers = ['🆕 獲得・加入 (In)', '👋 放出・退団 (Out)', '💬 噂・動向 (Rumors)', 'その他']
# Find all occurrences
all_transfers = []
for h in transfer_headers:
    # This naive get_section_text only finds first. Use find_all loop.
    pass

# Better approach for transfer: Iterate through soup to split by team sections if possible.
# Given constraints, let's just dump specific known sections.

def get_all_sections(header_text):
    sections = []
    for header in soup.find_all(lambda tag: tag.name in ["h3", "h4", "h5", "h6"] and header_text in tag.get_text()):
        content = []
        curr = header.find_next_sibling()
        while curr and curr.name not in ["h2", "h3", "h4", "h5", "h6"]:
             if curr.name == "p":
                 content.append(curr.get_text(strip=True))
             elif curr.name == "ul":
                 for li in curr.find_all("li"):
                     content.append("- " + li.get_text(strip=True))
             curr = curr.find_next_sibling()
        sections.append("\n".join(content))
    return sections

in_news = get_all_sections('🆕 獲得・加入 (In)')
rumor_news = get_all_sections('💬 噂・動向 (Rumors)')
out_news = get_all_sections('👋 放出・退団 (Out)')

# Assemble broadly
extracted["home_transfer_raw"] = "### 加入\n" + (in_news[0] if in_news else "") + "\n\n### 噂\n" + (rumor_news[0] if rumor_news else "")
extracted["away_transfer_raw"] = "### 加入\n" + (in_news[1] if len(in_news)>1 else "") + "\n\n### 放出\n" + (out_news[0] if out_news else "") + "\n\n### 噂\n" + (rumor_news[1] if len(rumor_news)>1 else "")

with open("extraction_output.json", "w", encoding="utf-8") as f:
    json.dump(extracted, f, indent=2, ensure_ascii=False)
