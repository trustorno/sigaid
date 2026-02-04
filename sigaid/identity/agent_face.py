"""AgentFace v5 - Matrix/Holographic Visual Identity for AI Agents.

Generates unique, stunning face visualizations with 2+ TRILLION
human-distinguishable combinations through expanded feature categories:

- 20 color palettes
- 12 face shapes
- 16 eye styles × 8 expressions
- 14 mouth styles
- 16 crown/top features
- 12 forehead markings
- 10 cheek patterns
- 8 chin features
- 10 side accessories
- 6 background styles
- 6 aura effects

Total: ~2.4 trillion distinct human-recognizable faces

Each face is deterministically derived from the agent's cryptographic key,
ensuring the same key always produces the same unique face.

Usage:
    from sigaid.identity.agent_face import AgentFace

    face = AgentFace.from_public_key(public_key_bytes)
    svg = face.to_svg(animated=True)
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from pathlib import Path


# =============================================================================
# FEATURE DEFINITIONS - 2.4 TRILLION combinations
# =============================================================================

# 20 Color Palettes
PALETTES = [
    # Original 16
    {"name": "Cyan", "primary": "#00f5ff", "secondary": "#0088aa", "accent": "#00ff88", "glow": "#00f5ff", "bg": "#0a0a12"},
    {"name": "Matrix", "primary": "#00ff41", "secondary": "#008f11", "accent": "#88ff88", "glow": "#00ff41", "bg": "#0a0f0a"},
    {"name": "Purple", "primary": "#bf00ff", "secondary": "#6600aa", "accent": "#ff00ff", "glow": "#bf00ff", "bg": "#0f0a12"},
    {"name": "Gold", "primary": "#ffd700", "secondary": "#ff8c00", "accent": "#ffee88", "glow": "#ffd700", "bg": "#12100a"},
    {"name": "Ice", "primary": "#88ddff", "secondary": "#4499cc", "accent": "#ffffff", "glow": "#88ddff", "bg": "#0a0c10"},
    {"name": "Rose", "primary": "#ff0080", "secondary": "#aa0055", "accent": "#ff88bb", "glow": "#ff0080", "bg": "#120a0c"},
    {"name": "Emerald", "primary": "#00ff88", "secondary": "#00aa55", "accent": "#88ffcc", "glow": "#00ff88", "bg": "#0a100c"},
    {"name": "Violet", "primary": "#8800ff", "secondary": "#5500aa", "accent": "#bb88ff", "glow": "#8800ff", "bg": "#0c0a12"},
    {"name": "Blood", "primary": "#ff2222", "secondary": "#aa0000", "accent": "#ff8888", "glow": "#ff2222", "bg": "#120a0a"},
    {"name": "Solar", "primary": "#ffaa00", "secondary": "#ff6600", "accent": "#ffdd44", "glow": "#ffaa00", "bg": "#12100a"},
    {"name": "Arctic", "primary": "#aaeeff", "secondary": "#66bbdd", "accent": "#ffffff", "glow": "#aaeeff", "bg": "#0a0e12"},
    {"name": "Toxic", "primary": "#aaff00", "secondary": "#66aa00", "accent": "#ddff66", "glow": "#aaff00", "bg": "#0c100a"},
    {"name": "Sunset", "primary": "#ff6644", "secondary": "#cc3366", "accent": "#ffaa88", "glow": "#ff6644", "bg": "#120c0a"},
    {"name": "Midnight", "primary": "#4466ff", "secondary": "#2233aa", "accent": "#8899ff", "glow": "#4466ff", "bg": "#0a0a14"},
    {"name": "Chrome", "primary": "#cccccc", "secondary": "#888888", "accent": "#ffffff", "glow": "#cccccc", "bg": "#101010"},
    {"name": "Plasma", "primary": "#ff00ff", "secondary": "#00ffff", "accent": "#ff88ff", "glow": "#ff00ff", "bg": "#0f0a10"},
    # New 4
    {"name": "Neon", "primary": "#ff00aa", "secondary": "#ffff00", "accent": "#00ffaa", "glow": "#ff00aa", "bg": "#0a0808"},
    {"name": "Ocean", "primary": "#0066cc", "secondary": "#004488", "accent": "#00aaff", "glow": "#0088ff", "bg": "#080a10"},
    {"name": "Lava", "primary": "#ff4400", "secondary": "#cc2200", "accent": "#ffaa00", "glow": "#ff6600", "bg": "#100808"},
    {"name": "Void", "primary": "#6633aa", "secondary": "#331166", "accent": "#9966ff", "glow": "#7744cc", "bg": "#08060c"},
]

# 12 Face Shapes
FACE_SHAPES = [
    "oval", "angular", "hexagonal", "diamond", "shield", "heart", "octagonal", "rounded_square",
    "pentagon", "triangle", "pill", "star"
]

# 16 Eye Styles
EYE_STYLES = [
    "holo_ring", "matrix_scan", "data_orb", "cyber_lens", "visor_bar", "split_iris",
    "compound", "target_lock", "energy_slit", "binary_dots", "spiral", "crosshair",
    "scanner_bar", "diamond_core", "pixel_grid", "flame_eye"
]

# 8 Eye Expressions
EYE_EXPRESSIONS = ["neutral", "wide", "narrow", "tilt_up", "tilt_down", "asymmetric", "squint", "shock"]

# 14 Mouth Styles
MOUTH_STYLES = [
    "data_stream", "waveform", "minimal", "grid", "vent", "speaker", "binary",
    "smile_arc", "glyph", "silent", "pixel_smile", "teeth_grid", "equalizer", "circuit_mouth"
]

# 16 Crown/Top Features
CROWN_STYLES = [
    "none", "antenna_single", "antenna_dual", "horns", "halo", "mohawk_data",
    "floating_orbs", "energy_spikes", "circuit_crown", "visor_top", "flames", "crystals",
    "crown_peaks", "satellite", "wings", "data_cloud"
]

# 12 Forehead Markings
FOREHEAD_MARKS = [
    "none", "third_eye", "symbol_circle", "barcode", "circuit_node", "gem",
    "scanner_line", "binary_row", "hexagon", "omega", "cross", "infinity"
]

# 10 Cheek Patterns
CHEEK_PATTERNS = [
    "none", "circuit_lines", "tribal_bars", "dots", "vents", "data_ports",
    "scars", "glyphs", "binary_stream", "wave_lines"
]

# 8 Chin Features
CHIN_FEATURES = ["none", "vent", "light_bar", "beard_lines", "energy_core", "port", "speaker_grille", "data_jack"]

# 10 Side Accessories
SIDE_ACCESSORIES = [
    "none", "earpiece_left", "earpiece_right", "earpiece_both", "antenna_side",
    "blade", "coil", "jack", "wing_fins", "data_nodes"
]

# 6 Background Styles
BG_STYLES = ["data_rain", "hex_grid", "circuit", "particles", "void", "matrix_code"]

# 6 Aura Effects
AURA_STYLES = ["glow", "double_ring", "glitch", "holographic", "pulse", "electric"]

# Matrix characters
MATRIX_CHARS = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF"

# Symbols for markings
SYMBOLS = ["◯", "△", "□", "◇", "⬡", "✦", "⚡", "Ω", "Δ", "Ψ", "∞", "⊕", "✕", "☆"]


@dataclass
class FaceParams:
    """All parameters extracted from key bytes for face generation."""
    # Core identity (bytes 0-3)
    palette_idx: int
    face_shape: int
    eye_style: int
    eye_expression: int

    # Face features (bytes 4-7)
    mouth_style: int
    crown_style: int
    forehead_mark: int
    cheek_pattern: int

    # Additional features (bytes 8-11)
    chin_feature: int
    side_accessory: int
    bg_style: int
    aura_style: int

    # Continuous variations (bytes 12-19)
    face_width: float
    face_height: float
    eye_size: float
    eye_spacing: float
    mouth_width: float
    crown_size: float
    mark_size: float
    accessory_size: float

    # Effects (bytes 20-23)
    glow_intensity: float
    animation_speed: float
    glitch_amount: float
    particle_density: int

    # Seeds for randomization (bytes 24-31)
    pattern_seed: int
    circuit_seed: int
    particle_seed: int
    effect_seed: int


class AgentFace:
    """Generates Matrix/Holographic face with 2+ TRILLION unique combinations."""

    CANVAS_SIZE = 200
    CENTER = CANVAS_SIZE // 2

    def __init__(self, key_bytes: bytes):
        """Initialize from raw key bytes (32 bytes)."""
        if len(key_bytes) < 32:
            key_bytes = hashlib.blake2b(key_bytes, digest_size=32).digest()

        self._key_bytes = key_bytes[:32]
        self._params = self._extract_params()
        self._rng = random.Random(int.from_bytes(key_bytes[:8], 'big'))

    @classmethod
    def from_public_key(cls, public_key: bytes) -> AgentFace:
        """Create from Ed25519 public key."""
        return cls(public_key)

    @classmethod
    def from_agent_id(cls, agent_id: str) -> AgentFace:
        """Create from agent ID string."""
        from sigaid.identity.agent_id import AgentID
        aid = AgentID(agent_id)
        return cls(aid.to_public_key_bytes())

    def _byte_to_range(self, byte_val: int, min_v: float, max_v: float) -> float:
        """Map byte value to range."""
        return min_v + (byte_val / 255) * (max_v - min_v)

    def _extract_params(self) -> FaceParams:
        """Extract face parameters from key bytes."""
        b = self._key_bytes

        return FaceParams(
            palette_idx=b[0] % len(PALETTES),
            face_shape=b[1] % len(FACE_SHAPES),
            eye_style=b[2] % len(EYE_STYLES),
            eye_expression=b[3] % len(EYE_EXPRESSIONS),
            mouth_style=b[4] % len(MOUTH_STYLES),
            crown_style=b[5] % len(CROWN_STYLES),
            forehead_mark=b[6] % len(FOREHEAD_MARKS),
            cheek_pattern=b[7] % len(CHEEK_PATTERNS),
            chin_feature=b[8] % len(CHIN_FEATURES),
            side_accessory=b[9] % len(SIDE_ACCESSORIES),
            bg_style=b[10] % len(BG_STYLES),
            aura_style=b[11] % len(AURA_STYLES),
            face_width=self._byte_to_range(b[12], 50, 70),
            face_height=self._byte_to_range(b[13], 65, 85),
            eye_size=self._byte_to_range(b[14], 10, 20),
            eye_spacing=self._byte_to_range(b[15], 22, 38),
            mouth_width=self._byte_to_range(b[16], 18, 40),
            crown_size=self._byte_to_range(b[17], 0.7, 1.3),
            mark_size=self._byte_to_range(b[18], 0.7, 1.3),
            accessory_size=self._byte_to_range(b[19], 0.8, 1.2),
            glow_intensity=self._byte_to_range(b[20], 0.5, 1.0),
            animation_speed=self._byte_to_range(b[21], 1.5, 3.5),
            glitch_amount=self._byte_to_range(b[22], 0.1, 0.3),
            particle_density=int(self._byte_to_range(b[23], 8, 20)),
            pattern_seed=int.from_bytes(b[24:26], 'big'),
            circuit_seed=int.from_bytes(b[26:28], 'big'),
            particle_seed=int.from_bytes(b[28:30], 'big'),
            effect_seed=int.from_bytes(b[30:32], 'big'),
        )

    def _get_palette(self) -> dict:
        """Get color palette."""
        return PALETTES[self._params.palette_idx]

    def to_svg(self, size: int = 200, animated: bool = True) -> str:
        """Generate the complete face SVG."""
        p = self._params
        c = self.CENTER
        palette = self._get_palette()

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.CANVAS_SIZE} {self.CANVAS_SIZE}" width="{size}" height="{size}">'
        ]

        svg_parts.append(self._create_defs(palette))
        if animated:
            svg_parts.append(self._create_animations(palette))

        svg_parts.append(self._draw_background(palette))
        svg_parts.append(self._draw_aura(c, palette, animated))

        if CROWN_STYLES[p.crown_style] in ["halo", "flames", "data_cloud"]:
            svg_parts.append(self._draw_crown(c, palette, animated))

        svg_parts.append(self._draw_face(c, palette, animated))
        svg_parts.append(self._draw_forehead_mark(c, palette, animated))
        svg_parts.append(self._draw_eyes(c, palette, animated))
        svg_parts.append(self._draw_cheeks(c, palette, animated))
        svg_parts.append(self._draw_mouth(c, palette, animated))
        svg_parts.append(self._draw_chin(c, palette, animated))
        svg_parts.append(self._draw_side_accessories(c, palette, animated))

        if CROWN_STYLES[p.crown_style] not in ["none", "halo", "flames", "data_cloud"]:
            svg_parts.append(self._draw_crown(c, palette, animated))

        if animated:
            svg_parts.append(self._draw_scan_overlay(palette))

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _create_defs(self, palette: dict) -> str:
        """Create SVG defs."""
        primary = palette["primary"]
        secondary = palette["secondary"]
        glow = palette["glow"]

        return f'''
<defs>
    <linearGradient id="face-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="{primary}" stop-opacity="0.2"/>
        <stop offset="50%" stop-color="{secondary}" stop-opacity="0.1"/>
        <stop offset="100%" stop-color="{primary}" stop-opacity="0.2"/>
    </linearGradient>
    <radialGradient id="face-glass" cx="30%" cy="30%" r="70%">
        <stop offset="0%" stop-color="white" stop-opacity="0.25"/>
        <stop offset="50%" stop-color="{primary}" stop-opacity="0.1"/>
        <stop offset="100%" stop-color="{secondary}" stop-opacity="0.05"/>
    </radialGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow-strong" x="-100%" y="-100%" width="300%" height="300%">
        <feGaussianBlur stdDeviation="6" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="blur"/><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glitch">
        <feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r"/>
        <feOffset in="r" dx="2" dy="0" result="r-shift"/>
        <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="b"/>
        <feOffset in="b" dx="-2" dy="0" result="b-shift"/>
        <feBlend in="r-shift" in2="SourceGraphic" mode="screen" result="rg"/>
        <feBlend in="rg" in2="b-shift" mode="screen"/>
    </filter>
</defs>'''

    def _create_animations(self, palette: dict) -> str:
        """Create CSS animations."""
        p = self._params
        speed = p.animation_speed
        glow = palette["glow"]

        return f'''
<style>
    @keyframes pulse {{ 0%, 100% {{ opacity: 0.7; }} 50% {{ opacity: 1; }} }}
    @keyframes glow-pulse {{ 0%, 100% {{ filter: drop-shadow(0 0 4px {glow}); }} 50% {{ filter: drop-shadow(0 0 12px {glow}); }} }}
    @keyframes float {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-4px); }} }}
    @keyframes rotate {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    @keyframes glitch {{ 0%, 92%, 100% {{ transform: translate(0); }} 94% {{ transform: translate(-2px, 1px); }} 96% {{ transform: translate(2px, -1px); }} 98% {{ transform: translate(-1px, -1px); }} }}
    @keyframes flicker {{ 0%, 90%, 100% {{ opacity: 1; }} 92% {{ opacity: 0.8; }} 96% {{ opacity: 0.7; }} }}
    @keyframes data-fall {{ 0% {{ transform: translateY(-20px); opacity: 0; }} 10% {{ opacity: 0.8; }} 90% {{ opacity: 0.8; }} 100% {{ transform: translateY(220px); opacity: 0; }} }}
    @keyframes electric {{ 0%, 100% {{ opacity: 0.6; }} 25% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 75% {{ opacity: 0.9; }} }}
    @keyframes flame {{ 0%, 100% {{ transform: scaleY(1) translateY(0); }} 50% {{ transform: scaleY(1.1) translateY(-2px); }} }}
    .pulse {{ animation: pulse {speed}s ease-in-out infinite; }}
    .glow-pulse {{ animation: glow-pulse {speed}s ease-in-out infinite; }}
    .float {{ animation: float {speed * 1.5}s ease-in-out infinite; }}
    .rotate {{ animation: rotate {speed * 4}s linear infinite; }}
    .glitch {{ animation: glitch {speed * 5}s steps(1) infinite; }}
    .flicker {{ animation: flicker {speed * 3}s steps(1) infinite; }}
    .electric {{ animation: electric {speed * 0.5}s steps(2) infinite; }}
    .flame {{ animation: flame {speed * 0.8}s ease-in-out infinite; }}
</style>'''

    def _draw_background(self, palette: dict) -> str:
        """Draw background based on style."""
        p = self._params
        bg_style = BG_STYLES[p.bg_style]
        primary = palette["primary"]
        bg_color = palette["bg"]

        parts = [f'<rect width="{self.CANVAS_SIZE}" height="{self.CANVAS_SIZE}" fill="{bg_color}"/>']

        if bg_style == "data_rain":
            self._rng.seed(p.particle_seed)
            for i in range(p.particle_density):
                x = self._rng.randint(5, self.CANVAS_SIZE - 5)
                delay = self._rng.uniform(0, 5)
                duration = self._rng.uniform(3, 6)
                char = self._rng.choice(MATRIX_CHARS)
                parts.append(
                    f'<text x="{x}" y="0" fill="{primary}" font-family="monospace" font-size="10" opacity="0.5"'
                    f' style="animation: data-fall {duration}s linear {delay}s infinite;">{char}</text>'
                )

        elif bg_style == "hex_grid":
            for y in range(-10, self.CANVAS_SIZE + 20, 30):
                offset = 17 if (y // 30) % 2 else 0
                for x in range(-10 + offset, self.CANVAS_SIZE + 20, 34):
                    parts.append(
                        f'<polygon points="{x},{y-10} {x+8},{y-5} {x+8},{y+5} {x},{y+10} {x-8},{y+5} {x-8},{y-5}"'
                        f' fill="none" stroke="{primary}" stroke-width="0.5" opacity="0.1"/>'
                    )

        elif bg_style == "circuit":
            self._rng.seed(p.circuit_seed)
            for i in range(12):
                x1 = self._rng.randint(0, self.CANVAS_SIZE)
                y1 = self._rng.randint(0, self.CANVAS_SIZE)
                x2 = x1 + self._rng.choice([-40, -20, 20, 40])
                y2 = y1
                x3 = x2
                y3 = y2 + self._rng.choice([-40, -20, 20, 40])
                parts.append(f'<path d="M{x1},{y1} L{x2},{y2} L{x3},{y3}" fill="none" stroke="{primary}" stroke-width="1" opacity="0.15"/>')
                parts.append(f'<circle cx="{x3}" cy="{y3}" r="2" fill="{primary}" opacity="0.2"/>')

        elif bg_style == "particles":
            self._rng.seed(p.particle_seed)
            for i in range(p.particle_density * 2):
                x = self._rng.randint(5, self.CANVAS_SIZE - 5)
                y = self._rng.randint(5, self.CANVAS_SIZE - 5)
                size = self._rng.uniform(1, 3)
                delay = self._rng.uniform(0, 3)
                parts.append(f'<circle cx="{x}" cy="{y}" r="{size}" fill="{primary}" opacity="0.3" class="float" style="animation-delay: {delay}s;"/>')

        elif bg_style == "matrix_code":
            self._rng.seed(p.particle_seed)
            for i in range(p.particle_density + 8):
                x = self._rng.randint(5, self.CANVAS_SIZE - 5)
                delay = self._rng.uniform(0, 4)
                duration = self._rng.uniform(2.5, 5)
                col_height = self._rng.randint(3, 6)
                for j in range(col_height):
                    char = self._rng.choice(MATRIX_CHARS)
                    opacity = 0.8 - j * 0.15
                    parts.append(
                        f'<text x="{x}" y="{j * 12}" fill="{primary}" font-family="monospace" font-size="9" opacity="{opacity}"'
                        f' style="animation: data-fall {duration}s linear {delay + j * 0.1}s infinite;">{char}</text>'
                    )

        return '\n'.join(parts)

    def _draw_aura(self, c: int, palette: dict, animated: bool) -> str:
        """Draw aura effect around face."""
        p = self._params
        aura = AURA_STYLES[p.aura_style]
        primary = palette["primary"]
        glow = palette["glow"]
        secondary = palette["secondary"]
        radius = max(p.face_width, p.face_height) + 12

        anim = 'class="glow-pulse"' if animated else ''

        if aura == "glow":
            return f'<circle cx="{c}" cy="{c}" r="{radius}" fill="none" stroke="{glow}" stroke-width="2" opacity="0.5" {anim} filter="url(#glow)"/>'

        elif aura == "double_ring":
            return f'''<circle cx="{c}" cy="{c}" r="{radius}" fill="none" stroke="{glow}" stroke-width="1.5" opacity="0.5" {anim}/>
<circle cx="{c}" cy="{c}" r="{radius + 6}" fill="none" stroke="{primary}" stroke-width="1" opacity="0.3"/>
<circle cx="{c}" cy="{c}" r="{radius + 12}" fill="none" stroke="{glow}" stroke-width="0.5" opacity="0.2"/>'''

        elif aura == "glitch":
            anim_glitch = 'class="glitch"' if animated else ''
            return f'<g {anim_glitch}><circle cx="{c}" cy="{c}" r="{radius}" fill="none" stroke="{glow}" stroke-width="2" opacity="0.6"/></g>'

        elif aura == "holographic":
            return f'''<circle cx="{c}" cy="{c}" r="{radius}" fill="none" stroke="{primary}" stroke-width="1" opacity="0.4" stroke-dasharray="4 4" {anim}/>
<circle cx="{c}" cy="{c}" r="{radius + 4}" fill="none" stroke="{glow}" stroke-width="0.5" opacity="0.3" stroke-dasharray="2 6"/>
<circle cx="{c}" cy="{c}" r="{radius - 4}" fill="none" stroke="{secondary}" stroke-width="0.5" opacity="0.3" stroke-dasharray="6 2"/>'''

        elif aura == "pulse":
            anim_pulse = 'class="pulse"' if animated else ''
            return f'''<circle cx="{c}" cy="{c}" r="{radius}" fill="none" stroke="{glow}" stroke-width="3" opacity="0.4" {anim_pulse} filter="url(#glow)"/>
<circle cx="{c}" cy="{c}" r="{radius - 3}" fill="none" stroke="{primary}" stroke-width="1" opacity="0.6"/>'''

        else:  # electric
            anim_elec = 'class="electric"' if animated else ''
            parts = [f'<circle cx="{c}" cy="{c}" r="{radius}" fill="none" stroke="{glow}" stroke-width="2" opacity="0.5" {anim_elec}/>']
            self._rng.seed(p.effect_seed)
            for i in range(6):
                angle = i * 60 * math.pi / 180
                x1 = c + radius * math.cos(angle)
                y1 = c + radius * math.sin(angle)
                x2 = c + (radius + 8) * math.cos(angle + 0.1)
                y2 = c + (radius + 8) * math.sin(angle + 0.1)
                x3 = c + (radius + 5) * math.cos(angle - 0.1)
                y3 = c + (radius + 5) * math.sin(angle - 0.1)
                parts.append(f'<path d="M{x1},{y1} L{x2},{y2} L{x3},{y3}" fill="none" stroke="{glow}" stroke-width="1.5" {anim_elec}/>')
            return '\n'.join(parts)

    def _get_face_shape_element(self, c: int, w: float, h: float, palette: dict) -> str:
        """Get face shape SVG element."""
        p = self._params
        shape = FACE_SHAPES[p.face_shape]
        primary = palette["primary"]

        if shape == "oval":
            return f'<ellipse cx="{c}" cy="{c}" rx="{w}" ry="{h}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "angular":
            pts = [(c, c-h), (c+w*0.85, c-h*0.35), (c+w*0.7, c+h*0.65), (c, c+h), (c-w*0.7, c+h*0.65), (c-w*0.85, c-h*0.35)]
            return f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "hexagonal":
            pts = [(c + w * math.cos(math.pi/3 * i - math.pi/2), c + h * math.sin(math.pi/3 * i - math.pi/2)) for i in range(6)]
            return f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "diamond":
            pts = [(c, c-h), (c+w, c), (c, c+h), (c-w, c)]
            return f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "shield":
            return f'<path d="M{c},{c-h} Q{c+w},{c-h*0.5} {c+w},{c+h*0.2} Q{c+w*0.7},{c+h} {c},{c+h} Q{c-w*0.7},{c+h} {c-w},{c+h*0.2} Q{c-w},{c-h*0.5} {c},{c-h}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "heart":
            return f'<path d="M{c},{c-h*0.3} Q{c},{c-h} {c-w*0.5},{c-h} Q{c-w},{c-h} {c-w},{c-h*0.3} Q{c-w},{c+h*0.3} {c},{c+h} Q{c+w},{c+h*0.3} {c+w},{c-h*0.3} Q{c+w},{c-h} {c+w*0.5},{c-h} Q{c},{c-h} {c},{c-h*0.3}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "octagonal":
            d = w * 0.4
            pts = [(c-d, c-h), (c+d, c-h), (c+w, c-d), (c+w, c+d), (c+d, c+h), (c-d, c+h), (c-w, c+d), (c-w, c-d)]
            return f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "rounded_square":
            return f'<rect x="{c-w}" y="{c-h}" width="{w*2}" height="{h*2}" rx="{w*0.25}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "pentagon":
            pts = [(c + w * 0.95 * math.cos(2*math.pi/5 * i - math.pi/2), c + h * 0.95 * math.sin(2*math.pi/5 * i - math.pi/2)) for i in range(5)]
            return f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "triangle":
            pts = [(c, c-h), (c+w, c+h*0.8), (c-w, c+h*0.8)]
            return f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        elif shape == "pill":
            return f'<rect x="{c-w*0.7}" y="{c-h}" width="{w*1.4}" height="{h*2}" rx="{w*0.7}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'
        else:  # star
            pts = []
            for i in range(10):
                angle = math.pi/5 * i - math.pi/2
                r = w if i % 2 == 0 else w * 0.5
                pts.append((c + r * math.cos(angle), c + h/w * r * math.sin(angle)))
            return f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="url(#face-glass)" stroke="{primary}" stroke-width="1.5"/>'

    def _draw_face(self, c: int, palette: dict, animated: bool) -> str:
        """Draw the main face shape."""
        p = self._params
        w, h = p.face_width, p.face_height
        anim = 'class="glitch"' if animated else ''
        return f'<g {anim}>{self._get_face_shape_element(c, w, h, palette)}</g>'

    def _draw_forehead_mark(self, c: int, palette: dict, animated: bool) -> str:
        """Draw forehead marking."""
        p = self._params
        mark = FOREHEAD_MARKS[p.forehead_mark]
        if mark == "none":
            return ''

        primary = palette["primary"]
        glow = palette["glow"]
        y = c - p.face_height * 0.55
        size = 8 * p.mark_size
        anim = 'class="pulse"' if animated else ''

        if mark == "third_eye":
            return f'<circle cx="{c}" cy="{y}" r="{size}" fill="none" stroke="{primary}" stroke-width="1.5" {anim}/><circle cx="{c}" cy="{y}" r="{size*0.4}" fill="{glow}" filter="url(#glow)" {anim}/>'
        elif mark == "symbol_circle":
            symbol = SYMBOLS[p.pattern_seed % len(SYMBOLS)]
            return f'<circle cx="{c}" cy="{y}" r="{size}" fill="none" stroke="{primary}" stroke-width="1"/><text x="{c}" y="{y+3}" text-anchor="middle" fill="{glow}" font-size="{size*1.2}" {anim}>{symbol}</text>'
        elif mark == "barcode":
            lines = [f'<rect x="{c + i*3 - (1 if (p.pattern_seed >> (i+3)) & 1 else 2)/2}" y="{y-size/2}" width="{1 if (p.pattern_seed >> (i+3)) & 1 else 2}" height="{size}" fill="{primary}"/>' for i in range(-3, 4)]
            return f'<g opacity="0.8">{chr(10).join(lines)}</g>'
        elif mark == "circuit_node":
            return f'<circle cx="{c}" cy="{y}" r="{size*0.5}" fill="{glow}" filter="url(#glow)" {anim}/><line x1="{c-size}" y1="{y}" x2="{c-size*0.6}" y2="{y}" stroke="{primary}" stroke-width="1"/><line x1="{c+size*0.6}" y1="{y}" x2="{c+size}" y2="{y}" stroke="{primary}" stroke-width="1"/><line x1="{c}" y1="{y-size}" x2="{c}" y2="{y-size*0.6}" stroke="{primary}" stroke-width="1"/>'
        elif mark == "gem":
            pts = [(c, y-size), (c+size*0.7, y), (c, y+size*0.5), (c-size*0.7, y)]
            return f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="{glow}" opacity="0.6" filter="url(#glow)" {anim}/><polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{primary}" stroke-width="1"/>'
        elif mark == "scanner_line":
            return f'<line x1="{c-size*1.5}" y1="{y}" x2="{c+size*1.5}" y2="{y}" stroke="{glow}" stroke-width="2" filter="url(#glow)" {anim}/><circle cx="{c-size*1.5}" cy="{y}" r="2" fill="{primary}"/><circle cx="{c+size*1.5}" cy="{y}" r="2" fill="{primary}"/>'
        elif mark == "binary_row":
            bits = format(p.pattern_seed % 256, '08b')
            return f'<text x="{c}" y="{y+3}" text-anchor="middle" fill="{primary}" font-family="monospace" font-size="6" {anim}>{bits}</text>'
        elif mark == "hexagon":
            pts = [(c + size*0.8*math.cos(math.pi/3*i - math.pi/2), y + size*0.8*math.sin(math.pi/3*i - math.pi/2)) for i in range(6)]
            return f'<polygon points="{" ".join(f"{x},{py}" for x,py in pts)}" fill="none" stroke="{primary}" stroke-width="1.5" {anim}/><circle cx="{c}" cy="{y}" r="{size*0.3}" fill="{glow}" filter="url(#glow)"/>'
        elif mark == "omega":
            return f'<text x="{c}" y="{y+size*0.4}" text-anchor="middle" fill="{glow}" font-size="{size*2}" filter="url(#glow)" {anim}>Ω</text>'
        elif mark == "cross":
            return f'<line x1="{c-size}" y1="{y}" x2="{c+size}" y2="{y}" stroke="{glow}" stroke-width="2" filter="url(#glow)" {anim}/><line x1="{c}" y1="{y-size}" x2="{c}" y2="{y+size}" stroke="{glow}" stroke-width="2" filter="url(#glow)"/>'
        else:  # infinity
            return f'<text x="{c}" y="{y+size*0.3}" text-anchor="middle" fill="{glow}" font-size="{size*2.5}" filter="url(#glow)" {anim}>∞</text>'

    def _draw_eyes(self, c: int, palette: dict, animated: bool) -> str:
        """Draw eyes based on style and expression."""
        p = self._params
        style = EYE_STYLES[p.eye_style]
        expr = EYE_EXPRESSIONS[p.eye_expression]
        primary = palette["primary"]
        glow = palette["glow"]
        accent = palette["accent"]

        eye_y = c - 5
        left_x = c - p.eye_spacing / 2
        right_x = c + p.eye_spacing / 2
        size = p.eye_size

        # Expression modifiers
        left_mod = right_mod = 0
        size_mod = 1.0
        if expr == "wide":
            size_mod = 1.2
        elif expr == "narrow":
            size_mod = 0.75
        elif expr == "tilt_up":
            left_mod, right_mod = 3, -3
        elif expr == "tilt_down":
            left_mod, right_mod = -3, 3
        elif expr == "asymmetric":
            left_mod = -2
            size_mod = 0.9
        elif expr == "squint":
            size_mod = 0.6
            left_mod, right_mod = 1, -1
        elif expr == "shock":
            size_mod = 1.4

        size *= size_mod
        left_y = eye_y + left_mod
        right_y = eye_y + right_mod
        anim = 'class="pulse"' if animated else ''
        parts = []

        for ex, ey in [(left_x, left_y), (right_x, right_y)]:
            if style == "holo_ring":
                for i in range(3):
                    parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size - i*3}" fill="none" stroke="{primary}" stroke-width="1.5" opacity="{1 - i*0.3}"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size*0.25}" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif style == "matrix_scan":
                w, h = size * 1.4, size * 0.7
                parts.append(f'<rect x="{ex-w/2}" y="{ey-h/2}" width="{w}" height="{h}" fill="none" stroke="{primary}" stroke-width="1.5" rx="2"/>')
                parts.append(f'<line x1="{ex-w/2+3}" y1="{ey}" x2="{ex+w/2-3}" y2="{ey}" stroke="{glow}" stroke-width="2" filter="url(#glow)" {anim}/>')
            elif style == "data_orb":
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size}" fill="{glow}" opacity="0.2" filter="url(#glow)"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size*0.6}" fill="none" stroke="{primary}" stroke-width="1"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size*0.25}" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif style == "cyber_lens":
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size}" fill="rgba(0,0,0,0.4)" stroke="{primary}" stroke-width="1.5"/>')
                parts.append(f'<line x1="{ex-size}" y1="{ey}" x2="{ex+size}" y2="{ey}" stroke="{primary}" stroke-width="0.5" opacity="0.5"/>')
                parts.append(f'<line x1="{ex}" y1="{ey-size}" x2="{ex}" y2="{ey+size}" stroke="{primary}" stroke-width="0.5" opacity="0.5"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="3" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif style == "visor_bar":
                w, h = size * 2, size * 0.5
                parts.append(f'<rect x="{ex-w/2}" y="{ey-h/2}" width="{w}" height="{h}" fill="{glow}" opacity="0.4" filter="url(#glow)" rx="2"/>')
                parts.append(f'<rect x="{ex-w/2}" y="{ey-h/2}" width="{w}" height="{h}" fill="none" stroke="{primary}" stroke-width="1" rx="2"/>')
            elif style == "split_iris":
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size}" fill="none" stroke="{primary}" stroke-width="1.5"/>')
                parts.append(f'<line x1="{ex}" y1="{ey-size}" x2="{ex}" y2="{ey+size}" stroke="{glow}" stroke-width="2" filter="url(#glow)"/>')
                parts.append(f'<circle cx="{ex-size*0.35}" cy="{ey}" r="2" fill="{accent}" {anim}/>')
                parts.append(f'<circle cx="{ex+size*0.35}" cy="{ey}" r="2" fill="{accent}" {anim}/>')
            elif style == "compound":
                for i in range(6):
                    angle = math.pi / 3 * i
                    parts.append(f'<circle cx="{ex + size*0.5*math.cos(angle)}" cy="{ey + size*0.5*math.sin(angle)}" r="{size*0.3}" fill="none" stroke="{primary}" stroke-width="1"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size*0.3}" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif style == "target_lock":
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size}" fill="none" stroke="{primary}" stroke-width="1" stroke-dasharray="4 2"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size*0.5}" fill="none" stroke="{glow}" stroke-width="1.5"/>')
                for angle in [0, 90, 180, 270]:
                    rad = math.radians(angle)
                    parts.append(f'<line x1="{ex + size*0.6*math.cos(rad)}" y1="{ey + size*0.6*math.sin(rad)}" x2="{ex + size*1.1*math.cos(rad)}" y2="{ey + size*1.1*math.sin(rad)}" stroke="{primary}" stroke-width="1.5"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="2" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif style == "energy_slit":
                parts.append(f'<ellipse cx="{ex}" cy="{ey}" rx="{size}" ry="{size*0.3}" fill="{glow}" opacity="0.6" filter="url(#glow)" {anim}/>')
                parts.append(f'<ellipse cx="{ex}" cy="{ey}" rx="{size}" ry="{size*0.3}" fill="none" stroke="{primary}" stroke-width="1.5"/>')
            elif style == "binary_dots":
                bits = format((p.pattern_seed + int(ex)) % 16, '04b')
                for i, bit in enumerate(bits):
                    parts.append(f'<circle cx="{ex + (i-1.5)*size*0.5}" cy="{ey}" r="{size*0.2}" fill="{glow if bit=="1" else "none"}" stroke="{primary}" stroke-width="1"/>')
            elif style == "spiral":
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size}" fill="none" stroke="{primary}" stroke-width="1"/>')
                path = f'M{ex},{ey}' + ''.join(f' L{ex + size*0.1*i/2*math.cos(i*0.5)},{ey + size*0.1*i/2*math.sin(i*0.5)}' for i in range(20))
                parts.append(f'<path d="{path}" fill="none" stroke="{glow}" stroke-width="1.5" filter="url(#glow)" {anim}/>')
            elif style == "crosshair":
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size}" fill="none" stroke="{primary}" stroke-width="1"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size*0.5}" fill="none" stroke="{primary}" stroke-width="0.5"/>')
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    parts.append(f'<line x1="{ex + dx*size*0.6}" y1="{ey + dy*size*0.6}" x2="{ex + dx*size*1.2}" y2="{ey + dy*size*1.2}" stroke="{glow}" stroke-width="1.5"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="2" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif style == "scanner_bar":
                w = size * 2.5
                parts.append(f'<rect x="{ex-w/2}" y="{ey-3}" width="{w}" height="6" fill="{glow}" opacity="0.5" filter="url(#glow)" rx="3" {anim}/>')
                parts.append(f'<rect x="{ex-w/2}" y="{ey-3}" width="{w}" height="6" fill="none" stroke="{primary}" stroke-width="1" rx="3"/>')
            elif style == "diamond_core":
                pts = [(ex, ey-size), (ex+size, ey), (ex, ey+size), (ex-size, ey)]
                parts.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{primary}" stroke-width="1.5"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey}" r="{size*0.3}" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif style == "pixel_grid":
                ps = size * 0.4
                for i in range(-1, 2):
                    for j in range(-1, 2):
                        fill = glow if (i + j) % 2 == 0 else "none"
                        parts.append(f'<rect x="{ex + i*ps - ps/2}" y="{ey + j*ps - ps/2}" width="{ps}" height="{ps}" fill="{fill}" stroke="{primary}" stroke-width="0.5" opacity="0.8"/>')
            else:  # flame_eye
                parts.append(f'<ellipse cx="{ex}" cy="{ey}" rx="{size*0.8}" ry="{size}" fill="{glow}" opacity="0.3" filter="url(#glow)" class="flame"/>')
                parts.append(f'<ellipse cx="{ex}" cy="{ey+size*0.2}" rx="{size*0.5}" ry="{size*0.7}" fill="{glow}" opacity="0.5" class="flame"/>')
                parts.append(f'<circle cx="{ex}" cy="{ey+size*0.3}" r="{size*0.25}" fill="{accent}" filter="url(#glow)" {anim}/>')

        return f'<g class="eyes">{chr(10).join(parts)}</g>'

    def _draw_cheeks(self, c: int, palette: dict, animated: bool) -> str:
        """Draw cheek patterns."""
        p = self._params
        pattern = CHEEK_PATTERNS[p.cheek_pattern]
        if pattern == "none":
            return ''

        primary = palette["primary"]
        glow = palette["glow"]
        y = c + 5
        left_x = c - p.face_width * 0.6
        right_x = c + p.face_width * 0.6
        parts = []
        anim = 'class="pulse"' if animated else ''

        for cx in [left_x, right_x]:
            mirror = -1 if cx < c else 1
            if pattern == "circuit_lines":
                parts.append(f'<path d="M{cx},{y-8} L{cx+mirror*10},{y-8} L{cx+mirror*10},{y+8} L{cx+mirror*5},{y+8}" fill="none" stroke="{primary}" stroke-width="1" opacity="0.7"/>')
                parts.append(f'<circle cx="{cx+mirror*5}" cy="{y+8}" r="2" fill="{glow}" filter="url(#glow)"/>')
            elif pattern == "tribal_bars":
                for i in range(3):
                    parts.append(f'<line x1="{cx}" y1="{y-6+i*6}" x2="{cx+mirror*12}" y2="{y-6+i*6}" stroke="{primary}" stroke-width="2" opacity="{0.9-i*0.2}"/>')
            elif pattern == "dots":
                for i in range(3):
                    for j in range(2):
                        parts.append(f'<circle cx="{cx+mirror*i*5}" cy="{y-4+j*8}" r="1.5" fill="{primary}" opacity="0.7"/>')
            elif pattern == "vents":
                for i in range(4):
                    parts.append(f'<rect x="{cx if mirror > 0 else cx-8}" y="{y-8+i*5}" width="8" height="2" fill="{primary}" opacity="0.6"/>')
            elif pattern == "data_ports":
                parts.append(f'<rect x="{cx-4 if mirror < 0 else cx}" y="{y-6}" width="8" height="12" fill="none" stroke="{primary}" stroke-width="1" rx="1"/>')
                parts.append(f'<circle cx="{cx + mirror*2}" cy="{y}" r="2" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif pattern == "scars":
                parts.append(f'<line x1="{cx-mirror*5}" y1="{y-10}" x2="{cx+mirror*8}" y2="{y+10}" stroke="{primary}" stroke-width="1.5" opacity="0.6"/>')
                parts.append(f'<line x1="{cx}" y1="{y-8}" x2="{cx+mirror*10}" y2="{y+5}" stroke="{primary}" stroke-width="1" opacity="0.4"/>')
            elif pattern == "glyphs":
                symbol = SYMBOLS[(p.pattern_seed + (0 if cx < c else 1)) % len(SYMBOLS)]
                parts.append(f'<text x="{cx}" y="{y+4}" text-anchor="middle" fill="{glow}" font-size="12" opacity="0.8" {anim}>{symbol}</text>')
            elif pattern == "binary_stream":
                for i in range(4):
                    char = '01'[(p.pattern_seed >> i) & 1]
                    parts.append(f'<text x="{cx+mirror*4}" y="{y-8+i*6}" fill="{primary}" font-family="monospace" font-size="6" opacity="0.7">{char}</text>')
            elif pattern == "wave_lines":
                path = f'M{cx},{y-8}' + ''.join(f' Q{cx+mirror*(i*4+2)},{y-8+i*4 + (3 if i%2 else -3)} {cx+mirror*(i*4+4)},{y-8+i*4}' for i in range(4))
                parts.append(f'<path d="{path}" fill="none" stroke="{primary}" stroke-width="1.5" opacity="0.6"/>')

        return f'<g class="cheeks">{chr(10).join(parts)}</g>'

    def _draw_mouth(self, c: int, palette: dict, animated: bool) -> str:
        """Draw mouth based on style."""
        p = self._params
        style = MOUTH_STYLES[p.mouth_style]
        primary = palette["primary"]
        glow = palette["glow"]
        accent = palette["accent"]
        y = c + p.face_height * 0.4
        w = p.mouth_width
        anim = 'class="pulse"' if animated else ''
        parts = []

        if style == "data_stream":
            for i in range(5):
                char = '01'[p.pattern_seed >> i & 1]
                parts.append(f'<text x="{c - w/2 + i*w/4}" y="{y+3}" fill="{primary}" font-family="monospace" font-size="9" style="animation-delay:{i*0.15}s" {anim}>{char}</text>')
        elif style == "waveform":
            self._rng.seed(p.pattern_seed)
            path = f'M{c-w/2},{y}' + ''.join(f' L{c - w/2 + i*w/9},{y + self._rng.uniform(3,8) * (1 if i%2 else -1)}' for i in range(10)) + f' L{c+w/2},{y}'
            parts.append(f'<path d="{path}" fill="none" stroke="{glow}" stroke-width="2" filter="url(#glow)" {anim}/>')
        elif style == "minimal":
            parts.append(f'<line x1="{c-w/2}" y1="{y}" x2="{c+w/2}" y2="{y}" stroke="{glow}" stroke-width="2.5" stroke-linecap="round" filter="url(#glow)" {anim}/>')
        elif style == "grid":
            for i in range(3):
                parts.append(f'<line x1="{c-w/3}" y1="{y-3+i*3}" x2="{c+w/3}" y2="{y-3+i*3}" stroke="{primary}" stroke-width="1.5" opacity="0.7"/>')
            for i in range(4):
                parts.append(f'<line x1="{c-w/3+i*w/4.5}" y1="{y-3}" x2="{c-w/3+i*w/4.5}" y2="{y+3}" stroke="{accent}" stroke-width="1" opacity="0.5"/>')
        elif style == "vent":
            parts.append(f'<rect x="{c-w/2}" y="{y-4}" width="{w}" height="8" fill="none" stroke="{primary}" stroke-width="1" rx="2"/>')
            for i in range(5):
                parts.append(f'<line x1="{c - w/2 + 4 + i*(w-8)/4}" y1="{y-2}" x2="{c - w/2 + 4 + i*(w-8)/4}" y2="{y+2}" stroke="{primary}" stroke-width="1.5"/>')
        elif style == "speaker":
            parts.append(f'<ellipse cx="{c}" cy="{y}" rx="{w/2}" ry="5" fill="none" stroke="{primary}" stroke-width="1.5"/>')
            parts.append(f'<ellipse cx="{c}" cy="{y}" rx="{w/4}" ry="2.5" fill="{glow}" opacity="0.4" filter="url(#glow)" {anim}/>')
        elif style == "binary":
            bits = format(p.pattern_seed % 256, '08b')
            parts.append(f'<text x="{c}" y="{y+3}" text-anchor="middle" fill="{primary}" font-family="monospace" font-size="7">{bits}</text>')
        elif style == "smile_arc":
            parts.append(f'<path d="M{c-w/2},{y-2} Q{c},{y+8} {c+w/2},{y-2}" fill="none" stroke="{glow}" stroke-width="2" stroke-linecap="round" filter="url(#glow)" {anim}/>')
        elif style == "glyph":
            symbol = SYMBOLS[p.pattern_seed % len(SYMBOLS)]
            parts.append(f'<text x="{c}" y="{y+5}" text-anchor="middle" fill="{glow}" font-size="14" filter="url(#glow)" {anim}>{symbol}</text>')
        elif style == "silent":
            parts.append(f'<line x1="{c-w/4}" y1="{y}" x2="{c+w/4}" y2="{y}" stroke="{primary}" stroke-width="1" opacity="0.4"/>')
        elif style == "pixel_smile":
            ps = 4
            for i in range(-2, 3):
                dy = 0 if abs(i) < 2 else -ps
                parts.append(f'<rect x="{c + i*ps - ps/2}" y="{y + dy}" width="{ps}" height="{ps}" fill="{glow}" opacity="0.8"/>')
        elif style == "teeth_grid":
            tw = w / 6
            for i in range(6):
                parts.append(f'<rect x="{c - w/2 + i*tw + 1}" y="{y-3}" width="{tw-2}" height="6" fill="none" stroke="{primary}" stroke-width="1" rx="1"/>')
        elif style == "equalizer":
            self._rng.seed(p.pattern_seed)
            for i in range(8):
                h = self._rng.uniform(3, 10)
                parts.append(f'<rect x="{c - w/2 + i*w/8 + 1}" y="{y - h/2}" width="{w/8 - 2}" height="{h}" fill="{glow}" opacity="0.7" {anim}/>')
        else:  # circuit_mouth
            parts.append(f'<line x1="{c-w/2}" y1="{y}" x2="{c+w/2}" y2="{y}" stroke="{primary}" stroke-width="1.5"/>')
            for i in range(3):
                x = c - w/3 + i*w/3
                parts.append(f'<circle cx="{x}" cy="{y}" r="2" fill="{glow}" {anim}/>')

        return f'<g class="mouth">{chr(10).join(parts)}</g>'

    def _draw_chin(self, c: int, palette: dict, animated: bool) -> str:
        """Draw chin feature."""
        p = self._params
        feature = CHIN_FEATURES[p.chin_feature]
        if feature == "none":
            return ''

        primary = palette["primary"]
        glow = palette["glow"]
        y = c + p.face_height * 0.7
        anim = 'class="pulse"' if animated else ''

        if feature == "vent":
            return '<g class="chin">' + ''.join(f'<line x1="{c-12+i*8}" y1="{y}" x2="{c-12+i*8}" y2="{y+6}" stroke="{primary}" stroke-width="2" opacity="0.6"/>' for i in range(4)) + '</g>'
        elif feature == "light_bar":
            return f'<rect x="{c-15}" y="{y}" width="30" height="4" fill="{glow}" opacity="0.5" filter="url(#glow)" rx="2" {anim}/>'
        elif feature == "beard_lines":
            return '<g class="chin">' + ''.join(f'<line x1="{c - 10 + i*5}" y1="{y}" x2="{c - 10 + i*5}" y2="{y+10+i%2*3}" stroke="{primary}" stroke-width="1" opacity="0.5"/>' for i in range(5)) + '</g>'
        elif feature == "energy_core":
            return f'<circle cx="{c}" cy="{y+3}" r="6" fill="{glow}" opacity="0.3" filter="url(#glow)"/><circle cx="{c}" cy="{y+3}" r="3" fill="{glow}" filter="url(#glow-strong)" {anim}/>'
        elif feature == "port":
            return f'<rect x="{c-6}" y="{y}" width="12" height="8" fill="none" stroke="{primary}" stroke-width="1" rx="1"/><rect x="{c-3}" y="{y+2}" width="6" height="4" fill="{glow}" opacity="0.5"/>'
        elif feature == "speaker_grille":
            lines = ''.join(f'<line x1="{c-10}" y1="{y+i*3}" x2="{c+10}" y2="{y+i*3}" stroke="{primary}" stroke-width="1.5" opacity="0.6"/>' for i in range(4))
            return f'<g class="chin">{lines}</g>'
        else:  # data_jack
            return f'<rect x="{c-8}" y="{y}" width="16" height="10" fill="none" stroke="{primary}" stroke-width="1.5" rx="2"/><circle cx="{c-3}" cy="{y+5}" r="2" fill="{glow}" {anim}/><circle cx="{c+3}" cy="{y+5}" r="2" fill="{glow}" {anim}/>'

    def _draw_side_accessories(self, c: int, palette: dict, animated: bool) -> str:
        """Draw side accessories."""
        p = self._params
        accessory = SIDE_ACCESSORIES[p.side_accessory]
        if accessory == "none":
            return ''

        primary = palette["primary"]
        glow = palette["glow"]
        parts = []
        size = 10 * p.accessory_size
        y = c - 5
        anim = 'class="pulse"' if animated else ''

        left = accessory in ["earpiece_left", "earpiece_both", "antenna_side", "blade", "coil", "jack", "wing_fins", "data_nodes"]
        right = accessory in ["earpiece_right", "earpiece_both", "antenna_side", "blade", "coil", "jack", "wing_fins", "data_nodes"]

        for side, draw in [(-1, left), (1, right)]:
            if not draw:
                continue
            x = c + side * (p.face_width + 8)

            if "earpiece" in accessory:
                parts.append(f'<ellipse cx="{x}" cy="{y}" rx="4" ry="{size*0.8}" fill="none" stroke="{primary}" stroke-width="1.5"/>')
                parts.append(f'<circle cx="{x}" cy="{y}" r="2" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif accessory == "antenna_side":
                parts.append(f'<line x1="{x}" y1="{y}" x2="{x+side*size}" y2="{y-size*1.5}" stroke="{primary}" stroke-width="1.5"/>')
                parts.append(f'<circle cx="{x+side*size}" cy="{y-size*1.5}" r="3" fill="{glow}" filter="url(#glow)" {anim}/>')
            elif accessory == "blade":
                pts = [(x, y-size), (x+side*size*0.5, y), (x, y+size)]
                parts.append(f'<polygon points="{" ".join(f"{px},{py}" for px,py in pts)}" fill="none" stroke="{primary}" stroke-width="1.5"/>')
                parts.append(f'<line x1="{x}" y1="{y-size+2}" x2="{x}" y2="{y+size-2}" stroke="{glow}" stroke-width="1" filter="url(#glow)"/>')
            elif accessory == "coil":
                for i in range(4):
                    parts.append(f'<ellipse cx="{x+side*3}" cy="{y-6+i*4}" rx="3" ry="2" fill="none" stroke="{primary}" stroke-width="1" opacity="{1-i*0.2}"/>')
            elif accessory == "jack":
                parts.append(f'<rect x="{x-3 if side < 0 else x}" y="{y-4}" width="6" height="8" fill="none" stroke="{primary}" stroke-width="1" rx="1"/>')
                parts.append(f'<circle cx="{x + side*1.5}" cy="{y}" r="2" fill="{glow}" {anim}/>')
            elif accessory == "wing_fins":
                pts = [(x, y-size), (x+side*size*0.8, y-size*0.5), (x+side*size*0.6, y+size*0.5), (x, y+size*0.3)]
                parts.append(f'<polygon points="{" ".join(f"{px},{py}" for px,py in pts)}" fill="none" stroke="{primary}" stroke-width="1.5"/>')
                parts.append(f'<line x1="{x}" y1="{y-size*0.3}" x2="{x+side*size*0.5}" y2="{y}" stroke="{glow}" stroke-width="1" filter="url(#glow)"/>')
            elif accessory == "data_nodes":
                for i in range(3):
                    nx = x + side * (5 + i * 4)
                    ny = y - 8 + i * 8
                    parts.append(f'<circle cx="{nx}" cy="{ny}" r="3" fill="{glow}" filter="url(#glow)" class="float" style="animation-delay:{i*0.2}s"/>')

        return f'<g class="side-accessories">{chr(10).join(parts)}</g>'

    def _draw_crown(self, c: int, palette: dict, animated: bool) -> str:
        """Draw crown/top feature."""
        p = self._params
        crown = CROWN_STYLES[p.crown_style]
        if crown == "none":
            return ''

        primary = palette["primary"]
        glow = palette["glow"]
        accent = palette["accent"]
        y = c - p.face_height - 5
        size = 15 * p.crown_size
        anim = 'class="pulse"' if animated else ''
        anim_float = 'class="float"' if animated else ''

        if crown == "antenna_single":
            return f'<line x1="{c}" y1="{y}" x2="{c}" y2="{y-size*1.5}" stroke="{primary}" stroke-width="2"/><circle cx="{c}" cy="{y-size*1.5}" r="4" fill="{glow}" filter="url(#glow-strong)" {anim}/>'
        elif crown == "antenna_dual":
            return f'<line x1="{c-10}" y1="{y}" x2="{c-15}" y2="{y-size*1.2}" stroke="{primary}" stroke-width="2"/><line x1="{c+10}" y1="{y}" x2="{c+15}" y2="{y-size*1.2}" stroke="{primary}" stroke-width="2"/><circle cx="{c-15}" cy="{y-size*1.2}" r="3" fill="{glow}" filter="url(#glow)" {anim}/><circle cx="{c+15}" cy="{y-size*1.2}" r="3" fill="{glow}" filter="url(#glow)" {anim}/>'
        elif crown == "horns":
            return f'<path d="M{c-20},{y+5} Q{c-25},{y-size} {c-15},{y-size*1.5}" fill="none" stroke="{primary}" stroke-width="3" stroke-linecap="round"/><path d="M{c+20},{y+5} Q{c+25},{y-size} {c+15},{y-size*1.5}" fill="none" stroke="{primary}" stroke-width="3" stroke-linecap="round"/><circle cx="{c-15}" cy="{y-size*1.5}" r="2" fill="{glow}" filter="url(#glow)"/><circle cx="{c+15}" cy="{y-size*1.5}" r="2" fill="{glow}" filter="url(#glow)"/>'
        elif crown == "halo":
            return f'<ellipse cx="{c}" cy="{y-size*0.3}" rx="{p.face_width*0.9}" ry="{size*0.4}" fill="none" stroke="{glow}" stroke-width="2" filter="url(#glow)" {anim}/><ellipse cx="{c}" cy="{y-size*0.3}" rx="{p.face_width*0.9}" ry="{size*0.4}" fill="none" stroke="{primary}" stroke-width="0.5" opacity="0.5"/>'
        elif crown == "mohawk_data":
            chars = ''.join(f'<text x="{c - 15 + i*5}" y="{y - size*(0.5 + 0.5*(1 - abs(i-3)/3))}" fill="{glow}" font-family="monospace" font-size="8" opacity="0.8">{self._rng.choice(MATRIX_CHARS)}</text>' for i in range(7))
            return f'<g {anim_float}>{chars}</g>'
        elif crown == "floating_orbs":
            orbs = ''.join(f'<circle cx="{c - 20 + i*10}" cy="{y - size*(0.3 + 0.4*(1 - abs(i-2)/2))}" r="4" fill="{glow}" filter="url(#glow)" class="float" style="animation-delay:{i*0.3}s"/>' for i in range(5))
            return f'<g>{orbs}</g>'
        elif crown == "energy_spikes":
            spikes = ''.join(f'<line x1="{c - 16 + i*8}" y1="{y}" x2="{c - 16 + i*8}" y2="{y - size*(0.6 + 0.4*(1 - abs(i-2)/2))}" stroke="{glow}" stroke-width="2" filter="url(#glow)" {anim}/>' for i in range(5))
            return f'<g>{spikes}</g>'
        elif crown == "circuit_crown":
            return f'<path d="M{c-25},{y} L{c-20},{y-size*0.8} L{c-10},{y-size*0.5} L{c},{y-size} L{c+10},{y-size*0.5} L{c+20},{y-size*0.8} L{c+25},{y}" fill="none" stroke="{primary}" stroke-width="1.5"/><circle cx="{c}" cy="{y-size}" r="3" fill="{glow}" filter="url(#glow)" {anim}/><circle cx="{c-20}" cy="{y-size*0.8}" r="2" fill="{accent}"/><circle cx="{c+20}" cy="{y-size*0.8}" r="2" fill="{accent}"/>'
        elif crown == "visor_top":
            return f'<rect x="{c-p.face_width*0.7}" y="{y-size*0.3}" width="{p.face_width*1.4}" height="{size*0.5}" fill="{glow}" opacity="0.3" filter="url(#glow)" rx="2"/><rect x="{c-p.face_width*0.7}" y="{y-size*0.3}" width="{p.face_width*1.4}" height="{size*0.5}" fill="none" stroke="{primary}" stroke-width="1" rx="2"/>'
        elif crown == "flames":
            flames = ''.join(f'<ellipse cx="{c - 18 + i*6}" cy="{y - size*(0.5 + self._rng.uniform(0.3, 0.7))/2}" rx="4" ry="{size*(0.5 + self._rng.uniform(0.3, 0.7))/2}" fill="{glow}" opacity="0.4" filter="url(#glow)" class="flame"/>' for i in range(7))
            return f'<g>{flames}</g>'
        elif crown == "crystals":
            crystals = []
            for i in range(5):
                x = c - 16 + i * 8
                h = size * (0.5 + 0.5 * (1 - abs(i-2)/2))
                pts = [(x, y), (x-4, y-h*0.3), (x, y-h), (x+4, y-h*0.3)]
                crystals.append(f'<polygon points="{" ".join(f"{px},{py}" for px,py in pts)}" fill="{glow}" opacity="0.3" stroke="{primary}" stroke-width="1"/>')
            return f'<g>{chr(10).join(crystals)}</g>'
        elif crown == "crown_peaks":
            pts = [(c-25, y), (c-20, y-size*0.6), (c-15, y-size*0.3), (c-10, y-size*0.9), (c-5, y-size*0.3), (c, y-size*1.1), (c+5, y-size*0.3), (c+10, y-size*0.9), (c+15, y-size*0.3), (c+20, y-size*0.6), (c+25, y)]
            return f'<polygon points="{" ".join(f"{x},{py}" for x,py in pts)}" fill="none" stroke="{primary}" stroke-width="2"/><circle cx="{c}" cy="{y-size*1.1}" r="3" fill="{glow}" filter="url(#glow)" {anim}/>'
        elif crown == "satellite":
            return f'<ellipse cx="{c}" cy="{y-size*0.5}" rx="{size*1.2}" ry="{size*0.3}" fill="none" stroke="{primary}" stroke-width="1.5"/><line x1="{c}" y1="{y}" x2="{c}" y2="{y-size}" stroke="{primary}" stroke-width="2"/><circle cx="{c}" cy="{y-size}" r="4" fill="{glow}" filter="url(#glow)" {anim}/>'
        elif crown == "wings":
            left_wing = f'<path d="M{c-5},{y} Q{c-20},{y-size*0.5} {c-30},{y-size*0.8} Q{c-20},{y-size*0.3} {c-5},{y+5}" fill="none" stroke="{primary}" stroke-width="1.5"/>'
            right_wing = f'<path d="M{c+5},{y} Q{c+20},{y-size*0.5} {c+30},{y-size*0.8} Q{c+20},{y-size*0.3} {c+5},{y+5}" fill="none" stroke="{primary}" stroke-width="1.5"/>'
            return f'{left_wing}{right_wing}<circle cx="{c-30}" cy="{y-size*0.8}" r="2" fill="{glow}" filter="url(#glow)"/><circle cx="{c+30}" cy="{y-size*0.8}" r="2" fill="{glow}" filter="url(#glow)"/>'
        else:  # data_cloud
            cloud = []
            self._rng.seed(p.effect_seed)
            for i in range(8):
                cx = c - 20 + self._rng.uniform(0, 40)
                cy = y - size * 0.5 + self._rng.uniform(-size*0.3, size*0.3)
                char = self._rng.choice(MATRIX_CHARS)
                cloud.append(f'<text x="{cx}" y="{cy}" fill="{glow}" font-family="monospace" font-size="8" opacity="0.6" class="float" style="animation-delay:{i*0.2}s">{char}</text>')
            return f'<g>{chr(10).join(cloud)}</g>'

    def _draw_scan_overlay(self, palette: dict) -> str:
        """Draw scanning effect overlay."""
        p = self._params
        primary = palette["primary"]
        return f'<rect x="0" y="0" width="{self.CANVAS_SIZE}" height="3" fill="{primary}" opacity="0.15"><animate attributeName="y" from="-10" to="{self.CANVAS_SIZE+10}" dur="{p.animation_speed*2}s" repeatCount="indefinite"/></rect>'

    def to_data_uri(self, size: int = 200, animated: bool = True) -> str:
        """Generate data URI for embedding."""
        import base64
        svg = self.to_svg(size, animated)
        return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('ascii')}"

    def save_svg(self, path: Path | str, animated: bool = True) -> None:
        """Save as SVG file."""
        Path(path).write_text(self.to_svg(animated=animated))

    def fingerprint(self) -> str:
        """Get 8-character fingerprint."""
        return hashlib.blake2b(self._key_bytes, digest_size=4).hexdigest()

    def describe(self) -> str:
        """Get human-readable description."""
        p = self._params
        return f"{PALETTES[p.palette_idx]['name']} | {FACE_SHAPES[p.face_shape]} | {EYE_STYLES[p.eye_style]} eyes | {CROWN_STYLES[p.crown_style]} crown"

    def full_description(self) -> dict:
        """Get complete feature breakdown."""
        p = self._params
        return {
            "palette": PALETTES[p.palette_idx]["name"],
            "face_shape": FACE_SHAPES[p.face_shape],
            "eye_style": EYE_STYLES[p.eye_style],
            "eye_expression": EYE_EXPRESSIONS[p.eye_expression],
            "mouth_style": MOUTH_STYLES[p.mouth_style],
            "crown": CROWN_STYLES[p.crown_style],
            "forehead_mark": FOREHEAD_MARKS[p.forehead_mark],
            "cheek_pattern": CHEEK_PATTERNS[p.cheek_pattern],
            "chin_feature": CHIN_FEATURES[p.chin_feature],
            "side_accessory": SIDE_ACCESSORIES[p.side_accessory],
            "background": BG_STYLES[p.bg_style],
            "aura": AURA_STYLES[p.aura_style],
        }

    def similarity(self, other: AgentFace) -> float:
        """Calculate visual similarity (0.0 = identical, 1.0 = completely different)."""
        if self._key_bytes == other._key_bytes:
            return 0.0
        p1, p2 = self._params, other._params
        diff = sum([p1.palette_idx != p2.palette_idx, p1.face_shape != p2.face_shape, p1.eye_style != p2.eye_style,
                   p1.eye_expression != p2.eye_expression, p1.mouth_style != p2.mouth_style, p1.crown_style != p2.crown_style,
                   p1.forehead_mark != p2.forehead_mark, p1.cheek_pattern != p2.cheek_pattern, p1.chin_feature != p2.chin_feature,
                   p1.side_accessory != p2.side_accessory, p1.bg_style != p2.bg_style, p1.aura_style != p2.aura_style]) / 12
        return min(1.0, diff)

    @staticmethod
    def total_combinations() -> int:
        """Return total number of discrete human-distinguishable combinations."""
        return (len(PALETTES) * len(FACE_SHAPES) * len(EYE_STYLES) * len(EYE_EXPRESSIONS) *
                len(MOUTH_STYLES) * len(CROWN_STYLES) * len(FOREHEAD_MARKS) * len(CHEEK_PATTERNS) *
                len(CHIN_FEATURES) * len(SIDE_ACCESSORIES) * len(BG_STYLES) * len(AURA_STYLES))
        # = 2,378,170,368,000 (~2.4 trillion)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AgentFace) and self._key_bytes == other._key_bytes

    def __hash__(self) -> int:
        return hash(self._key_bytes)

    def __repr__(self) -> str:
        return f"AgentFace({self.fingerprint()}: {self.describe()})"


def generate_face_gallery(count: int = 16, size: int = 180, animated: bool = True) -> str:
    """Generate HTML gallery of faces."""
    import os
    faces_html = []
    for i in range(count):
        face = AgentFace(os.urandom(32))
        desc = face.full_description()
        faces_html.append(f'''
        <div class="face-card">
            <div class="face-wrapper"><img src="{face.to_data_uri(size, animated)}" width="{size}" height="{size}"/></div>
            <div class="face-info">
                <span class="fingerprint">{face.fingerprint()}</span>
                <span class="features">{desc["palette"]} · {desc["face_shape"]} · {desc["crown"]}</span>
            </div>
        </div>''')

    total = AgentFace.total_combinations()
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>SigAid AgentFace Gallery v5</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ background: #0a0a0f; min-height: 100vh; margin: 0; padding: 40px 20px; font-family: 'Courier New', monospace; color: #00ff41; }}
        h1 {{ text-align: center; font-size: 28px; margin-bottom: 10px; text-shadow: 0 0 20px rgba(0, 255, 65, 0.5); }}
        .subtitle {{ text-align: center; color: #00aa30; margin-bottom: 40px; font-size: 14px; }}
        .stats {{ text-align: center; color: #ffaa00; margin-bottom: 30px; font-size: 18px; }}
        .gallery {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 25px; max-width: 1400px; margin: 0 auto; }}
        .face-card {{ background: rgba(0, 255, 65, 0.03); border: 1px solid rgba(0, 255, 65, 0.2); border-radius: 12px; padding: 15px; transition: all 0.3s ease; }}
        .face-card:hover {{ border-color: rgba(0, 255, 65, 0.5); box-shadow: 0 0 30px rgba(0, 255, 65, 0.2); transform: translateY(-5px); }}
        .face-wrapper {{ border-radius: 8px; overflow: hidden; }}
        .face-wrapper img {{ display: block; }}
        .face-info {{ margin-top: 12px; text-align: center; }}
        .fingerprint {{ display: block; font-size: 12px; color: #00ff41; margin-bottom: 4px; }}
        .features {{ display: block; font-size: 9px; color: #008822; }}
        body::before {{ content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.15), rgba(0, 0, 0, 0.15) 1px, transparent 1px, transparent 2px); pointer-events: none; z-index: 1000; }}
    </style>
</head>
<body>
    <h1>// SIGAID AGENT FACES v5</h1>
    <p class="stats">{total:,} unique human-distinguishable combinations</p>
    <p class="subtitle">12 feature categories · 2+ TRILLION faces · Deterministic from cryptographic keys</p>
    <div class="gallery">{''.join(faces_html)}</div>
</body>
</html>'''
