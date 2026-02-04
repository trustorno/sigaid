/**
 * AgentFace v5 Constants
 *
 * These must match the Python implementation EXACTLY to ensure
 * identical face generation across platforms.
 *
 * Total combinations: 2,378,170,368,000 (~2.4 trillion)
 */

export interface Palette {
  name: string;
  primary: string;
  secondary: string;
  accent: string;
  glow: string;
  bg: string;
}

// 20 Color Palettes
export const PALETTES: Palette[] = [
  // Original 16
  { name: "Cyan", primary: "#00f5ff", secondary: "#0088aa", accent: "#00ff88", glow: "#00f5ff", bg: "#0a0a12" },
  { name: "Matrix", primary: "#00ff41", secondary: "#008f11", accent: "#88ff88", glow: "#00ff41", bg: "#0a0f0a" },
  { name: "Purple", primary: "#bf00ff", secondary: "#6600aa", accent: "#ff00ff", glow: "#bf00ff", bg: "#0f0a12" },
  { name: "Gold", primary: "#ffd700", secondary: "#ff8c00", accent: "#ffee88", glow: "#ffd700", bg: "#12100a" },
  { name: "Ice", primary: "#88ddff", secondary: "#4499cc", accent: "#ffffff", glow: "#88ddff", bg: "#0a0c10" },
  { name: "Rose", primary: "#ff0080", secondary: "#aa0055", accent: "#ff88bb", glow: "#ff0080", bg: "#120a0c" },
  { name: "Emerald", primary: "#00ff88", secondary: "#00aa55", accent: "#88ffcc", glow: "#00ff88", bg: "#0a100c" },
  { name: "Violet", primary: "#8800ff", secondary: "#5500aa", accent: "#bb88ff", glow: "#8800ff", bg: "#0c0a12" },
  { name: "Blood", primary: "#ff2222", secondary: "#aa0000", accent: "#ff8888", glow: "#ff2222", bg: "#120a0a" },
  { name: "Solar", primary: "#ffaa00", secondary: "#ff6600", accent: "#ffdd44", glow: "#ffaa00", bg: "#12100a" },
  { name: "Arctic", primary: "#aaeeff", secondary: "#66bbdd", accent: "#ffffff", glow: "#aaeeff", bg: "#0a0e12" },
  { name: "Toxic", primary: "#aaff00", secondary: "#66aa00", accent: "#ddff66", glow: "#aaff00", bg: "#0c100a" },
  { name: "Sunset", primary: "#ff6644", secondary: "#cc3366", accent: "#ffaa88", glow: "#ff6644", bg: "#120c0a" },
  { name: "Midnight", primary: "#4466ff", secondary: "#2233aa", accent: "#8899ff", glow: "#4466ff", bg: "#0a0a14" },
  { name: "Chrome", primary: "#cccccc", secondary: "#888888", accent: "#ffffff", glow: "#cccccc", bg: "#101010" },
  { name: "Plasma", primary: "#ff00ff", secondary: "#00ffff", accent: "#ff88ff", glow: "#ff00ff", bg: "#0f0a10" },
  // New 4
  { name: "Neon", primary: "#ff00aa", secondary: "#ffff00", accent: "#00ffaa", glow: "#ff00aa", bg: "#0a0808" },
  { name: "Ocean", primary: "#0066cc", secondary: "#004488", accent: "#00aaff", glow: "#0088ff", bg: "#080a10" },
  { name: "Lava", primary: "#ff4400", secondary: "#cc2200", accent: "#ffaa00", glow: "#ff6600", bg: "#100808" },
  { name: "Void", primary: "#6633aa", secondary: "#331166", accent: "#9966ff", glow: "#7744cc", bg: "#08060c" },
];

// 12 Face Shapes
export const FACE_SHAPES = [
  "oval", "angular", "hexagonal", "diamond", "shield", "heart",
  "octagonal", "rounded_square", "pentagon", "triangle", "pill", "star"
] as const;

// 16 Eye Styles
export const EYE_STYLES = [
  "holo_ring", "matrix_scan", "data_orb", "cyber_lens", "visor_bar", "split_iris",
  "compound", "target_lock", "energy_slit", "binary_dots", "spiral", "crosshair",
  "scanner_bar", "diamond_core", "pixel_grid", "flame_eye"
] as const;

// 8 Eye Expressions
export const EYE_EXPRESSIONS = [
  "neutral", "wide", "narrow", "tilt_up", "tilt_down", "asymmetric", "squint", "shock"
] as const;

// 14 Mouth Styles
export const MOUTH_STYLES = [
  "data_stream", "waveform", "minimal", "grid", "vent", "speaker", "binary",
  "smile_arc", "glyph", "silent", "pixel_smile", "teeth_grid", "equalizer", "circuit_mouth"
] as const;

// 16 Crown/Top Features
export const CROWN_STYLES = [
  "none", "antenna_single", "antenna_dual", "horns", "halo", "mohawk_data",
  "floating_orbs", "energy_spikes", "circuit_crown", "visor_top", "flames", "crystals",
  "crown_peaks", "satellite", "wings", "data_cloud"
] as const;

// 12 Forehead Markings
export const FOREHEAD_MARKS = [
  "none", "third_eye", "symbol_circle", "barcode", "circuit_node", "gem",
  "scanner_line", "binary_row", "hexagon", "omega", "cross", "infinity"
] as const;

// 10 Cheek Patterns
export const CHEEK_PATTERNS = [
  "none", "circuit_lines", "tribal_bars", "dots", "vents", "data_ports",
  "scars", "glyphs", "binary_stream", "wave_lines"
] as const;

// 8 Chin Features
export const CHIN_FEATURES = [
  "none", "vent", "light_bar", "beard_lines", "energy_core", "port", "speaker_grille", "data_jack"
] as const;

// 10 Side Accessories
export const SIDE_ACCESSORIES = [
  "none", "earpiece_left", "earpiece_right", "earpiece_both", "antenna_side",
  "blade", "coil", "jack", "wing_fins", "data_nodes"
] as const;

// 6 Background Styles
export const BG_STYLES = [
  "data_rain", "hex_grid", "circuit", "particles", "void", "matrix_code"
] as const;

// 6 Aura Effects
export const AURA_STYLES = [
  "glow", "double_ring", "glitch", "holographic", "pulse", "electric"
] as const;

// Matrix characters for data rain effect
export const MATRIX_CHARS = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF";

// Symbols for markings
export const SYMBOLS = ["◯", "△", "□", "◇", "⬡", "✦", "⚡", "Ω", "Δ", "Ψ", "∞", "⊕", "✕", "☆"];

// Type exports
export type FaceShape = typeof FACE_SHAPES[number];
export type EyeStyle = typeof EYE_STYLES[number];
export type EyeExpression = typeof EYE_EXPRESSIONS[number];
export type MouthStyle = typeof MOUTH_STYLES[number];
export type CrownStyle = typeof CROWN_STYLES[number];
export type ForeheadMark = typeof FOREHEAD_MARKS[number];
export type CheekPattern = typeof CHEEK_PATTERNS[number];
export type ChinFeature = typeof CHIN_FEATURES[number];
export type SideAccessory = typeof SIDE_ACCESSORIES[number];
export type BgStyle = typeof BG_STYLES[number];
export type AuraStyle = typeof AURA_STYLES[number];

/**
 * Calculate total combinations.
 * Must match Python: 2,378,170,368,000
 */
export function totalCombinations(): number {
  return (
    PALETTES.length *
    FACE_SHAPES.length *
    EYE_STYLES.length *
    EYE_EXPRESSIONS.length *
    MOUTH_STYLES.length *
    CROWN_STYLES.length *
    FOREHEAD_MARKS.length *
    CHEEK_PATTERNS.length *
    CHIN_FEATURES.length *
    SIDE_ACCESSORIES.length *
    BG_STYLES.length *
    AURA_STYLES.length
  );
}
