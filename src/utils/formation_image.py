"""
Formation Image Generator
Generates formation diagram images using Pillow (PIL)
"""

from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional, Dict
import os
import logging

logger = logging.getLogger(__name__)

# Pitch dimensions (pixels) - reduced for compact display
PITCH_WIDTH = 500
PITCH_HEIGHT = 400
PITCH_COLOR = (34, 139, 34)  # Forest green
LINE_COLOR = (255, 255, 255)  # White
PLAYER_COLOR = (255, 255, 255)
PLAYER_BG_HOME = (0, 0, 139)  # Dark blue
PLAYER_BG_AWAY = (139, 0, 0)  # Dark red
PLAYER_RADIUS = 14

# Formation layouts - define Y positions for each line (0.0 = goal, 1.0 = midfield)
# Each formation maps to list of (line_y_ratio, num_players) 
# Y ratios adjusted to match mock HTML: GK~12%, DF~32%, MF~55%, FW~78%
FORMATION_LAYOUTS = {
    # 4 defenders
    "4-3-3": [(0.10, 1), (0.32, 4), (0.60, 3), (0.85, 3)],
    "4-4-2": [(0.10, 1), (0.32, 4), (0.60, 4), (0.85, 2)],
    "4-2-3-1": [(0.10, 1), (0.30, 4), (0.50, 2), (0.70, 3), (0.90, 1)],
    "4-1-4-1": [(0.10, 1), (0.30, 4), (0.50, 1), (0.70, 4), (0.90, 1)],
    "4-5-1": [(0.10, 1), (0.30, 4), (0.60, 5), (0.90, 1)],
    "4-4-1-1": [(0.10, 1), (0.30, 4), (0.50, 4), (0.70, 1), (0.90, 1)],
    "4-3-2-1": [(0.10, 1), (0.30, 4), (0.50, 3), (0.70, 2), (0.90, 1)],  # Christmas tree
    "4-3-1-2": [(0.10, 1), (0.30, 4), (0.50, 3), (0.70, 1), (0.90, 2)],
    "4-1-2-1-2": [(0.08, 1), (0.28, 4), (0.44, 1), (0.60, 2), (0.76, 1), (0.92, 2)], # 6 lines, slightly tighter
    # 3 defenders
    "3-4-3": [(0.10, 1), (0.32, 3), (0.60, 4), (0.85, 3)],
    "3-5-2": [(0.10, 1), (0.32, 3), (0.60, 5), (0.85, 2)],
    "3-4-2-1": [(0.10, 1), (0.30, 3), (0.50, 4), (0.70, 2), (0.90, 1)],
    "3-4-1-2": [(0.10, 1), (0.30, 3), (0.50, 4), (0.70, 1), (0.90, 2)],
    "3-1-4-2": [(0.10, 1), (0.30, 3), (0.50, 1), (0.70, 4), (0.90, 2)],
    # 5 defenders
    "5-3-2": [(0.10, 1), (0.32, 5), (0.60, 3), (0.85, 2)],
    "5-4-1": [(0.10, 1), (0.32, 5), (0.60, 4), (0.90, 1)],
    "5-2-3": [(0.10, 1), (0.32, 5), (0.60, 2), (0.85, 3)],
    "5-2-1-2": [(0.10, 1), (0.30, 5), (0.50, 2), (0.70, 1), (0.90, 2)],
}


class FormationImageGenerator:
    def __init__(self):
        self.width = PITCH_WIDTH
        self.height = PITCH_HEIGHT
        
    def generate(
        self, 
        formation: str, 
        players: List[str], 
        team_name: str,
        is_home: bool = True,
        output_path: str = None,
        player_numbers: dict = None
    ) -> Optional[str]:
        """
        Generate a formation diagram image.
        
        Args:
            formation: Formation string like "4-3-3"
            players: List of 11 player names (GK first)
            team_name: Team name for title
            is_home: True for home team (blue), False for away (red)
            output_path: Path to save the image
            
        Returns:
            Path to generated image, or None on error
        """
        if not output_path:
            return None
            
        try:
            # Create base pitch image
            img = self._create_pitch()
            draw = ImageDraw.Draw(img)
            
            # Get layout for this formation
            layout = self._get_layout(formation)
            if not layout:
                logger.warning(f"Unknown formation: {formation}, using 4-4-2")
                layout = FORMATION_LAYOUTS["4-4-2"]
            
            # Place players
            player_bg = PLAYER_BG_HOME if is_home else PLAYER_BG_AWAY
            player_idx = 0
            
            for line_y_ratio, num_players in layout:
                y = int(self.height * line_y_ratio)
                x_positions = self._distribute_x(num_players)
                
                for x in x_positions:
                    if player_idx < len(players):
                        name = players[player_idx]
                        number = None
                        if player_numbers:
                            number = player_numbers.get(name)
                        self._draw_player(draw, x, y, name, player_bg, number)
                        player_idx += 1
            
            # Add team name and formation title
            self._draw_title(draw, f"{team_name} （{formation}）", is_home)
            
            # Save image
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path)
            logger.info(f"Formation image saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating formation image: {e}")
            return None
    
    def _create_pitch(self) -> Image.Image:
        """Create a basic pitch background"""
        img = Image.new('RGB', (self.width, self.height), PITCH_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Draw pitch lines
        margin = 20
        # Outer boundary
        draw.rectangle(
            [margin, margin, self.width - margin, self.height - margin],
            outline=LINE_COLOR, width=2
        )
        # Center line
        center_y = self.height // 2
        draw.line([(margin, center_y), (self.width - margin, center_y)], 
                  fill=LINE_COLOR, width=2)
        # Center circle
        circle_radius = 35
        draw.ellipse(
            [self.width//2 - circle_radius, center_y - circle_radius,
             self.width//2 + circle_radius, center_y + circle_radius],
            outline=LINE_COLOR, width=2
        )
        # Penalty areas
        penalty_width = 130
        penalty_height = 55
        # Top penalty area
        draw.rectangle(
            [self.width//2 - penalty_width//2, margin,
             self.width//2 + penalty_width//2, margin + penalty_height],
            outline=LINE_COLOR, width=2
        )
        # Bottom penalty area
        draw.rectangle(
            [self.width//2 - penalty_width//2, self.height - margin - penalty_height,
             self.width//2 + penalty_width//2, self.height - margin],
            outline=LINE_COLOR, width=2
        )
        
        return img
    
    def _get_layout(self, formation: str) -> Optional[List[Tuple[float, int]]]:
        """Get layout for a formation string"""
        # Normalize formation string
        formation = formation.strip().replace(" ", "")
        return FORMATION_LAYOUTS.get(formation)
    
    def _distribute_x(self, num_players: int) -> List[int]:
        """Calculate X positions for players in a line"""
        margin = 50
        available_width = self.width - 2 * margin
        
        if num_players == 1:
            return [self.width // 2]
        
        spacing = available_width // (num_players - 1)
        return [margin + i * spacing for i in range(num_players)]
    
    def _draw_player(self, draw: ImageDraw.Draw, x: int, y: int, 
                     name: str, bg_color: tuple, number: int = None):
        """Draw a player circle with name and optional jersey number"""
        # Draw circle
        draw.ellipse(
            [x - PLAYER_RADIUS, y - PLAYER_RADIUS, 
             x + PLAYER_RADIUS, y + PLAYER_RADIUS],
            fill=bg_color, outline=PLAYER_COLOR, width=2
        )
        
        # Draw jersey number inside circle (if available)
        if number is not None:
            number_font = self._get_font(11)
            number_str = str(number)
            bbox = draw.textbbox((0, 0), number_str, font=number_font)
            num_width = bbox[2] - bbox[0]
            num_height = bbox[3] - bbox[1]
            draw.text(
                (x - num_width // 2, y - num_height // 2 - 2),
                number_str, fill=PLAYER_COLOR, font=number_font
            )
        
        # Draw name (shortened) below circle
        short_name = self._shorten_name(name)
        font = self._get_font(12)
            
        # Get text bounding box
        bbox = draw.textbbox((0, 0), short_name, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = x - text_width // 2
        text_y = y + PLAYER_RADIUS + 5
        
        draw.text((text_x, text_y), short_name, fill=PLAYER_COLOR, font=font)
    
    def _get_font(self, size: int):
        """Get font with fallback for different OS"""
        font_paths = [
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # Mac
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        # Ultimate fallback - use default but note it won't scale
        return ImageFont.load_default()
    
    def _shorten_name(self, name: str) -> str:
        """Shorten player name to fit in display"""
        parts = name.split()
        if len(parts) == 1:
            return name[:10]
        # Return first initial + last name
        return f"{parts[0][0]}. {parts[-1][:8]}"
    
    def _draw_title(self, draw: ImageDraw.Draw, title: str, is_home: bool):
        """Draw title at top of image"""
        font = self._get_font(18)
            
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.width - text_width) // 2
        y = 5
        
        color = PLAYER_BG_HOME if is_home else PLAYER_BG_AWAY
        draw.rectangle([x - 8, y - 4, x + text_width + 8, y + text_height + 4], fill=color)
        draw.text((x, y), title, fill=PLAYER_COLOR, font=font)


def distribute_x_percent(num_players: int) -> List[float]:
    """Calculate X positions as percentages (0-100)"""
    # Default margin for standard layouts
    margin_percent = 12.0
    
    # 2 Players: More centered (35% margin as requested)
    if num_players == 2:
        margin_percent = 35.0
        
    available_percent = 100.0 - 2 * margin_percent
    
    if num_players == 1:
        return [50.0]
    
    spacing = available_percent / (num_players - 1)
    positions = [margin_percent + i * spacing for i in range(num_players)]

    # 3 or 4 Players: Only adjust outer positions by ±1.5%
    if num_players in [3, 4]:
        positions[0] += 1.5  # Left-most moves right
        positions[-1] -= 1.5  # Right-most moves left
    
    return positions

# Country name to ISO Alpha-2 code mapping (for flagcdn)
COUNTRY_TO_ISO = {
    "Spain": "es",
    "England": "gb-eng",
    "France": "fr",
    "Germany": "de",
    "Italy": "it",
    "Portugal": "pt",
    "Brazil": "br",
    "Argentina": "ar",
    "Netherlands": "nl",
    "Belgium": "be",
    "Japan": "jp",
    "South Korea": "kr",
    "Norway": "no",
    "Sweden": "se",
    "Denmark": "dk",
    "Croatia": "hr",
    "Switzerland": "ch",
    "Uruguay": "uy",
    "Colombia": "co",
    "Senegal": "sn",
    "Nigeria": "ng",
    "Egypt": "eg",
    "Morocco": "ma",
    "Ukraine": "ua",
    "Poland": "pl",
    "Scotland": "gb-sct",
    "Wales": "gb-wls",
    "Northern Ireland": "gb-nir",
    "Ireland": "ie",
    "USA": "us",
    "Canada": "ca",
    "Mexico": "mx",
    "Australia": "au",
}

def get_formation_layout_data(
    formation: str,
    players: List[str],
    team_name: str,
    team_logo: str,
    team_color: str,
    is_home: bool,
    player_nationalities: Dict[str, str],
    player_numbers: Dict[str, int],
    player_photos: Dict[str, str],
    player_short_names: Dict[str, str] = None  # New argument
) -> Dict:
    """
    Get formation layout data for HTML rendering.
    """
    # Normalize formation string
    fmt = formation.strip().replace(" ", "")
    layout = FORMATION_LAYOUTS.get(fmt)
    if not layout:
        logger.warning(f"Unknown formation: {formation}, using 4-4-2")
        layout = FORMATION_LAYOUTS["4-4-2"]
    
    player_data = []
    player_idx = 0
    
    for line_y_ratio, num_players in layout:
        base_top_percent = line_y_ratio * 100
        x_percents = distribute_x_percent(num_players)
        
        # 5 Player W-shape logic
        # 2nd and 4th players slightly up (-3%), others slightly down (+3%)
        y_offsets = [0.0] * num_players
        if num_players == 5:
            for i in range(num_players):
                if i in [1, 3]:  # 2nd (index 1) and 4th (index 3)
                    y_offsets[i] = -3.0
                else:
                    y_offsets[i] = 3.0
        
        for i, left_percent in enumerate(x_percents):
            if player_idx < len(players):
                name = players[player_idx]
                nationality_name = player_nationalities.get(name, "")
                nationality_code = COUNTRY_TO_ISO.get(nationality_name, "")
                # Generate full flag URL in Python (avoid Jinja2 filter issues)
                flag_url = f"https://flagcdn.com/{nationality_code}.svg" if nationality_code else ""
                
                # Use provided short name, fallback to manual shortening if not provided
                short_name = name
                if player_short_names and name in player_short_names:
                    short_name = player_short_names[name]
                else:
                    # Fallback manual shortening logic
                    parts = name.split()
                    if len(parts) > 1:
                        short_name = f"{parts[0][0]}. {parts[-1][:8]}"
                
                player_data.append({
                    "name": name,
                    "short_name": short_name,  # New field
                    "number": player_numbers.get(name, ""),
                    "photo": player_photos.get(name, ""),
                    "nationality": nationality_code,
                    "flag_url": flag_url,
                    "top_percent": round(base_top_percent + y_offsets[i], 1),
                    "left_percent": round(left_percent, 1)
                })
                player_idx += 1
    
    return {
        "team_name": team_name,
        "team_logo": team_logo,
        "team_color": team_color,
        "formation": formation,
        "is_home": is_home,
        "players": player_data
    }

def generate_formation_image(
    formation: str,
    players: List[str],
    team_name: str,
    is_home: bool,
    output_dir: str,
    match_id: str,
    player_numbers: dict = None
) -> Optional[str]:
    """
    Generate formation image and return relative path for markdown.
    (Legacy function, will be replaced by get_formation_layout_data)
    """
    suffix = "home" if is_home else "away"
    filename = f"{match_id}_{suffix}.png"
    output_path = os.path.join(output_dir, "images", filename)
    
    generator = FormationImageGenerator()
    result = generator.generate(formation, players, team_name, is_home, output_path, player_numbers)
    
    if result:
        return f"images/{filename}"
    return None
