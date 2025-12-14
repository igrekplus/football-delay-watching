"""
Formation Image Generator
Generates formation diagram images using Pillow (PIL)
"""

from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional
import os
import logging

logger = logging.getLogger(__name__)

# Pitch dimensions (pixels)
PITCH_WIDTH = 800
PITCH_HEIGHT = 600
PITCH_COLOR = (34, 139, 34)  # Forest green
LINE_COLOR = (255, 255, 255)  # White
PLAYER_COLOR = (255, 255, 255)
PLAYER_BG_HOME = (0, 0, 139)  # Dark blue
PLAYER_BG_AWAY = (139, 0, 0)  # Dark red
PLAYER_RADIUS = 20

# Formation layouts - define Y positions for each line (0.0 = goal, 1.0 = midfield)
# Each formation maps to list of (line_y_ratio, num_players) 
FORMATION_LAYOUTS = {
    # 4 defenders
    "4-3-3": [(0.15, 1), (0.35, 4), (0.55, 3), (0.80, 3)],
    "4-4-2": [(0.15, 1), (0.35, 4), (0.55, 4), (0.80, 2)],
    "4-2-3-1": [(0.12, 1), (0.30, 4), (0.48, 2), (0.68, 3), (0.88, 1)],
    "4-1-4-1": [(0.15, 1), (0.35, 4), (0.45, 1), (0.60, 4), (0.85, 1)],
    "4-5-1": [(0.15, 1), (0.35, 4), (0.55, 5), (0.80, 1)],
    "4-4-1-1": [(0.15, 1), (0.35, 4), (0.50, 4), (0.70, 1), (0.85, 1)],
    # 3 defenders
    "3-4-3": [(0.15, 1), (0.35, 3), (0.55, 4), (0.80, 3)],
    "3-5-2": [(0.15, 1), (0.35, 3), (0.55, 5), (0.80, 2)],
    "3-4-2-1": [(0.12, 1), (0.28, 3), (0.48, 4), (0.70, 2), (0.90, 1)],
    "3-4-1-2": [(0.15, 1), (0.35, 3), (0.50, 4), (0.65, 1), (0.85, 2)],
    # 5 defenders
    "5-3-2": [(0.15, 1), (0.35, 5), (0.55, 3), (0.80, 2)],
    "5-4-1": [(0.15, 1), (0.35, 5), (0.55, 4), (0.80, 1)],
    "5-2-3": [(0.15, 1), (0.35, 5), (0.55, 2), (0.80, 3)],
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
        output_path: str = None
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
                        self._draw_player(draw, x, y, name, player_bg)
                        player_idx += 1
            
            # Add team name and formation title
            self._draw_title(draw, f"{team_name} ({formation})", is_home)
            
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
        margin = 30
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
        circle_radius = 50
        draw.ellipse(
            [self.width//2 - circle_radius, center_y - circle_radius,
             self.width//2 + circle_radius, center_y + circle_radius],
            outline=LINE_COLOR, width=2
        )
        # Penalty areas
        penalty_width = 200
        penalty_height = 80
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
        margin = 80
        available_width = self.width - 2 * margin
        
        if num_players == 1:
            return [self.width // 2]
        
        spacing = available_width // (num_players - 1)
        return [margin + i * spacing for i in range(num_players)]
    
    def _draw_player(self, draw: ImageDraw.Draw, x: int, y: int, 
                     name: str, bg_color: tuple):
        """Draw a player circle with name"""
        # Draw circle
        draw.ellipse(
            [x - PLAYER_RADIUS, y - PLAYER_RADIUS, 
             x + PLAYER_RADIUS, y + PLAYER_RADIUS],
            fill=bg_color, outline=PLAYER_COLOR, width=2
        )
        
        # Draw name (shortened)
        short_name = self._shorten_name(name)
        font = self._get_font(18)
            
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
        font = self._get_font(24)
            
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.width - text_width) // 2
        y = 5
        
        color = PLAYER_BG_HOME if is_home else PLAYER_BG_AWAY
        draw.rectangle([x - 8, y - 4, x + text_width + 8, y + text_height + 4], fill=color)
        draw.text((x, y), title, fill=PLAYER_COLOR, font=font)


# Utility function for easy use
def generate_formation_image(
    formation: str,
    players: List[str],
    team_name: str,
    is_home: bool,
    output_dir: str,
    match_id: str
) -> Optional[str]:
    """
    Generate formation image and return relative path for markdown.
    
    Returns:
        Relative path like "images/match_id_home.png" or None on error
    """
    suffix = "home" if is_home else "away"
    filename = f"{match_id}_{suffix}.png"
    output_path = os.path.join(output_dir, "images", filename)
    
    generator = FormationImageGenerator()
    result = generator.generate(formation, players, team_name, is_home, output_path)
    
    if result:
        return f"images/{filename}"
    return None
