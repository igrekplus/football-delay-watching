import re
from typing import List

class SpoilerFilter:
    def __init__(self):
        # Forbidden patterns - Score only (not formations like 3-4-2-1)
        # Matches "1-0", "2-1" etc. but NOT "3-4-2-1" or "4-3-3"
        # Negative lookbehind/lookahead to exclude patterns with more hyphens
        self.score_pattern = re.compile(r'(?<!\d-)(\b\d{1,2}-\d{1,2}\b)(?!-\d)')
        
        # Common formation patterns to preserve (will be temporarily escaped)
        self.formation_patterns = [
            r'3-4-3', r'3-4-2-1', r'3-5-2', r'3-4-1-2',
            r'4-3-3', r'4-4-2', r'4-2-3-1', r'4-1-4-1', r'4-5-1', r'4-4-1-1', r'4-1-2-1-2',
            r'5-3-2', r'5-4-1', r'5-2-3'
        ]
        
        self.banned_keywords = [
            "won", "lost", "victory", "defeat", "beat", "winner", "loser",
            "勝った", "負けた", "勝利", "敗北", "勝ち点3", "points",
            "goal", "scored", "scoresheet", "netted",
            "得点", "ゴール", "先制", "決勝点"
        ]

    def check_text(self, text: str) -> str:
        # Issue #32: CENSORED置換を無効化し、そのまま出力
        # 結果言及の判定は別Issue（#33）でGeminiを使用して実施
        return text

    def is_safe_article(self, article_content: str) -> bool:
        # Pre-check: if too many forbidden words, mark as unsafe
        hits = 0
        for keyword in self.banned_keywords:
             if keyword.lower() in article_content.lower():
                 hits += 1
        
        # If it looks like a match report (many hits), reject it
        if hits > 3:
            return False
            
        return True
