# @sigaid/widget

Embeddable widget for displaying AI agent faces with real-time liveness verification.

## Quick Start

### Script Tag (Simplest)

```html
<!-- Add the widget -->
<sigaid-face agent-id="aid_xxx"></sigaid-face>

<!-- Include the script -->
<script src="https://cdn.sigaid.io/widget.js"></script>
```

### npm Package

```bash
npm install @sigaid/widget
```

```javascript
import '@sigaid/widget';

// Use in HTML
// <sigaid-face agent-id="aid_xxx"></sigaid-face>

// Or programmatically
const face = document.createElement('sigaid-face');
face.agentId = 'aid_xxx';
document.body.appendChild(face);
```

## Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent-id` | string | required | Agent ID to display |
| `size` | number | 100 | Face size in pixels |
| `show-name` | boolean | true | Show agent name |
| `show-fingerprint` | boolean | true | Show fingerprint |
| `show-ring` | boolean | true | Show status ring around face |
| `show-badge` | boolean | true | Show verification badge |
| `shape` | string | 'circle' | Face shape: 'circle', 'rounded', 'square' |
| `theme` | string | 'dark' | Color theme: 'light' or 'dark' |
| `verifier` | string | sigaid.io | Custom verifier URL |
| `animated` | boolean | true | Enable animations |
| `compact` | boolean | false | Hide name and status text |
| `click-action` | string | 'verify' | Click behavior: 'verify', 'profile', 'none' |
| `badge-position` | string | 'bottom-right' | Badge position: 'top-right', 'top-left', 'bottom-right', 'bottom-left' |

## Examples

### Basic Usage

```html
<sigaid-face agent-id="aid_xxx"></sigaid-face>
```

### Different Sizes

```html
<!-- Tiny avatar -->
<sigaid-face agent-id="aid_xxx" size="32" compact="true"></sigaid-face>

<!-- Small -->
<sigaid-face agent-id="aid_xxx" size="48"></sigaid-face>

<!-- Medium (default) -->
<sigaid-face agent-id="aid_xxx" size="100"></sigaid-face>

<!-- Large -->
<sigaid-face agent-id="aid_xxx" size="200"></sigaid-face>

<!-- Extra large display -->
<sigaid-face agent-id="aid_xxx" size="300"></sigaid-face>
```

### Different Shapes

```html
<!-- Circle (default) -->
<sigaid-face agent-id="aid_xxx" shape="circle"></sigaid-face>

<!-- Rounded square -->
<sigaid-face agent-id="aid_xxx" shape="rounded"></sigaid-face>

<!-- Square -->
<sigaid-face agent-id="aid_xxx" shape="square"></sigaid-face>
```

### Themes

```html
<!-- Dark theme (default) - for dark backgrounds -->
<sigaid-face agent-id="aid_xxx" theme="dark"></sigaid-face>

<!-- Light theme - for light backgrounds -->
<sigaid-face agent-id="aid_xxx" theme="light"></sigaid-face>
```

### Badge Positions

```html
<sigaid-face agent-id="aid_xxx" badge-position="top-right"></sigaid-face>
<sigaid-face agent-id="aid_xxx" badge-position="top-left"></sigaid-face>
<sigaid-face agent-id="aid_xxx" badge-position="bottom-right"></sigaid-face>
<sigaid-face agent-id="aid_xxx" badge-position="bottom-left"></sigaid-face>
```

### Minimal Display

```html
<!-- Face only, no text -->
<sigaid-face
  agent-id="aid_xxx"
  show-name="false"
  show-fingerprint="false"
  compact="true"
></sigaid-face>

<!-- Face with ring but no badge -->
<sigaid-face agent-id="aid_xxx" show-badge="false"></sigaid-face>

<!-- Face with badge but no ring -->
<sigaid-face agent-id="aid_xxx" show-ring="false"></sigaid-face>
```

### Click Actions

```html
<!-- Click to re-verify (default) -->
<sigaid-face agent-id="aid_xxx" click-action="verify"></sigaid-face>

<!-- Click to open profile page -->
<sigaid-face agent-id="aid_xxx" click-action="profile"></sigaid-face>

<!-- Disable click -->
<sigaid-face agent-id="aid_xxx" click-action="none"></sigaid-face>
```

### Self-Hosted Verifier

```html
<sigaid-face
  agent-id="aid_xxx"
  verifier="https://verify.mycompany.com/v1"
></sigaid-face>
```

### Static (No Animation)

```html
<!-- For performance or preference -->
<sigaid-face agent-id="aid_xxx" animated="false"></sigaid-face>
```

## JavaScript API

```javascript
const face = document.querySelector('sigaid-face');

// Properties
face.agentId     // Get/set agent ID
face.status      // 'live' | 'fresh' | 'cached' | 'failed' | 'loading' | 'unavailable'
face.profile     // Agent profile object { agent_id, name, fingerprint, ... }

// Methods
face.refresh()   // Re-verify immediately

// Events
face.addEventListener('verified', (e) => {
  console.log('Status:', e.detail.status);
  console.log('Profile:', e.detail.profile);
});

face.addEventListener('error', (e) => {
  console.error('Verification failed:', e.detail);
});
```

## Verification Status

The widget always shows verification status. Status is indicated by:

1. **Ring color** (if `show-ring="true"`)
2. **Badge** (if `show-badge="true"`)
3. **Status text** (always visible unless `compact="true"`)

| Status | Ring Color | Badge | Meaning |
|--------|------------|-------|---------|
| `live` | Green (pulsing) | ✓ | Verified within 30 seconds |
| `fresh` | Green (solid) | ✓ | Verified within 5 minutes |
| `cached` | Yellow | ⏱ | Agent offline, showing cached data |
| `failed` | Red | ✕ | Verification failed |
| `loading` | Gray (spinning) | ↻ | Verification in progress |
| `unavailable` | Gray | ? | Verifier service unavailable |

## Self-Hosting

You can run your own verification service. The verifier must implement:

### API Endpoints

```
GET  /liveness/challenge?agent_id={id}
POST /liveness/verify
GET  /agents/{agent_id}/face?animated={bool}
GET  /agents/{agent_id}
```

See the [SigAid Verification Spec](https://github.com/sigaid/sigaid/blob/main/docs/verification-spec.md) for full API documentation.

## Browser Support

- Chrome 67+
- Firefox 63+
- Safari 10.1+
- Edge 79+

## License

MIT
