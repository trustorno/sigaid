# @sigaid/faces

Generate unique, deterministic visual identities from cryptographic keys.

**2.4 trillion unique faces** - each one deterministically derived from a 32-byte key.

## Installation

```bash
npm install @sigaid/faces
# or
yarn add @sigaid/faces
# or
pnpm add @sigaid/faces
```

## Usage

### Basic Usage

```typescript
import { AgentFace } from '@sigaid/faces';

// From any 32-byte key (public key, hash, etc.)
const keyBytes = new Uint8Array(32);
crypto.getRandomValues(keyBytes);

const face = AgentFace.fromBytes(keyBytes);

// Generate SVG
const svg = face.toSVG({ size: 128, animated: true });
document.getElementById('avatar').innerHTML = svg;
```

### From Different Formats

```typescript
// From base64 (e.g., from API response)
const face = AgentFace.fromBase64('SGVsbG8gV29ybGQhIQ==...');

// From hex string
const face = AgentFace.fromHex('deadbeef...');

// Direct construction
const face = new AgentFace(uint8Array);
```

### Get Metadata

```typescript
const face = AgentFace.fromBytes(keyBytes);

// 8-character fingerprint
console.log(face.fingerprint());
// => "a3f8b2c1"

// Human-readable description
console.log(face.describe());
// => "Cyan | oval | holo_ring eyes | crystals crown"

// Full feature breakdown
console.log(face.fullDescription());
// => { palette: "Cyan", faceShape: "oval", eyeStyle: "holo_ring", ... }
```

### React Component

```tsx
import { AgentFace } from '@sigaid/faces';
import { useMemo } from 'react';

function AgentAvatar({ publicKey, size = 64 }: { publicKey: Uint8Array; size?: number }) {
  const svg = useMemo(() => {
    const face = AgentFace.fromBytes(publicKey);
    return face.toSVG({ size, animated: true });
  }, [publicKey, size]);

  return <div dangerouslySetInnerHTML={{ __html: svg }} />;
}
```

### Data URI for img tags

```typescript
const face = AgentFace.fromBytes(keyBytes);
const dataUri = face.toDataURI({ size: 64 });

// Use in img tag
const img = document.createElement('img');
img.src = dataUri;
```

### Compare Faces

```typescript
const face1 = AgentFace.fromBytes(key1);
const face2 = AgentFace.fromBytes(key2);

// 0.0 = identical, 1.0 = completely different
const similarity = face1.similarity(face2);
console.log(`Similarity: ${similarity}`);
```

## Features

Each face is composed of 12 feature categories:

| Feature | Variations | Description |
|---------|------------|-------------|
| Palette | 20 | Color scheme (Cyan, Matrix, Purple, Gold, etc.) |
| Face Shape | 12 | Oval, angular, hexagonal, diamond, star, etc. |
| Eye Style | 16 | Holo ring, matrix scan, compound, flame, etc. |
| Eye Expression | 8 | Neutral, wide, narrow, squint, shock, etc. |
| Mouth Style | 14 | Data stream, waveform, grid, smile, etc. |
| Crown | 16 | Antenna, horns, halo, flames, wings, etc. |
| Forehead Mark | 12 | Third eye, barcode, omega, infinity, etc. |
| Cheek Pattern | 10 | Circuit lines, tribal bars, vents, etc. |
| Chin Feature | 8 | Vent, light bar, energy core, etc. |
| Side Accessory | 10 | Earpiece, antenna, blade, wing fins, etc. |
| Background | 6 | Data rain, hex grid, circuit, particles, etc. |
| Aura | 6 | Glow, double ring, glitch, electric, etc. |

**Total combinations: 2,378,170,368,000** (~2.4 trillion)

## API Reference

### `AgentFace`

#### Static Methods

- `AgentFace.fromBytes(bytes: Uint8Array): AgentFace` - Create from raw bytes
- `AgentFace.fromBase64(base64: string): AgentFace` - Create from base64 string
- `AgentFace.fromHex(hex: string): AgentFace` - Create from hex string
- `AgentFace.totalCombinations(): number` - Get total unique face count

#### Instance Methods

- `toSVG(options?: { size?: number; animated?: boolean }): string` - Generate SVG string
- `toDataURI(options?: { size?: number; animated?: boolean }): string` - Generate data URI
- `fingerprint(): string` - Get 8-character fingerprint
- `describe(): string` - Get human-readable description
- `fullDescription(): FaceDescription` - Get complete feature breakdown
- `similarity(other: AgentFace): number` - Compare two faces (0-1)

#### Properties

- `features: AgentFaceFeatures` - Access all extracted features

## Browser Support

Works in all modern browsers. For older browsers, ensure you have:
- `Uint8Array` support
- `btoa`/`atob` for base64 encoding

## Cross-Platform Compatibility

This library produces **identical output** to the Python implementation (`sigaid.identity.agent_face`). The same 32-byte key will generate the exact same SVG in both JavaScript and Python.

## License

MIT
