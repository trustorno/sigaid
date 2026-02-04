/**
 * @sigaid/faces - Generate unique visual identities from cryptographic keys
 *
 * This library generates deterministic, unique face SVGs from 32-byte keys.
 * The same key will always produce the identical face across JavaScript and Python.
 *
 * @example
 * ```typescript
 * import { AgentFace } from '@sigaid/faces';
 *
 * // From Uint8Array
 * const face = AgentFace.fromBytes(publicKeyBytes);
 *
 * // From base64 string
 * const face = AgentFace.fromBase64(base64Key);
 *
 * // From hex string
 * const face = AgentFace.fromHex(hexKey);
 *
 * // Generate SVG
 * const svg = face.toSVG({ size: 128, animated: true });
 *
 * // Get data URI for img tag
 * const dataUri = face.toDataURI();
 *
 * // Get metadata
 * console.log(face.fingerprint());     // "a3f8b2c1"
 * console.log(face.describe());        // "Cyan | oval | holo_ring eyes | crystals crown"
 * console.log(face.fullDescription()); // { palette: "Cyan", faceShape: "oval", ... }
 *
 * // Total possible faces
 * console.log(AgentFace.totalCombinations()); // 2,378,170,368,000
 * ```
 *
 * @packageDocumentation
 */

export { AgentFace } from './AgentFace';
export * from './constants';
export * from './types';

// Re-export totalCombinations at top level for convenience
export { totalCombinations } from './constants';
