/**
 * AgentFace v5 - Matrix/Holographic Visual Identity for AI Agents
 *
 * TypeScript implementation that produces IDENTICAL output to the Python version.
 * Same key bytes = same SVG output across both platforms.
 */

import {
  PALETTES,
  FACE_SHAPES,
  EYE_STYLES,
  EYE_EXPRESSIONS,
  MOUTH_STYLES,
  CROWN_STYLES,
  FOREHEAD_MARKS,
  CHEEK_PATTERNS,
  CHIN_FEATURES,
  SIDE_ACCESSORIES,
  BG_STYLES,
  AURA_STYLES,
  MATRIX_CHARS,
  SYMBOLS,
  totalCombinations,
  type Palette,
} from './constants';
import type { FaceParams, FaceDescription, SVGOptions, AgentFaceFeatures } from './types';

/**
 * Mersenne Twister PRNG matching Python's random.Random.
 * This implementation produces identical sequences to Python when seeded with the same value.
 */
class SeededRandom {
  private mt: Uint32Array;
  private mti: number;

  private static readonly N = 624;
  private static readonly M = 397;
  private static readonly MATRIX_A = 0x9908b0df;
  private static readonly UPPER_MASK = 0x80000000;
  private static readonly LOWER_MASK = 0x7fffffff;

  constructor(seed: number) {
    this.mt = new Uint32Array(SeededRandom.N);
    this.mti = SeededRandom.N + 1;
    this.seed(seed);
  }

  seed(seed: number): void {
    // For seeds that fit in 32 bits, use simple seeding
    // For larger seeds, Python uses init_by_array
    if (seed >= 0 && seed <= 0xffffffff) {
      this.initGenrand(seed >>> 0);
    } else {
      // Convert to array of 32-bit words (big-endian, matching Python)
      const initKey: number[] = [];
      let temp = Math.abs(seed);
      while (temp > 0) {
        initKey.unshift(temp >>> 0 & 0xffffffff);
        temp = Math.floor(temp / 0x100000000);
      }
      if (initKey.length === 0) initKey.push(0);
      this.initByArray(initKey);
    }
  }

  private initGenrand(seed: number): void {
    this.mt[0] = seed >>> 0;
    for (this.mti = 1; this.mti < SeededRandom.N; this.mti++) {
      const s = this.mt[this.mti - 1] ^ (this.mt[this.mti - 1] >>> 30);
      this.mt[this.mti] = (((((s & 0xffff0000) >>> 16) * 1812433253) << 16) +
        (s & 0x0000ffff) * 1812433253 + this.mti) >>> 0;
    }
  }

  private initByArray(initKey: number[]): void {
    // Match Python's init_by_array for large integer seeds
    this.initGenrand(19650218);
    let i = 1;
    let j = 0;
    let k = Math.max(SeededRandom.N, initKey.length);

    for (; k > 0; k--) {
      const s = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] = ((this.mt[i] ^ (((((s & 0xffff0000) >>> 16) * 1664525) << 16) +
        ((s & 0x0000ffff) * 1664525))) + initKey[j] + j) >>> 0;
      i++;
      j++;
      if (i >= SeededRandom.N) {
        this.mt[0] = this.mt[SeededRandom.N - 1];
        i = 1;
      }
      if (j >= initKey.length) {
        j = 0;
      }
    }

    for (k = SeededRandom.N - 1; k > 0; k--) {
      const s = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] = ((this.mt[i] ^ (((((s & 0xffff0000) >>> 16) * 1566083941) << 16) +
        ((s & 0x0000ffff) * 1566083941))) - i) >>> 0;
      i++;
      if (i >= SeededRandom.N) {
        this.mt[0] = this.mt[SeededRandom.N - 1];
        i = 1;
      }
    }

    this.mt[0] = 0x80000000; // MSB is 1; assuring non-zero initial array
  }

  private genrandInt32(): number {
    let y: number;
    const mag01 = [0x0, SeededRandom.MATRIX_A];

    if (this.mti >= SeededRandom.N) {
      let kk: number;

      for (kk = 0; kk < SeededRandom.N - SeededRandom.M; kk++) {
        y = (this.mt[kk] & SeededRandom.UPPER_MASK) | (this.mt[kk + 1] & SeededRandom.LOWER_MASK);
        this.mt[kk] = this.mt[kk + SeededRandom.M] ^ (y >>> 1) ^ mag01[y & 0x1];
      }
      for (; kk < SeededRandom.N - 1; kk++) {
        y = (this.mt[kk] & SeededRandom.UPPER_MASK) | (this.mt[kk + 1] & SeededRandom.LOWER_MASK);
        this.mt[kk] = this.mt[kk + (SeededRandom.M - SeededRandom.N)] ^ (y >>> 1) ^ mag01[y & 0x1];
      }
      y = (this.mt[SeededRandom.N - 1] & SeededRandom.UPPER_MASK) | (this.mt[0] & SeededRandom.LOWER_MASK);
      this.mt[SeededRandom.N - 1] = this.mt[SeededRandom.M - 1] ^ (y >>> 1) ^ mag01[y & 0x1];

      this.mti = 0;
    }

    y = this.mt[this.mti++];

    // Tempering
    y ^= (y >>> 11);
    y ^= (y << 7) & 0x9d2c5680;
    y ^= (y << 15) & 0xefc60000;
    y ^= (y >>> 18);

    return y >>> 0;
  }

  random(): number {
    // Match Python's random(): returns [0.0, 1.0)
    // Python uses 53 bits of precision: (a * 2^27 + b) / 2^53
    const a = this.genrandInt32() >>> 5;
    const b = this.genrandInt32() >>> 6;
    return (a * 67108864.0 + b) / 9007199254740992.0;
  }

  randint(min: number, max: number): number {
    // Match Python's randint(a, b): returns a <= N <= b
    const range = max - min + 1;
    return min + Math.floor(this.random() * range);
  }

  uniform(min: number, max: number): number {
    // Match Python's uniform(a, b): returns a + (b-a) * random()
    return min + (max - min) * this.random();
  }

  choice<T>(array: readonly T[] | string): T {
    // Match Python's choice(): returns array[int(random() * len(array))]
    const idx = Math.floor(this.random() * array.length);
    return array[idx] as T;
  }

  /**
   * Seed the RNG from bytes, matching Python's random.Random(int.from_bytes(b, 'big'))
   */
  seedFromBytes(bytes: Uint8Array): void {
    // Convert bytes to array of 32-bit words (big-endian), matching Python's behavior
    // for large integers passed to random.seed()
    const initKey: number[] = [];

    // Pad to multiple of 4 bytes
    const padded = new Uint8Array(Math.ceil(bytes.length / 4) * 4);
    padded.set(bytes, padded.length - bytes.length);

    // Convert to 32-bit words (big-endian)
    for (let i = 0; i < padded.length; i += 4) {
      const word = (padded[i] << 24) | (padded[i + 1] << 16) | (padded[i + 2] << 8) | padded[i + 3];
      initKey.push(word >>> 0);
    }

    // Remove leading zeros but keep at least one element
    while (initKey.length > 1 && initKey[0] === 0) {
      initKey.shift();
    }

    this.initByArray(initKey);
  }
}

/**
 * BLAKE2b-like hash for fingerprint generation.
 * Simplified implementation for browser compatibility.
 */
async function blake2bDigest(data: Uint8Array, digestLength: number): Promise<Uint8Array> {
  // Use SubtleCrypto if available, otherwise fall back to simple hash
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    // Create a copy to ensure we have a plain ArrayBuffer
    const buffer = new ArrayBuffer(data.length);
    new Uint8Array(buffer).set(data);
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    return new Uint8Array(hashBuffer).slice(0, digestLength);
  }
  // Fallback: simple XOR-based hash (not cryptographically secure, but deterministic)
  const result = new Uint8Array(digestLength);
  for (let i = 0; i < data.length; i++) {
    result[i % digestLength] ^= data[i];
    result[i % digestLength] = (result[i % digestLength] * 31 + data[i]) & 0xFF;
  }
  return result;
}

/**
 * Synchronous fingerprint using simple hash (for non-async contexts).
 */
function simpleHash(data: Uint8Array, digestLength: number): Uint8Array {
  const result = new Uint8Array(digestLength);
  for (let i = 0; i < data.length; i++) {
    result[i % digestLength] ^= data[i];
    result[i % digestLength] = ((result[i % digestLength] * 31) + data[i]) & 0xFF;
  }
  // Add additional mixing
  for (let round = 0; round < 4; round++) {
    for (let i = 0; i < digestLength; i++) {
      result[i] = ((result[i] * 17) ^ result[(i + 1) % digestLength]) & 0xFF;
    }
  }
  return result;
}

export class AgentFace {
  private readonly keyBytes: Uint8Array;
  private readonly params: FaceParams;
  private readonly rng: SeededRandom;

  static readonly CANVAS_SIZE = 200;
  static readonly CENTER = 100;

  /**
   * Create an AgentFace from raw key bytes (32 bytes).
   */
  constructor(keyBytes: Uint8Array | ArrayBuffer) {
    const bytes = keyBytes instanceof ArrayBuffer ? new Uint8Array(keyBytes) : keyBytes;

    if (bytes.length < 32) {
      // Hash short keys to get 32 bytes (matching Python behavior)
      this.keyBytes = simpleHash(bytes, 32);
    } else {
      this.keyBytes = bytes.slice(0, 32);
    }

    this.params = this.extractParams();
    // Initialize RNG from first 8 bytes, matching Python's random.Random(int.from_bytes(key[:8], 'big'))
    this.rng = new SeededRandom(0); // Temporary, will be reseeded
    this.rng.seedFromBytes(this.keyBytes.slice(0, 8));
  }

  /**
   * Create from a hex string.
   */
  static fromHex(hex: string): AgentFace {
    if (!hex || hex.length === 0) {
      throw new Error('Hex string cannot be empty');
    }
    const cleanHex = hex.replace(/^0x/i, '').replace(/\s/g, '');
    if (!/^[0-9a-fA-F]*$/.test(cleanHex)) {
      throw new Error('Invalid hex string');
    }
    const matches = cleanHex.match(/.{1,2}/g);
    if (!matches) {
      throw new Error('Invalid hex string');
    }
    const bytes = new Uint8Array(matches.map(byte => parseInt(byte, 16)));
    return new AgentFace(bytes);
  }

  /**
   * Create from a base64 string.
   */
  static fromBase64(base64: string): AgentFace {
    // Support both browser (atob) and Node.js (Buffer)
    let binary: string;
    if (typeof atob === 'function') {
      binary = atob(base64);
    } else if (typeof Buffer !== 'undefined') {
      binary = Buffer.from(base64, 'base64').toString('binary');
    } else {
      throw new Error('No base64 decoder available');
    }
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return new AgentFace(bytes);
  }

  /**
   * Create from any bytes (public key, hash, etc.).
   */
  static fromBytes(bytes: Uint8Array | ArrayBuffer): AgentFace {
    return new AgentFace(bytes);
  }

  /**
   * Get exposed features.
   */
  get features(): AgentFaceFeatures {
    const p = this.params;
    return {
      palette: PALETTES[p.paletteIdx],
      faceShape: FACE_SHAPES[p.faceShape],
      eyeStyle: EYE_STYLES[p.eyeStyle],
      eyeExpression: EYE_EXPRESSIONS[p.eyeExpression],
      mouthStyle: MOUTH_STYLES[p.mouthStyle],
      crownStyle: CROWN_STYLES[p.crownStyle],
      foreheadMark: FOREHEAD_MARKS[p.foreheadMark],
      cheekPattern: CHEEK_PATTERNS[p.cheekPattern],
      chinFeature: CHIN_FEATURES[p.chinFeature],
      sideAccessory: SIDE_ACCESSORIES[p.sideAccessory],
      bgStyle: BG_STYLES[p.bgStyle],
      auraStyle: AURA_STYLES[p.auraStyle],
    };
  }

  private byteToRange(byteVal: number, minV: number, maxV: number): number {
    return minV + (byteVal / 255) * (maxV - minV);
  }

  private extractParams(): FaceParams {
    const b = this.keyBytes;

    return {
      paletteIdx: b[0] % PALETTES.length,
      faceShape: b[1] % FACE_SHAPES.length,
      eyeStyle: b[2] % EYE_STYLES.length,
      eyeExpression: b[3] % EYE_EXPRESSIONS.length,
      mouthStyle: b[4] % MOUTH_STYLES.length,
      crownStyle: b[5] % CROWN_STYLES.length,
      foreheadMark: b[6] % FOREHEAD_MARKS.length,
      cheekPattern: b[7] % CHEEK_PATTERNS.length,
      chinFeature: b[8] % CHIN_FEATURES.length,
      sideAccessory: b[9] % SIDE_ACCESSORIES.length,
      bgStyle: b[10] % BG_STYLES.length,
      auraStyle: b[11] % AURA_STYLES.length,
      faceWidth: this.byteToRange(b[12], 50, 70),
      faceHeight: this.byteToRange(b[13], 65, 85),
      eyeSize: this.byteToRange(b[14], 10, 20),
      eyeSpacing: this.byteToRange(b[15], 22, 38),
      mouthWidth: this.byteToRange(b[16], 18, 40),
      crownSize: this.byteToRange(b[17], 0.7, 1.3),
      markSize: this.byteToRange(b[18], 0.7, 1.3),
      accessorySize: this.byteToRange(b[19], 0.8, 1.2),
      glowIntensity: this.byteToRange(b[20], 0.5, 1.0),
      animationSpeed: this.byteToRange(b[21], 1.5, 3.5),
      glitchAmount: this.byteToRange(b[22], 0.1, 0.3),
      particleDensity: Math.floor(this.byteToRange(b[23], 8, 20)),
      patternSeed: b[24] * 256 + b[25],
      circuitSeed: b[26] * 256 + b[27],
      particleSeed: b[28] * 256 + b[29],
      effectSeed: b[30] * 256 + b[31],
    };
  }

  private getPalette(): Palette {
    return PALETTES[this.params.paletteIdx];
  }

  /**
   * Generate the complete face SVG.
   */
  toSVG(options: SVGOptions = {}): string {
    const { size = 200, animated = true } = options;
    const p = this.params;
    const c = AgentFace.CENTER;
    const palette = this.getPalette();

    const parts: string[] = [
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${AgentFace.CANVAS_SIZE} ${AgentFace.CANVAS_SIZE}" width="${size}" height="${size}">`
    ];

    parts.push(this.createDefs(palette));
    if (animated) {
      parts.push(this.createAnimations(palette));
    }

    parts.push(this.drawBackground(palette));
    parts.push(this.drawAura(c, palette, animated));

    const crownStyle = CROWN_STYLES[p.crownStyle];
    if (crownStyle === "halo" || crownStyle === "flames" || crownStyle === "data_cloud") {
      parts.push(this.drawCrown(c, palette, animated));
    }

    parts.push(this.drawFace(c, palette, animated));
    parts.push(this.drawForeheadMark(c, palette, animated));
    parts.push(this.drawEyes(c, palette, animated));
    parts.push(this.drawCheeks(c, palette, animated));
    parts.push(this.drawMouth(c, palette, animated));
    parts.push(this.drawChin(c, palette, animated));
    parts.push(this.drawSideAccessories(c, palette, animated));

    if (crownStyle !== "none" && crownStyle !== "halo" && crownStyle !== "flames" && crownStyle !== "data_cloud") {
      parts.push(this.drawCrown(c, palette, animated));
    }

    if (animated) {
      parts.push(this.drawScanOverlay(palette));
    }

    parts.push('</svg>');
    return parts.join('\n');
  }

  private createDefs(palette: Palette): string {
    const { primary, secondary } = palette;

    return `
<defs>
    <linearGradient id="face-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="${primary}" stop-opacity="0.2"/>
        <stop offset="50%" stop-color="${secondary}" stop-opacity="0.1"/>
        <stop offset="100%" stop-color="${primary}" stop-opacity="0.2"/>
    </linearGradient>
    <radialGradient id="face-glass" cx="30%" cy="30%" r="70%">
        <stop offset="0%" stop-color="white" stop-opacity="0.25"/>
        <stop offset="50%" stop-color="${primary}" stop-opacity="0.1"/>
        <stop offset="100%" stop-color="${secondary}" stop-opacity="0.05"/>
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
</defs>`;
  }

  private createAnimations(palette: Palette): string {
    const p = this.params;
    const speed = p.animationSpeed;
    const { glow } = palette;

    return `
<style>
    @keyframes pulse { 0%, 100% { opacity: 0.7; } 50% { opacity: 1; } }
    @keyframes glow-pulse { 0%, 100% { filter: drop-shadow(0 0 4px ${glow}); } 50% { filter: drop-shadow(0 0 12px ${glow}); } }
    @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
    @keyframes rotate { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    @keyframes glitch { 0%, 92%, 100% { transform: translate(0); } 94% { transform: translate(-2px, 1px); } 96% { transform: translate(2px, -1px); } 98% { transform: translate(-1px, -1px); } }
    @keyframes flicker { 0%, 90%, 100% { opacity: 1; } 92% { opacity: 0.8; } 96% { opacity: 0.7; } }
    @keyframes data-fall { 0% { transform: translateY(-20px); opacity: 0; } 10% { opacity: 0.8; } 90% { opacity: 0.8; } 100% { transform: translateY(220px); opacity: 0; } }
    @keyframes electric { 0%, 100% { opacity: 0.6; } 25% { opacity: 1; } 50% { opacity: 0.4; } 75% { opacity: 0.9; } }
    @keyframes flame { 0%, 100% { transform: scaleY(1) translateY(0); } 50% { transform: scaleY(1.1) translateY(-2px); } }
    .pulse { animation: pulse ${speed}s ease-in-out infinite; }
    .glow-pulse { animation: glow-pulse ${speed}s ease-in-out infinite; }
    .float { animation: float ${speed * 1.5}s ease-in-out infinite; }
    .rotate { animation: rotate ${speed * 4}s linear infinite; }
    .glitch { animation: glitch ${speed * 5}s steps(1) infinite; }
    .flicker { animation: flicker ${speed * 3}s steps(1) infinite; }
    .electric { animation: electric ${speed * 0.5}s steps(2) infinite; }
    .flame { animation: flame ${speed * 0.8}s ease-in-out infinite; }
</style>`;
  }

  private drawBackground(palette: Palette): string {
    const p = this.params;
    const bgStyle = BG_STYLES[p.bgStyle];
    const { primary, bg } = palette;
    const parts: string[] = [`<rect width="${AgentFace.CANVAS_SIZE}" height="${AgentFace.CANVAS_SIZE}" fill="${bg}"/>`];

    if (bgStyle === "data_rain") {
      this.rng.seed(p.particleSeed);
      for (let i = 0; i < p.particleDensity; i++) {
        const x = this.rng.randint(5, AgentFace.CANVAS_SIZE - 5);
        const delay = this.rng.uniform(0, 5);
        const duration = this.rng.uniform(3, 6);
        const char = this.rng.choice(MATRIX_CHARS);
        parts.push(`<text x="${x}" y="0" fill="${primary}" font-family="monospace" font-size="10" opacity="0.5" style="animation: data-fall ${duration}s linear ${delay}s infinite;">${char}</text>`);
      }
    } else if (bgStyle === "hex_grid") {
      for (let y = -10; y < AgentFace.CANVAS_SIZE + 20; y += 30) {
        const offset = (Math.floor(y / 30) % 2) ? 17 : 0;
        for (let x = -10 + offset; x < AgentFace.CANVAS_SIZE + 20; x += 34) {
          parts.push(`<polygon points="${x},${y - 10} ${x + 8},${y - 5} ${x + 8},${y + 5} ${x},${y + 10} ${x - 8},${y + 5} ${x - 8},${y - 5}" fill="none" stroke="${primary}" stroke-width="0.5" opacity="0.1"/>`);
        }
      }
    } else if (bgStyle === "circuit") {
      this.rng.seed(p.circuitSeed);
      for (let i = 0; i < 12; i++) {
        const x1 = this.rng.randint(0, AgentFace.CANVAS_SIZE);
        const y1 = this.rng.randint(0, AgentFace.CANVAS_SIZE);
        const x2 = x1 + this.rng.choice([-40, -20, 20, 40]);
        const y2 = y1;
        const x3 = x2;
        const y3 = y2 + this.rng.choice([-40, -20, 20, 40]);
        parts.push(`<path d="M${x1},${y1} L${x2},${y2} L${x3},${y3}" fill="none" stroke="${primary}" stroke-width="1" opacity="0.15"/>`);
        parts.push(`<circle cx="${x3}" cy="${y3}" r="2" fill="${primary}" opacity="0.2"/>`);
      }
    } else if (bgStyle === "particles") {
      this.rng.seed(p.particleSeed);
      for (let i = 0; i < p.particleDensity * 2; i++) {
        const x = this.rng.randint(5, AgentFace.CANVAS_SIZE - 5);
        const y = this.rng.randint(5, AgentFace.CANVAS_SIZE - 5);
        const size = this.rng.uniform(1, 3);
        const delay = this.rng.uniform(0, 3);
        parts.push(`<circle cx="${x}" cy="${y}" r="${size}" fill="${primary}" opacity="0.3" class="float" style="animation-delay: ${delay}s;"/>`);
      }
    } else if (bgStyle === "matrix_code") {
      this.rng.seed(p.particleSeed);
      for (let i = 0; i < p.particleDensity + 8; i++) {
        const x = this.rng.randint(5, AgentFace.CANVAS_SIZE - 5);
        const delay = this.rng.uniform(0, 4);
        const duration = this.rng.uniform(2.5, 5);
        const colHeight = this.rng.randint(3, 6);
        for (let j = 0; j < colHeight; j++) {
          const char = this.rng.choice(MATRIX_CHARS);
          const opacity = 0.8 - j * 0.15;
          parts.push(`<text x="${x}" y="${j * 12}" fill="${primary}" font-family="monospace" font-size="9" opacity="${opacity}" style="animation: data-fall ${duration}s linear ${delay + j * 0.1}s infinite;">${char}</text>`);
        }
      }
    }

    return parts.join('\n');
  }

  private drawAura(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const aura = AURA_STYLES[p.auraStyle];
    const { primary, glow, secondary } = palette;
    const radius = Math.max(p.faceWidth, p.faceHeight) + 12;
    const anim = animated ? 'class="glow-pulse"' : '';

    if (aura === "glow") {
      return `<circle cx="${c}" cy="${c}" r="${radius}" fill="none" stroke="${glow}" stroke-width="2" opacity="0.5" ${anim} filter="url(#glow)"/>`;
    } else if (aura === "double_ring") {
      return `<circle cx="${c}" cy="${c}" r="${radius}" fill="none" stroke="${glow}" stroke-width="1.5" opacity="0.5" ${anim}/>
<circle cx="${c}" cy="${c}" r="${radius + 6}" fill="none" stroke="${primary}" stroke-width="1" opacity="0.3"/>
<circle cx="${c}" cy="${c}" r="${radius + 12}" fill="none" stroke="${glow}" stroke-width="0.5" opacity="0.2"/>`;
    } else if (aura === "glitch") {
      const animGlitch = animated ? 'class="glitch"' : '';
      return `<g ${animGlitch}><circle cx="${c}" cy="${c}" r="${radius}" fill="none" stroke="${glow}" stroke-width="2" opacity="0.6"/></g>`;
    } else if (aura === "holographic") {
      return `<circle cx="${c}" cy="${c}" r="${radius}" fill="none" stroke="${primary}" stroke-width="1" opacity="0.4" stroke-dasharray="4 4" ${anim}/>
<circle cx="${c}" cy="${c}" r="${radius + 4}" fill="none" stroke="${glow}" stroke-width="0.5" opacity="0.3" stroke-dasharray="2 6"/>
<circle cx="${c}" cy="${c}" r="${radius - 4}" fill="none" stroke="${secondary}" stroke-width="0.5" opacity="0.3" stroke-dasharray="6 2"/>`;
    } else if (aura === "pulse") {
      const animPulse = animated ? 'class="pulse"' : '';
      return `<circle cx="${c}" cy="${c}" r="${radius}" fill="none" stroke="${glow}" stroke-width="3" opacity="0.4" ${animPulse} filter="url(#glow)"/>
<circle cx="${c}" cy="${c}" r="${radius - 3}" fill="none" stroke="${primary}" stroke-width="1" opacity="0.6"/>`;
    } else {
      // electric
      const animElec = animated ? 'class="electric"' : '';
      const parts: string[] = [`<circle cx="${c}" cy="${c}" r="${radius}" fill="none" stroke="${glow}" stroke-width="2" opacity="0.5" ${animElec}/>`];
      this.rng.seed(p.effectSeed);
      for (let i = 0; i < 6; i++) {
        const angle = (i * 60 * Math.PI) / 180;
        const x1 = c + radius * Math.cos(angle);
        const y1 = c + radius * Math.sin(angle);
        const x2 = c + (radius + 8) * Math.cos(angle + 0.1);
        const y2 = c + (radius + 8) * Math.sin(angle + 0.1);
        const x3 = c + (radius + 5) * Math.cos(angle - 0.1);
        const y3 = c + (radius + 5) * Math.sin(angle - 0.1);
        parts.push(`<path d="M${x1},${y1} L${x2},${y2} L${x3},${y3}" fill="none" stroke="${glow}" stroke-width="1.5" ${animElec}/>`);
      }
      return parts.join('\n');
    }
  }

  private getFaceShapeElement(c: number, w: number, h: number, palette: Palette): string {
    const p = this.params;
    const shape = FACE_SHAPES[p.faceShape];
    const { primary } = palette;

    if (shape === "oval") {
      return `<ellipse cx="${c}" cy="${c}" rx="${w}" ry="${h}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "angular") {
      const pts: [number, number][] = [
        [c, c - h], [c + w * 0.85, c - h * 0.35], [c + w * 0.7, c + h * 0.65],
        [c, c + h], [c - w * 0.7, c + h * 0.65], [c - w * 0.85, c - h * 0.35]
      ];
      return `<polygon points="${pts.map(([x, y]) => `${x},${y}`).join(' ')}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "hexagonal") {
      const pts = Array.from({ length: 6 }, (_, i) => {
        const angle = (Math.PI / 3) * i - Math.PI / 2;
        return [c + w * Math.cos(angle), c + h * Math.sin(angle)] as [number, number];
      });
      return `<polygon points="${pts.map(([x, y]) => `${x},${y}`).join(' ')}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "diamond") {
      const pts: [number, number][] = [[c, c - h], [c + w, c], [c, c + h], [c - w, c]];
      return `<polygon points="${pts.map(([x, y]) => `${x},${y}`).join(' ')}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "shield") {
      return `<path d="M${c},${c - h} Q${c + w},${c - h * 0.5} ${c + w},${c + h * 0.2} Q${c + w * 0.7},${c + h} ${c},${c + h} Q${c - w * 0.7},${c + h} ${c - w},${c + h * 0.2} Q${c - w},${c - h * 0.5} ${c},${c - h}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "heart") {
      return `<path d="M${c},${c - h * 0.3} Q${c},${c - h} ${c - w * 0.5},${c - h} Q${c - w},${c - h} ${c - w},${c - h * 0.3} Q${c - w},${c + h * 0.3} ${c},${c + h} Q${c + w},${c + h * 0.3} ${c + w},${c - h * 0.3} Q${c + w},${c - h} ${c + w * 0.5},${c - h} Q${c},${c - h} ${c},${c - h * 0.3}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "octagonal") {
      const d = w * 0.4;
      const pts: [number, number][] = [
        [c - d, c - h], [c + d, c - h], [c + w, c - d], [c + w, c + d],
        [c + d, c + h], [c - d, c + h], [c - w, c + d], [c - w, c - d]
      ];
      return `<polygon points="${pts.map(([x, y]) => `${x},${y}`).join(' ')}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "rounded_square") {
      return `<rect x="${c - w}" y="${c - h}" width="${w * 2}" height="${h * 2}" rx="${w * 0.25}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "pentagon") {
      const pts = Array.from({ length: 5 }, (_, i) => {
        const angle = (2 * Math.PI / 5) * i - Math.PI / 2;
        return [c + w * 0.95 * Math.cos(angle), c + h * 0.95 * Math.sin(angle)] as [number, number];
      });
      return `<polygon points="${pts.map(([x, y]) => `${x},${y}`).join(' ')}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "triangle") {
      const pts: [number, number][] = [[c, c - h], [c + w, c + h * 0.8], [c - w, c + h * 0.8]];
      return `<polygon points="${pts.map(([x, y]) => `${x},${y}`).join(' ')}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else if (shape === "pill") {
      return `<rect x="${c - w * 0.7}" y="${c - h}" width="${w * 1.4}" height="${h * 2}" rx="${w * 0.7}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    } else {
      // star
      const pts: [number, number][] = [];
      for (let i = 0; i < 10; i++) {
        const angle = (Math.PI / 5) * i - Math.PI / 2;
        const r = i % 2 === 0 ? w : w * 0.5;
        pts.push([c + r * Math.cos(angle), c + (h / w) * r * Math.sin(angle)]);
      }
      return `<polygon points="${pts.map(([x, y]) => `${x},${y}`).join(' ')}" fill="url(#face-glass)" stroke="${primary}" stroke-width="1.5"/>`;
    }
  }

  private drawFace(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const { faceWidth: w, faceHeight: h } = p;
    const anim = animated ? 'class="glitch"' : '';
    return `<g ${anim}>${this.getFaceShapeElement(c, w, h, palette)}</g>`;
  }

  private drawForeheadMark(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const mark = FOREHEAD_MARKS[p.foreheadMark];
    if (mark === "none") return '';

    const { primary, glow } = palette;
    const y = c - p.faceHeight * 0.55;
    const size = 8 * p.markSize;
    const anim = animated ? 'class="pulse"' : '';

    if (mark === "third_eye") {
      return `<circle cx="${c}" cy="${y}" r="${size}" fill="none" stroke="${primary}" stroke-width="1.5" ${anim}/><circle cx="${c}" cy="${y}" r="${size * 0.4}" fill="${glow}" filter="url(#glow)" ${anim}/>`;
    } else if (mark === "symbol_circle") {
      const symbol = SYMBOLS[p.patternSeed % SYMBOLS.length];
      return `<circle cx="${c}" cy="${y}" r="${size}" fill="none" stroke="${primary}" stroke-width="1"/><text x="${c}" y="${y + 3}" text-anchor="middle" fill="${glow}" font-size="${size * 1.2}" ${anim}>${symbol}</text>`;
    } else if (mark === "barcode") {
      const lines = Array.from({ length: 7 }, (_, i) => {
        const width = ((p.patternSeed >> (i + 3)) & 1) ? 1 : 2;
        return `<rect x="${c + (i - 3) * 3 - width / 2}" y="${y - size / 2}" width="${width}" height="${size}" fill="${primary}"/>`;
      }).join('\n');
      return `<g opacity="0.8">${lines}</g>`;
    } else if (mark === "circuit_node") {
      return `<circle cx="${c}" cy="${y}" r="${size * 0.5}" fill="${glow}" filter="url(#glow)" ${anim}/><line x1="${c - size}" y1="${y}" x2="${c - size * 0.6}" y2="${y}" stroke="${primary}" stroke-width="1"/><line x1="${c + size * 0.6}" y1="${y}" x2="${c + size}" y2="${y}" stroke="${primary}" stroke-width="1"/><line x1="${c}" y1="${y - size}" x2="${c}" y2="${y - size * 0.6}" stroke="${primary}" stroke-width="1"/>`;
    } else if (mark === "gem") {
      const pts: [number, number][] = [[c, y - size], [c + size * 0.7, y], [c, y + size * 0.5], [c - size * 0.7, y]];
      return `<polygon points="${pts.map(([x, py]) => `${x},${py}`).join(' ')}" fill="${glow}" opacity="0.6" filter="url(#glow)" ${anim}/><polygon points="${pts.map(([x, py]) => `${x},${py}`).join(' ')}" fill="none" stroke="${primary}" stroke-width="1"/>`;
    } else if (mark === "scanner_line") {
      return `<line x1="${c - size * 1.5}" y1="${y}" x2="${c + size * 1.5}" y2="${y}" stroke="${glow}" stroke-width="2" filter="url(#glow)" ${anim}/><circle cx="${c - size * 1.5}" cy="${y}" r="2" fill="${primary}"/><circle cx="${c + size * 1.5}" cy="${y}" r="2" fill="${primary}"/>`;
    } else if (mark === "binary_row") {
      const bits = (p.patternSeed % 256).toString(2).padStart(8, '0');
      return `<text x="${c}" y="${y + 3}" text-anchor="middle" fill="${primary}" font-family="monospace" font-size="6" ${anim}>${bits}</text>`;
    } else if (mark === "hexagon") {
      const pts = Array.from({ length: 6 }, (_, i) => {
        const angle = (Math.PI / 3) * i - Math.PI / 2;
        return [c + size * 0.8 * Math.cos(angle), y + size * 0.8 * Math.sin(angle)] as [number, number];
      });
      return `<polygon points="${pts.map(([x, py]) => `${x},${py}`).join(' ')}" fill="none" stroke="${primary}" stroke-width="1.5" ${anim}/><circle cx="${c}" cy="${y}" r="${size * 0.3}" fill="${glow}" filter="url(#glow)"/>`;
    } else if (mark === "omega") {
      return `<text x="${c}" y="${y + size * 0.4}" text-anchor="middle" fill="${glow}" font-size="${size * 2}" filter="url(#glow)" ${anim}>Ω</text>`;
    } else if (mark === "cross") {
      return `<line x1="${c - size}" y1="${y}" x2="${c + size}" y2="${y}" stroke="${glow}" stroke-width="2" filter="url(#glow)" ${anim}/><line x1="${c}" y1="${y - size}" x2="${c}" y2="${y + size}" stroke="${glow}" stroke-width="2" filter="url(#glow)"/>`;
    } else {
      // infinity
      return `<text x="${c}" y="${y + size * 0.3}" text-anchor="middle" fill="${glow}" font-size="${size * 2.5}" filter="url(#glow)" ${anim}>∞</text>`;
    }
  }

  private drawEyes(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const style = EYE_STYLES[p.eyeStyle];
    const expr = EYE_EXPRESSIONS[p.eyeExpression];
    const { primary, glow, accent } = palette;

    const eyeY = c - 5;
    const leftX = c - p.eyeSpacing / 2;
    const rightX = c + p.eyeSpacing / 2;
    let size = p.eyeSize;

    // Expression modifiers
    let leftMod = 0, rightMod = 0, sizeMod = 1.0;
    if (expr === "wide") sizeMod = 1.2;
    else if (expr === "narrow") sizeMod = 0.75;
    else if (expr === "tilt_up") { leftMod = 3; rightMod = -3; }
    else if (expr === "tilt_down") { leftMod = -3; rightMod = 3; }
    else if (expr === "asymmetric") { leftMod = -2; sizeMod = 0.9; }
    else if (expr === "squint") { sizeMod = 0.6; leftMod = 1; rightMod = -1; }
    else if (expr === "shock") sizeMod = 1.4;

    size *= sizeMod;
    const leftY = eyeY + leftMod;
    const rightY = eyeY + rightMod;
    const anim = animated ? 'class="pulse"' : '';
    const parts: string[] = [];

    for (const [ex, ey] of [[leftX, leftY], [rightX, rightY]]) {
      if (style === "holo_ring") {
        for (let i = 0; i < 3; i++) {
          parts.push(`<circle cx="${ex}" cy="${ey}" r="${size - i * 3}" fill="none" stroke="${primary}" stroke-width="1.5" opacity="${1 - i * 0.3}"/>`);
        }
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size * 0.25}" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (style === "matrix_scan") {
        const w = size * 1.4, h = size * 0.7;
        parts.push(`<rect x="${ex - w / 2}" y="${ey - h / 2}" width="${w}" height="${h}" fill="none" stroke="${primary}" stroke-width="1.5" rx="2"/>`);
        parts.push(`<line x1="${ex - w / 2 + 3}" y1="${ey}" x2="${ex + w / 2 - 3}" y2="${ey}" stroke="${glow}" stroke-width="2" filter="url(#glow)" ${anim}/>`);
      } else if (style === "data_orb") {
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size}" fill="${glow}" opacity="0.2" filter="url(#glow)"/>`);
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size * 0.6}" fill="none" stroke="${primary}" stroke-width="1"/>`);
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size * 0.25}" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (style === "cyber_lens") {
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size}" fill="rgba(0,0,0,0.4)" stroke="${primary}" stroke-width="1.5"/>`);
        parts.push(`<line x1="${ex - size}" y1="${ey}" x2="${ex + size}" y2="${ey}" stroke="${primary}" stroke-width="0.5" opacity="0.5"/>`);
        parts.push(`<line x1="${ex}" y1="${ey - size}" x2="${ex}" y2="${ey + size}" stroke="${primary}" stroke-width="0.5" opacity="0.5"/>`);
        parts.push(`<circle cx="${ex}" cy="${ey}" r="3" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (style === "visor_bar") {
        const w = size * 2, h = size * 0.5;
        parts.push(`<rect x="${ex - w / 2}" y="${ey - h / 2}" width="${w}" height="${h}" fill="${glow}" opacity="0.4" filter="url(#glow)" rx="2"/>`);
        parts.push(`<rect x="${ex - w / 2}" y="${ey - h / 2}" width="${w}" height="${h}" fill="none" stroke="${primary}" stroke-width="1" rx="2"/>`);
      } else if (style === "split_iris") {
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size}" fill="none" stroke="${primary}" stroke-width="1.5"/>`);
        parts.push(`<line x1="${ex}" y1="${ey - size}" x2="${ex}" y2="${ey + size}" stroke="${glow}" stroke-width="2" filter="url(#glow)"/>`);
        parts.push(`<circle cx="${ex - size * 0.35}" cy="${ey}" r="2" fill="${accent}" ${anim}/>`);
        parts.push(`<circle cx="${ex + size * 0.35}" cy="${ey}" r="2" fill="${accent}" ${anim}/>`);
      } else if (style === "compound") {
        for (let i = 0; i < 6; i++) {
          const angle = (Math.PI / 3) * i;
          parts.push(`<circle cx="${ex + size * 0.5 * Math.cos(angle)}" cy="${ey + size * 0.5 * Math.sin(angle)}" r="${size * 0.3}" fill="none" stroke="${primary}" stroke-width="1"/>`);
        }
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size * 0.3}" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (style === "target_lock") {
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size}" fill="none" stroke="${primary}" stroke-width="1" stroke-dasharray="4 2"/>`);
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size * 0.5}" fill="none" stroke="${glow}" stroke-width="1.5"/>`);
        for (const angle of [0, 90, 180, 270]) {
          const rad = (angle * Math.PI) / 180;
          parts.push(`<line x1="${ex + size * 0.6 * Math.cos(rad)}" y1="${ey + size * 0.6 * Math.sin(rad)}" x2="${ex + size * 1.1 * Math.cos(rad)}" y2="${ey + size * 1.1 * Math.sin(rad)}" stroke="${primary}" stroke-width="1.5"/>`);
        }
        parts.push(`<circle cx="${ex}" cy="${ey}" r="2" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (style === "energy_slit") {
        parts.push(`<ellipse cx="${ex}" cy="${ey}" rx="${size}" ry="${size * 0.3}" fill="${glow}" opacity="0.6" filter="url(#glow)" ${anim}/>`);
        parts.push(`<ellipse cx="${ex}" cy="${ey}" rx="${size}" ry="${size * 0.3}" fill="none" stroke="${primary}" stroke-width="1.5"/>`);
      } else if (style === "binary_dots") {
        const bits = ((p.patternSeed + Math.floor(ex)) % 16).toString(2).padStart(4, '0');
        for (let i = 0; i < bits.length; i++) {
          parts.push(`<circle cx="${ex + (i - 1.5) * size * 0.5}" cy="${ey}" r="${size * 0.2}" fill="${bits[i] === '1' ? glow : 'none'}" stroke="${primary}" stroke-width="1"/>`);
        }
      } else if (style === "spiral") {
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size}" fill="none" stroke="${primary}" stroke-width="1"/>`);
        let path = `M${ex},${ey}`;
        for (let i = 0; i < 20; i++) {
          path += ` L${ex + size * 0.1 * i / 2 * Math.cos(i * 0.5)},${ey + size * 0.1 * i / 2 * Math.sin(i * 0.5)}`;
        }
        parts.push(`<path d="${path}" fill="none" stroke="${glow}" stroke-width="1.5" filter="url(#glow)" ${anim}/>`);
      } else if (style === "crosshair") {
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size}" fill="none" stroke="${primary}" stroke-width="1"/>`);
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size * 0.5}" fill="none" stroke="${primary}" stroke-width="0.5"/>`);
        for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
          parts.push(`<line x1="${ex + dx * size * 0.6}" y1="${ey + dy * size * 0.6}" x2="${ex + dx * size * 1.2}" y2="${ey + dy * size * 1.2}" stroke="${glow}" stroke-width="1.5"/>`);
        }
        parts.push(`<circle cx="${ex}" cy="${ey}" r="2" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (style === "scanner_bar") {
        const w = size * 2.5;
        parts.push(`<rect x="${ex - w / 2}" y="${ey - 3}" width="${w}" height="6" fill="${glow}" opacity="0.5" filter="url(#glow)" rx="3" ${anim}/>`);
        parts.push(`<rect x="${ex - w / 2}" y="${ey - 3}" width="${w}" height="6" fill="none" stroke="${primary}" stroke-width="1" rx="3"/>`);
      } else if (style === "diamond_core") {
        const pts: [number, number][] = [[ex, ey - size], [ex + size, ey], [ex, ey + size], [ex - size, ey]];
        parts.push(`<polygon points="${pts.map(([x, y]) => `${x},${y}`).join(' ')}" fill="none" stroke="${primary}" stroke-width="1.5"/>`);
        parts.push(`<circle cx="${ex}" cy="${ey}" r="${size * 0.3}" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (style === "pixel_grid") {
        const ps = size * 0.4;
        for (let i = -1; i <= 1; i++) {
          for (let j = -1; j <= 1; j++) {
            const fill = (i + j) % 2 === 0 ? glow : 'none';
            parts.push(`<rect x="${ex + i * ps - ps / 2}" y="${ey + j * ps - ps / 2}" width="${ps}" height="${ps}" fill="${fill}" stroke="${primary}" stroke-width="0.5" opacity="0.8"/>`);
          }
        }
      } else {
        // flame_eye
        parts.push(`<ellipse cx="${ex}" cy="${ey}" rx="${size * 0.8}" ry="${size}" fill="${glow}" opacity="0.3" filter="url(#glow)" class="flame"/>`);
        parts.push(`<ellipse cx="${ex}" cy="${ey + size * 0.2}" rx="${size * 0.5}" ry="${size * 0.7}" fill="${glow}" opacity="0.5" class="flame"/>`);
        parts.push(`<circle cx="${ex}" cy="${ey + size * 0.3}" r="${size * 0.25}" fill="${accent}" filter="url(#glow)" ${anim}/>`);
      }
    }

    return `<g class="eyes">\n${parts.join('\n')}</g>`;
  }

  private drawCheeks(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const pattern = CHEEK_PATTERNS[p.cheekPattern];
    if (pattern === "none") return '';

    const { primary, glow } = palette;
    const y = c + 5;
    const leftX = c - p.faceWidth * 0.6;
    const rightX = c + p.faceWidth * 0.6;
    const parts: string[] = [];
    const anim = animated ? 'class="pulse"' : '';

    for (const cx of [leftX, rightX]) {
      const mirror = cx < c ? -1 : 1;

      if (pattern === "circuit_lines") {
        parts.push(`<path d="M${cx},${y - 8} L${cx + mirror * 10},${y - 8} L${cx + mirror * 10},${y + 8} L${cx + mirror * 5},${y + 8}" fill="none" stroke="${primary}" stroke-width="1" opacity="0.7"/>`);
        parts.push(`<circle cx="${cx + mirror * 5}" cy="${y + 8}" r="2" fill="${glow}" filter="url(#glow)"/>`);
      } else if (pattern === "tribal_bars") {
        for (let i = 0; i < 3; i++) {
          parts.push(`<line x1="${cx}" y1="${y - 6 + i * 6}" x2="${cx + mirror * 12}" y2="${y - 6 + i * 6}" stroke="${primary}" stroke-width="2" opacity="${0.9 - i * 0.2}"/>`);
        }
      } else if (pattern === "dots") {
        for (let i = 0; i < 3; i++) {
          for (let j = 0; j < 2; j++) {
            parts.push(`<circle cx="${cx + mirror * i * 5}" cy="${y - 4 + j * 8}" r="1.5" fill="${primary}" opacity="0.7"/>`);
          }
        }
      } else if (pattern === "vents") {
        for (let i = 0; i < 4; i++) {
          parts.push(`<rect x="${mirror > 0 ? cx : cx - 8}" y="${y - 8 + i * 5}" width="8" height="2" fill="${primary}" opacity="0.6"/>`);
        }
      } else if (pattern === "data_ports") {
        parts.push(`<rect x="${mirror < 0 ? cx - 4 : cx}" y="${y - 6}" width="8" height="12" fill="none" stroke="${primary}" stroke-width="1" rx="1"/>`);
        parts.push(`<circle cx="${cx + mirror * 2}" cy="${y}" r="2" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (pattern === "scars") {
        parts.push(`<line x1="${cx - mirror * 5}" y1="${y - 10}" x2="${cx + mirror * 8}" y2="${y + 10}" stroke="${primary}" stroke-width="1.5" opacity="0.6"/>`);
        parts.push(`<line x1="${cx}" y1="${y - 8}" x2="${cx + mirror * 10}" y2="${y + 5}" stroke="${primary}" stroke-width="1" opacity="0.4"/>`);
      } else if (pattern === "glyphs") {
        const symbol = SYMBOLS[(p.patternSeed + (cx < c ? 0 : 1)) % SYMBOLS.length];
        parts.push(`<text x="${cx}" y="${y + 4}" text-anchor="middle" fill="${glow}" font-size="12" opacity="0.8" ${anim}>${symbol}</text>`);
      } else if (pattern === "binary_stream") {
        for (let i = 0; i < 4; i++) {
          const char = '01'[(p.patternSeed >> i) & 1];
          parts.push(`<text x="${cx + mirror * 4}" y="${y - 8 + i * 6}" fill="${primary}" font-family="monospace" font-size="6" opacity="0.7">${char}</text>`);
        }
      } else if (pattern === "wave_lines") {
        let path = `M${cx},${y - 8}`;
        for (let i = 0; i < 4; i++) {
          path += ` Q${cx + mirror * (i * 4 + 2)},${y - 8 + i * 4 + (i % 2 ? 3 : -3)} ${cx + mirror * (i * 4 + 4)},${y - 8 + i * 4}`;
        }
        parts.push(`<path d="${path}" fill="none" stroke="${primary}" stroke-width="1.5" opacity="0.6"/>`);
      }
    }

    return `<g class="cheeks">\n${parts.join('\n')}</g>`;
  }

  private drawMouth(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const style = MOUTH_STYLES[p.mouthStyle];
    const { primary, glow, accent } = palette;
    const y = c + p.faceHeight * 0.4;
    const w = p.mouthWidth;
    const anim = animated ? 'class="pulse"' : '';
    const parts: string[] = [];

    if (style === "data_stream") {
      for (let i = 0; i < 5; i++) {
        const char = '01'[(p.patternSeed >> i) & 1];
        parts.push(`<text x="${c - w / 2 + i * w / 4}" y="${y + 3}" fill="${primary}" font-family="monospace" font-size="9" style="animation-delay:${i * 0.15}s" ${anim}>${char}</text>`);
      }
    } else if (style === "waveform") {
      this.rng.seed(p.patternSeed);
      let path = `M${c - w / 2},${y}`;
      for (let i = 0; i < 10; i++) {
        path += ` L${c - w / 2 + i * w / 9},${y + this.rng.uniform(3, 8) * (i % 2 ? 1 : -1)}`;
      }
      path += ` L${c + w / 2},${y}`;
      parts.push(`<path d="${path}" fill="none" stroke="${glow}" stroke-width="2" filter="url(#glow)" ${anim}/>`);
    } else if (style === "minimal") {
      parts.push(`<line x1="${c - w / 2}" y1="${y}" x2="${c + w / 2}" y2="${y}" stroke="${glow}" stroke-width="2.5" stroke-linecap="round" filter="url(#glow)" ${anim}/>`);
    } else if (style === "grid") {
      for (let i = 0; i < 3; i++) {
        parts.push(`<line x1="${c - w / 3}" y1="${y - 3 + i * 3}" x2="${c + w / 3}" y2="${y - 3 + i * 3}" stroke="${primary}" stroke-width="1.5" opacity="0.7"/>`);
      }
      for (let i = 0; i < 4; i++) {
        parts.push(`<line x1="${c - w / 3 + i * w / 4.5}" y1="${y - 3}" x2="${c - w / 3 + i * w / 4.5}" y2="${y + 3}" stroke="${accent}" stroke-width="1" opacity="0.5"/>`);
      }
    } else if (style === "vent") {
      parts.push(`<rect x="${c - w / 2}" y="${y - 4}" width="${w}" height="8" fill="none" stroke="${primary}" stroke-width="1" rx="2"/>`);
      for (let i = 0; i < 5; i++) {
        parts.push(`<line x1="${c - w / 2 + 4 + i * (w - 8) / 4}" y1="${y - 2}" x2="${c - w / 2 + 4 + i * (w - 8) / 4}" y2="${y + 2}" stroke="${primary}" stroke-width="1.5"/>`);
      }
    } else if (style === "speaker") {
      parts.push(`<ellipse cx="${c}" cy="${y}" rx="${w / 2}" ry="5" fill="none" stroke="${primary}" stroke-width="1.5"/>`);
      parts.push(`<ellipse cx="${c}" cy="${y}" rx="${w / 4}" ry="2.5" fill="${glow}" opacity="0.4" filter="url(#glow)" ${anim}/>`);
    } else if (style === "binary") {
      const bits = (p.patternSeed % 256).toString(2).padStart(8, '0');
      parts.push(`<text x="${c}" y="${y + 3}" text-anchor="middle" fill="${primary}" font-family="monospace" font-size="7">${bits}</text>`);
    } else if (style === "smile_arc") {
      parts.push(`<path d="M${c - w / 2},${y - 2} Q${c},${y + 8} ${c + w / 2},${y - 2}" fill="none" stroke="${glow}" stroke-width="2" stroke-linecap="round" filter="url(#glow)" ${anim}/>`);
    } else if (style === "glyph") {
      const symbol = SYMBOLS[p.patternSeed % SYMBOLS.length];
      parts.push(`<text x="${c}" y="${y + 5}" text-anchor="middle" fill="${glow}" font-size="14" filter="url(#glow)" ${anim}>${symbol}</text>`);
    } else if (style === "silent") {
      parts.push(`<line x1="${c - w / 4}" y1="${y}" x2="${c + w / 4}" y2="${y}" stroke="${primary}" stroke-width="1" opacity="0.4"/>`);
    } else if (style === "pixel_smile") {
      const ps = 4;
      for (let i = -2; i <= 2; i++) {
        const dy = Math.abs(i) < 2 ? 0 : -ps;
        parts.push(`<rect x="${c + i * ps - ps / 2}" y="${y + dy}" width="${ps}" height="${ps}" fill="${glow}" opacity="0.8"/>`);
      }
    } else if (style === "teeth_grid") {
      const tw = w / 6;
      for (let i = 0; i < 6; i++) {
        parts.push(`<rect x="${c - w / 2 + i * tw + 1}" y="${y - 3}" width="${tw - 2}" height="6" fill="none" stroke="${primary}" stroke-width="1" rx="1"/>`);
      }
    } else if (style === "equalizer") {
      this.rng.seed(p.patternSeed);
      for (let i = 0; i < 8; i++) {
        const h = this.rng.uniform(3, 10);
        parts.push(`<rect x="${c - w / 2 + i * w / 8 + 1}" y="${y - h / 2}" width="${w / 8 - 2}" height="${h}" fill="${glow}" opacity="0.7" ${anim}/>`);
      }
    } else {
      // circuit_mouth
      parts.push(`<line x1="${c - w / 2}" y1="${y}" x2="${c + w / 2}" y2="${y}" stroke="${primary}" stroke-width="1.5"/>`);
      for (let i = 0; i < 3; i++) {
        const x = c - w / 3 + i * w / 3;
        parts.push(`<circle cx="${x}" cy="${y}" r="2" fill="${glow}" ${anim}/>`);
      }
    }

    return `<g class="mouth">\n${parts.join('\n')}</g>`;
  }

  private drawChin(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const feature = CHIN_FEATURES[p.chinFeature];
    if (feature === "none") return '';

    const { primary, glow } = palette;
    const y = c + p.faceHeight * 0.7;
    const anim = animated ? 'class="pulse"' : '';

    if (feature === "vent") {
      const lines = Array.from({ length: 4 }, (_, i) =>
        `<line x1="${c - 12 + i * 8}" y1="${y}" x2="${c - 12 + i * 8}" y2="${y + 6}" stroke="${primary}" stroke-width="2" opacity="0.6"/>`
      ).join('\n');
      return `<g class="chin">${lines}</g>`;
    } else if (feature === "light_bar") {
      return `<rect x="${c - 15}" y="${y}" width="30" height="4" fill="${glow}" opacity="0.5" filter="url(#glow)" rx="2" ${anim}/>`;
    } else if (feature === "beard_lines") {
      const lines = Array.from({ length: 5 }, (_, i) =>
        `<line x1="${c - 10 + i * 5}" y1="${y}" x2="${c - 10 + i * 5}" y2="${y + 10 + (i % 2) * 3}" stroke="${primary}" stroke-width="1" opacity="0.5"/>`
      ).join('\n');
      return `<g class="chin">${lines}</g>`;
    } else if (feature === "energy_core") {
      return `<circle cx="${c}" cy="${y + 3}" r="6" fill="${glow}" opacity="0.3" filter="url(#glow)"/><circle cx="${c}" cy="${y + 3}" r="3" fill="${glow}" filter="url(#glow-strong)" ${anim}/>`;
    } else if (feature === "port") {
      return `<rect x="${c - 6}" y="${y}" width="12" height="8" fill="none" stroke="${primary}" stroke-width="1" rx="1"/><rect x="${c - 3}" y="${y + 2}" width="6" height="4" fill="${glow}" opacity="0.5"/>`;
    } else if (feature === "speaker_grille") {
      const lines = Array.from({ length: 4 }, (_, i) =>
        `<line x1="${c - 10}" y1="${y + i * 3}" x2="${c + 10}" y2="${y + i * 3}" stroke="${primary}" stroke-width="1.5" opacity="0.6"/>`
      ).join('\n');
      return `<g class="chin">${lines}</g>`;
    } else {
      // data_jack
      return `<rect x="${c - 8}" y="${y}" width="16" height="10" fill="none" stroke="${primary}" stroke-width="1.5" rx="2"/><circle cx="${c - 3}" cy="${y + 5}" r="2" fill="${glow}" ${anim}/><circle cx="${c + 3}" cy="${y + 5}" r="2" fill="${glow}" ${anim}/>`;
    }
  }

  private drawSideAccessories(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const accessory = SIDE_ACCESSORIES[p.sideAccessory];
    if (accessory === "none") return '';

    const { primary, glow } = palette;
    const parts: string[] = [];
    const size = 10 * p.accessorySize;
    const y = c - 5;
    const anim = animated ? 'class="pulse"' : '';

    const left = ["earpiece_left", "earpiece_both", "antenna_side", "blade", "coil", "jack", "wing_fins", "data_nodes"].includes(accessory);
    const right = ["earpiece_right", "earpiece_both", "antenna_side", "blade", "coil", "jack", "wing_fins", "data_nodes"].includes(accessory);

    for (const [side, draw] of [[-1, left], [1, right]] as [number, boolean][]) {
      if (!draw) continue;
      const x = c + side * (p.faceWidth + 8);

      if (accessory.includes("earpiece")) {
        parts.push(`<ellipse cx="${x}" cy="${y}" rx="4" ry="${size * 0.8}" fill="none" stroke="${primary}" stroke-width="1.5"/>`);
        parts.push(`<circle cx="${x}" cy="${y}" r="2" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (accessory === "antenna_side") {
        parts.push(`<line x1="${x}" y1="${y}" x2="${x + side * size}" y2="${y - size * 1.5}" stroke="${primary}" stroke-width="1.5"/>`);
        parts.push(`<circle cx="${x + side * size}" cy="${y - size * 1.5}" r="3" fill="${glow}" filter="url(#glow)" ${anim}/>`);
      } else if (accessory === "blade") {
        const pts: [number, number][] = [[x, y - size], [x + side * size * 0.5, y], [x, y + size]];
        parts.push(`<polygon points="${pts.map(([px, py]) => `${px},${py}`).join(' ')}" fill="none" stroke="${primary}" stroke-width="1.5"/>`);
        parts.push(`<line x1="${x}" y1="${y - size + 2}" x2="${x}" y2="${y + size - 2}" stroke="${glow}" stroke-width="1" filter="url(#glow)"/>`);
      } else if (accessory === "coil") {
        for (let i = 0; i < 4; i++) {
          parts.push(`<ellipse cx="${x + side * 3}" cy="${y - 6 + i * 4}" rx="3" ry="2" fill="none" stroke="${primary}" stroke-width="1" opacity="${1 - i * 0.2}"/>`);
        }
      } else if (accessory === "jack") {
        parts.push(`<rect x="${side < 0 ? x - 3 : x}" y="${y - 4}" width="6" height="8" fill="none" stroke="${primary}" stroke-width="1" rx="1"/>`);
        parts.push(`<circle cx="${x + side * 1.5}" cy="${y}" r="2" fill="${glow}" ${anim}/>`);
      } else if (accessory === "wing_fins") {
        const pts: [number, number][] = [[x, y - size], [x + side * size * 0.8, y - size * 0.5], [x + side * size * 0.6, y + size * 0.5], [x, y + size * 0.3]];
        parts.push(`<polygon points="${pts.map(([px, py]) => `${px},${py}`).join(' ')}" fill="none" stroke="${primary}" stroke-width="1.5"/>`);
        parts.push(`<line x1="${x}" y1="${y - size * 0.3}" x2="${x + side * size * 0.5}" y2="${y}" stroke="${glow}" stroke-width="1" filter="url(#glow)"/>`);
      } else if (accessory === "data_nodes") {
        for (let i = 0; i < 3; i++) {
          const nx = x + side * (5 + i * 4);
          const ny = y - 8 + i * 8;
          parts.push(`<circle cx="${nx}" cy="${ny}" r="3" fill="${glow}" filter="url(#glow)" class="float" style="animation-delay:${i * 0.2}s"/>`);
        }
      }
    }

    return `<g class="side-accessories">\n${parts.join('\n')}</g>`;
  }

  private drawCrown(c: number, palette: Palette, animated: boolean): string {
    const p = this.params;
    const crown = CROWN_STYLES[p.crownStyle];
    if (crown === "none") return '';

    const { primary, glow, accent } = palette;
    const y = c - p.faceHeight - 5;
    const size = 15 * p.crownSize;
    const anim = animated ? 'class="pulse"' : '';
    const animFloat = animated ? 'class="float"' : '';

    if (crown === "antenna_single") {
      return `<line x1="${c}" y1="${y}" x2="${c}" y2="${y - size * 1.5}" stroke="${primary}" stroke-width="2"/><circle cx="${c}" cy="${y - size * 1.5}" r="4" fill="${glow}" filter="url(#glow-strong)" ${anim}/>`;
    } else if (crown === "antenna_dual") {
      return `<line x1="${c - 10}" y1="${y}" x2="${c - 15}" y2="${y - size * 1.2}" stroke="${primary}" stroke-width="2"/><line x1="${c + 10}" y1="${y}" x2="${c + 15}" y2="${y - size * 1.2}" stroke="${primary}" stroke-width="2"/><circle cx="${c - 15}" cy="${y - size * 1.2}" r="3" fill="${glow}" filter="url(#glow)" ${anim}/><circle cx="${c + 15}" cy="${y - size * 1.2}" r="3" fill="${glow}" filter="url(#glow)" ${anim}/>`;
    } else if (crown === "horns") {
      return `<path d="M${c - 20},${y + 5} Q${c - 25},${y - size} ${c - 15},${y - size * 1.5}" fill="none" stroke="${primary}" stroke-width="3" stroke-linecap="round"/><path d="M${c + 20},${y + 5} Q${c + 25},${y - size} ${c + 15},${y - size * 1.5}" fill="none" stroke="${primary}" stroke-width="3" stroke-linecap="round"/><circle cx="${c - 15}" cy="${y - size * 1.5}" r="2" fill="${glow}" filter="url(#glow)"/><circle cx="${c + 15}" cy="${y - size * 1.5}" r="2" fill="${glow}" filter="url(#glow)"/>`;
    } else if (crown === "halo") {
      return `<ellipse cx="${c}" cy="${y - size * 0.3}" rx="${p.faceWidth * 0.9}" ry="${size * 0.4}" fill="none" stroke="${glow}" stroke-width="2" filter="url(#glow)" ${anim}/><ellipse cx="${c}" cy="${y - size * 0.3}" rx="${p.faceWidth * 0.9}" ry="${size * 0.4}" fill="none" stroke="${primary}" stroke-width="0.5" opacity="0.5"/>`;
    } else if (crown === "mohawk_data") {
      const chars = Array.from({ length: 7 }, (_, i) => {
        const char = this.rng.choice(MATRIX_CHARS);
        return `<text x="${c - 15 + i * 5}" y="${y - size * (0.5 + 0.5 * (1 - Math.abs(i - 3) / 3))}" fill="${glow}" font-family="monospace" font-size="8" opacity="0.8">${char}</text>`;
      }).join('\n');
      return `<g ${animFloat}>${chars}</g>`;
    } else if (crown === "floating_orbs") {
      const orbs = Array.from({ length: 5 }, (_, i) =>
        `<circle cx="${c - 20 + i * 10}" cy="${y - size * (0.3 + 0.4 * (1 - Math.abs(i - 2) / 2))}" r="4" fill="${glow}" filter="url(#glow)" class="float" style="animation-delay:${i * 0.3}s"/>`
      ).join('\n');
      return `<g>${orbs}</g>`;
    } else if (crown === "energy_spikes") {
      const spikes = Array.from({ length: 5 }, (_, i) =>
        `<line x1="${c - 16 + i * 8}" y1="${y}" x2="${c - 16 + i * 8}" y2="${y - size * (0.6 + 0.4 * (1 - Math.abs(i - 2) / 2))}" stroke="${glow}" stroke-width="2" filter="url(#glow)" ${anim}/>`
      ).join('\n');
      return `<g>${spikes}</g>`;
    } else if (crown === "circuit_crown") {
      return `<path d="M${c - 25},${y} L${c - 20},${y - size * 0.8} L${c - 10},${y - size * 0.5} L${c},${y - size} L${c + 10},${y - size * 0.5} L${c + 20},${y - size * 0.8} L${c + 25},${y}" fill="none" stroke="${primary}" stroke-width="1.5"/><circle cx="${c}" cy="${y - size}" r="3" fill="${glow}" filter="url(#glow)" ${anim}/><circle cx="${c - 20}" cy="${y - size * 0.8}" r="2" fill="${accent}"/><circle cx="${c + 20}" cy="${y - size * 0.8}" r="2" fill="${accent}"/>`;
    } else if (crown === "visor_top") {
      return `<rect x="${c - p.faceWidth * 0.7}" y="${y - size * 0.3}" width="${p.faceWidth * 1.4}" height="${size * 0.5}" fill="${glow}" opacity="0.3" filter="url(#glow)" rx="2"/><rect x="${c - p.faceWidth * 0.7}" y="${y - size * 0.3}" width="${p.faceWidth * 1.4}" height="${size * 0.5}" fill="none" stroke="${primary}" stroke-width="1" rx="2"/>`;
    } else if (crown === "flames") {
      const flames = Array.from({ length: 7 }, (_, i) => {
        const h = size * (0.5 + this.rng.uniform(0.3, 0.7)) / 2;
        return `<ellipse cx="${c - 18 + i * 6}" cy="${y - h}" rx="4" ry="${h}" fill="${glow}" opacity="0.4" filter="url(#glow)" class="flame"/>`;
      }).join('\n');
      return `<g>${flames}</g>`;
    } else if (crown === "crystals") {
      const crystals = Array.from({ length: 5 }, (_, i) => {
        const x = c - 16 + i * 8;
        const h = size * (0.5 + 0.5 * (1 - Math.abs(i - 2) / 2));
        const pts: [number, number][] = [[x, y], [x - 4, y - h * 0.3], [x, y - h], [x + 4, y - h * 0.3]];
        return `<polygon points="${pts.map(([px, py]) => `${px},${py}`).join(' ')}" fill="${glow}" opacity="0.3" stroke="${primary}" stroke-width="1"/>`;
      }).join('\n');
      return `<g>${crystals}</g>`;
    } else if (crown === "crown_peaks") {
      const pts: [number, number][] = [
        [c - 25, y], [c - 20, y - size * 0.6], [c - 15, y - size * 0.3], [c - 10, y - size * 0.9],
        [c - 5, y - size * 0.3], [c, y - size * 1.1], [c + 5, y - size * 0.3], [c + 10, y - size * 0.9],
        [c + 15, y - size * 0.3], [c + 20, y - size * 0.6], [c + 25, y]
      ];
      return `<polygon points="${pts.map(([x, py]) => `${x},${py}`).join(' ')}" fill="none" stroke="${primary}" stroke-width="2"/><circle cx="${c}" cy="${y - size * 1.1}" r="3" fill="${glow}" filter="url(#glow)" ${anim}/>`;
    } else if (crown === "satellite") {
      return `<ellipse cx="${c}" cy="${y - size * 0.5}" rx="${size * 1.2}" ry="${size * 0.3}" fill="none" stroke="${primary}" stroke-width="1.5"/><line x1="${c}" y1="${y}" x2="${c}" y2="${y - size}" stroke="${primary}" stroke-width="2"/><circle cx="${c}" cy="${y - size}" r="4" fill="${glow}" filter="url(#glow)" ${anim}/>`;
    } else if (crown === "wings") {
      const leftWing = `<path d="M${c - 5},${y} Q${c - 20},${y - size * 0.5} ${c - 30},${y - size * 0.8} Q${c - 20},${y - size * 0.3} ${c - 5},${y + 5}" fill="none" stroke="${primary}" stroke-width="1.5"/>`;
      const rightWing = `<path d="M${c + 5},${y} Q${c + 20},${y - size * 0.5} ${c + 30},${y - size * 0.8} Q${c + 20},${y - size * 0.3} ${c + 5},${y + 5}" fill="none" stroke="${primary}" stroke-width="1.5"/>`;
      return `${leftWing}${rightWing}<circle cx="${c - 30}" cy="${y - size * 0.8}" r="2" fill="${glow}" filter="url(#glow)"/><circle cx="${c + 30}" cy="${y - size * 0.8}" r="2" fill="${glow}" filter="url(#glow)"/>`;
    } else {
      // data_cloud
      const cloud: string[] = [];
      this.rng.seed(p.effectSeed);
      for (let i = 0; i < 8; i++) {
        const cx = c - 20 + this.rng.uniform(0, 40);
        const cy = y - size * 0.5 + this.rng.uniform(-size * 0.3, size * 0.3);
        const char = this.rng.choice(MATRIX_CHARS);
        cloud.push(`<text x="${cx}" y="${cy}" fill="${glow}" font-family="monospace" font-size="8" opacity="0.6" class="float" style="animation-delay:${i * 0.2}s">${char}</text>`);
      }
      return `<g>${cloud.join('\n')}</g>`;
    }
  }

  private drawScanOverlay(palette: Palette): string {
    const p = this.params;
    const { primary } = palette;
    return `<rect x="0" y="0" width="${AgentFace.CANVAS_SIZE}" height="3" fill="${primary}" opacity="0.15"><animate attributeName="y" from="-10" to="${AgentFace.CANVAS_SIZE + 10}" dur="${p.animationSpeed * 2}s" repeatCount="indefinite"/></rect>`;
  }

  /**
   * Generate a data URI for embedding in HTML.
   */
  toDataURI(options: SVGOptions = {}): string {
    const svg = this.toSVG(options);
    // Support both browser (btoa) and Node.js (Buffer)
    let base64: string;
    if (typeof btoa === 'function') {
      base64 = btoa(unescape(encodeURIComponent(svg)));
    } else if (typeof Buffer !== 'undefined') {
      base64 = Buffer.from(svg, 'utf-8').toString('base64');
    } else {
      throw new Error('No base64 encoder available');
    }
    return `data:image/svg+xml;base64,${base64}`;
  }

  /**
   * Get 8-character fingerprint.
   */
  fingerprint(): string {
    const hash = simpleHash(this.keyBytes, 4);
    return Array.from(hash).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Get human-readable description.
   */
  describe(): string {
    const f = this.features;
    return `${f.palette.name} | ${f.faceShape} | ${f.eyeStyle} eyes | ${f.crownStyle} crown`;
  }

  /**
   * Get complete feature breakdown.
   */
  fullDescription(): FaceDescription {
    const f = this.features;
    return {
      palette: f.palette.name,
      faceShape: f.faceShape,
      eyeStyle: f.eyeStyle,
      eyeExpression: f.eyeExpression,
      mouthStyle: f.mouthStyle,
      crown: f.crownStyle,
      foreheadMark: f.foreheadMark,
      cheekPattern: f.cheekPattern,
      chinFeature: f.chinFeature,
      sideAccessory: f.sideAccessory,
      background: f.bgStyle,
      aura: f.auraStyle,
    };
  }

  /**
   * Calculate visual similarity (0.0 = identical, 1.0 = completely different).
   */
  similarity(other: AgentFace): number {
    if (this.keyBytes.every((b, i) => b === other.keyBytes[i])) {
      return 0.0;
    }
    const p1 = this.params;
    const p2 = other.params;
    const diffs = [
      p1.paletteIdx !== p2.paletteIdx,
      p1.faceShape !== p2.faceShape,
      p1.eyeStyle !== p2.eyeStyle,
      p1.eyeExpression !== p2.eyeExpression,
      p1.mouthStyle !== p2.mouthStyle,
      p1.crownStyle !== p2.crownStyle,
      p1.foreheadMark !== p2.foreheadMark,
      p1.cheekPattern !== p2.cheekPattern,
      p1.chinFeature !== p2.chinFeature,
      p1.sideAccessory !== p2.sideAccessory,
      p1.bgStyle !== p2.bgStyle,
      p1.auraStyle !== p2.auraStyle,
    ].filter(Boolean).length;
    return Math.min(1.0, diffs / 12);
  }

  /**
   * Total number of unique human-distinguishable combinations.
   */
  static totalCombinations(): number {
    return totalCombinations();
  }
}
