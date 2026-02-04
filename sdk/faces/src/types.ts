/**
 * Type definitions for AgentFace
 */

import type { Palette, FaceShape, EyeStyle, EyeExpression, MouthStyle, CrownStyle, ForeheadMark, CheekPattern, ChinFeature, SideAccessory, BgStyle, AuraStyle } from './constants';

/**
 * Parameters extracted from key bytes for face generation.
 */
export interface FaceParams {
  // Core identity (bytes 0-3)
  paletteIdx: number;
  faceShape: number;
  eyeStyle: number;
  eyeExpression: number;

  // Face features (bytes 4-7)
  mouthStyle: number;
  crownStyle: number;
  foreheadMark: number;
  cheekPattern: number;

  // Additional features (bytes 8-11)
  chinFeature: number;
  sideAccessory: number;
  bgStyle: number;
  auraStyle: number;

  // Continuous variations (bytes 12-19)
  faceWidth: number;
  faceHeight: number;
  eyeSize: number;
  eyeSpacing: number;
  mouthWidth: number;
  crownSize: number;
  markSize: number;
  accessorySize: number;

  // Effects (bytes 20-23)
  glowIntensity: number;
  animationSpeed: number;
  glitchAmount: number;
  particleDensity: number;

  // Seeds for randomization (bytes 24-31)
  patternSeed: number;
  circuitSeed: number;
  particleSeed: number;
  effectSeed: number;
}

/**
 * Full feature description for an agent face.
 */
export interface FaceDescription {
  palette: string;
  faceShape: FaceShape;
  eyeStyle: EyeStyle;
  eyeExpression: EyeExpression;
  mouthStyle: MouthStyle;
  crown: CrownStyle;
  foreheadMark: ForeheadMark;
  cheekPattern: CheekPattern;
  chinFeature: ChinFeature;
  sideAccessory: SideAccessory;
  background: BgStyle;
  aura: AuraStyle;
}

/**
 * Options for SVG generation.
 */
export interface SVGOptions {
  size?: number;
  animated?: boolean;
}

/**
 * Features exposed by AgentFace for external use.
 */
export interface AgentFaceFeatures {
  palette: Palette;
  faceShape: FaceShape;
  eyeStyle: EyeStyle;
  eyeExpression: EyeExpression;
  mouthStyle: MouthStyle;
  crownStyle: CrownStyle;
  foreheadMark: ForeheadMark;
  cheekPattern: CheekPattern;
  chinFeature: ChinFeature;
  sideAccessory: SideAccessory;
  bgStyle: BgStyle;
  auraStyle: AuraStyle;
}
