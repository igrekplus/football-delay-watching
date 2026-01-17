import os
import re
import sys
from pathlib import Path


def check_links(start_path):
    # Markdownファイルの検索
    md_files = []
    if os.path.isfile(start_path):
        md_files.append(Path(start_path).resolve())
    else:
        for root, dirs, files in os.walk(start_path):
            for file in files:
                if file.endswith(".md"):
                    md_files.append(Path(root) / file)

    broken_links = []
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md_file in md_files:
        try:
            with open(md_file, encoding="utf-8") as f:
                content = f.read()

            # リンクの抽出
            matches = link_pattern.findall(content)
            for text, link in matches:
                # アンカーリンクのみの場合はスキップ
                if link.startswith("#"):
                    continue

                # 外部URLはスキップ
                if link.startswith("http://") or link.startswith("https://"):
                    continue

                # mailtoはスキップ
                if link.startswith("mailto:"):
                    continue

                # アンカー部分を除去
                link_path = link.split("#")[0]
                if not link_path:
                    continue

                # パス解決
                # ファイルからの相対パスとして解決
                target_path = (md_file.parent / link_path).resolve()

                if not target_path.exists():
                    broken_links.append(
                        {
                            "file": str(md_file),
                            "text": text,
                            "link": link,
                            "resolved": str(target_path),
                        }
                    )

        except Exception as e:
            print(f"Error reading {md_file}: {e}")

    return broken_links


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_links.py <path_to_scan>")
        sys.exit(1)

    target_dir = sys.argv[1]
    print(f"Scanning {target_dir} for broken links...")

    broken = check_links(target_dir)

    if broken:
        print(f"\nFound {len(broken)} broken links:")
        for b in broken:
            print(f"\nFile: {b['file']}")
            print(f"  Link Text: {b['text']}")
            print(f"  Link Target: {b['link']}")
            print(f"  Resolved: {b['resolved']}")
        sys.exit(1)
    else:
        print("\nNo broken links found!")
        sys.exit(0)
