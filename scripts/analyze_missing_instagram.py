import csv
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).resolve().parent.parent))

def main():
    csv_path = Path("data/player_instagram_50.csv")
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    print(f"Analyzing {csv_path}...\n")
    
    missing_count = 0
    total_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            print(f"{'ID':<10} {'Name':<25} {'Position':<15} {'Number':<8}")
            print("-" * 60)
            
            for row in reader:
                total_count += 1
                url = row.get('instagram_url', '').strip()
                if not url:
                    missing_count += 1
                    print(f"{row.get('player_id', ''):<10} {row.get('name', ''):<25} {row.get('position', ''):<15} {row.get('number', ''):<8}")

        print("\n" + "=" * 30)
        print(f"Total Players: {total_count}")
        print(f"Missing URLs : {missing_count}")
        print("=" * 30)
        
        if missing_count > 0:
            print(f"\nTip: Run specific search for each player using 'search_web' tool.")
            
    except Exception as e:
        print(f"Error reading CSV: {e}")

if __name__ == "__main__":
    main()
