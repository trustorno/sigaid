/**
 * SigAid Face Widget - Embeddable agent identity verification
 *
 * Displays an agent's face with real-time liveness verification.
 *
 * Usage:
 *   <sigaid-face agent-id="aid_xxx"></sigaid-face>
 *   <script src="https://cdn.sigaid.io/widget.js"></script>
 *
 * Or with custom verifier:
 *   <sigaid-face agent-id="aid_xxx" verifier="https://verify.mycompany.com"></sigaid-face>
 */

// Types
export type LivenessStatus = 'live' | 'fresh' | 'cached' | 'failed' | 'loading' | 'unavailable';

export interface AgentProfile {
  agent_id: string;
  name: string;
  fingerprint: string;
  verified_domain?: string;
  metadata?: Record<string, unknown>;
}

export interface LivenessResult {
  status: LivenessStatus;
  agent_id: string;
  profile?: AgentProfile;
  verified_at?: string;
  cache_until?: string;
  error?: string;
}

export interface WidgetOptions {
  agentId: string;
  size?: number;
  showName?: boolean;
  showFingerprint?: boolean;
  showRing?: boolean;
  showBadge?: boolean;
  shape?: 'circle' | 'rounded' | 'square';
  theme?: 'light' | 'dark';
  verifier?: string;
  animated?: boolean;
  compact?: boolean;
  clickAction?: 'verify' | 'profile' | 'none';
  badgePosition?: 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left';
  onVerified?: (result: LivenessResult) => void;
  onError?: (error: Error) => void;
}

// Constants
const DEFAULT_VERIFIER = 'https://api.sigaid.io/v1';
const VERIFICATION_INTERVAL = 30000; // 30 seconds
const RETRY_DELAY = 5000; // 5 seconds

// Status colors
const STATUS_COLORS: Record<LivenessStatus, { ring: string; glow: string }> = {
  live: { ring: '#00ff88', glow: 'rgba(0, 255, 136, 0.4)' },
  fresh: { ring: '#00cc6a', glow: 'rgba(0, 204, 106, 0.3)' },
  cached: { ring: '#ffaa00', glow: 'rgba(255, 170, 0, 0.3)' },
  failed: { ring: '#ff4444', glow: 'rgba(255, 68, 68, 0.3)' },
  loading: { ring: '#888888', glow: 'rgba(136, 136, 136, 0.3)' },
  unavailable: { ring: '#666666', glow: 'rgba(102, 102, 102, 0.2)' },
};

/**
 * SigAid Face Web Component
 */
export class SigAidFaceElement extends HTMLElement {
  private shadow: ShadowRoot;
  private container: HTMLDivElement;
  private faceContainer: HTMLDivElement;
  private nameElement: HTMLDivElement;
  private statusElement: HTMLDivElement;
  private ringElement: HTMLDivElement;
  private badgeElement: HTMLDivElement;

  private _agentId: string = '';
  private _status: LivenessStatus = 'loading';
  private _profile: AgentProfile | null = null;
  private _verifierUrl: string = DEFAULT_VERIFIER;
  private _size: number = 100;
  private _showName: boolean = true;
  private _showFingerprint: boolean = true;
  private _showRing: boolean = true;
  private _showBadge: boolean = true;
  private _shape: 'circle' | 'rounded' | 'square' = 'circle';
  private _animated: boolean = true;
  private _theme: 'light' | 'dark' = 'dark';
  private _compact: boolean = false;
  private _clickAction: 'verify' | 'profile' | 'none' = 'verify';
  private _badgePosition: 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left' = 'bottom-right';

  private verificationInterval: number | null = null;
  private abortController: AbortController | null = null;

  // Callbacks
  public onVerified?: (result: LivenessResult) => void;
  public onError?: (error: Error) => void;

  static get observedAttributes() {
    return [
      'agent-id', 'size', 'show-name', 'show-fingerprint', 'show-ring', 'show-badge',
      'shape', 'theme', 'verifier', 'animated', 'compact', 'click-action', 'badge-position'
    ];
  }

  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: 'open' });

    // Create container
    this.container = document.createElement('div');
    this.container.className = 'sigaid-face-container';

    // Create ring element (for status indication)
    this.ringElement = document.createElement('div');
    this.ringElement.className = 'sigaid-ring';

    // Create face container
    this.faceContainer = document.createElement('div');
    this.faceContainer.className = 'sigaid-face';

    // Create badge element (verification status indicator)
    this.badgeElement = document.createElement('div');
    this.badgeElement.className = 'sigaid-badge';

    // Create name element
    this.nameElement = document.createElement('div');
    this.nameElement.className = 'sigaid-name';

    // Create status element (always visible)
    this.statusElement = document.createElement('div');
    this.statusElement.className = 'sigaid-status';

    // Assemble
    this.container.appendChild(this.ringElement);
    this.container.appendChild(this.faceContainer);
    this.container.appendChild(this.badgeElement);
    this.container.appendChild(this.nameElement);
    this.container.appendChild(this.statusElement);

    this.shadow.appendChild(this.createStyles());
    this.shadow.appendChild(this.container);

    // Click handler
    this.container.addEventListener('click', () => this.handleClick());
  }

  connectedCallback() {
    this.updateFromAttributes();
    if (this._agentId) {
      this.startVerification();
    }
  }

  disconnectedCallback() {
    this.stopVerification();
  }

  attributeChangedCallback(name: string, oldValue: string, newValue: string) {
    if (oldValue === newValue) return;

    switch (name) {
      case 'agent-id':
        this._agentId = newValue || '';
        if (this._agentId) {
          this.startVerification();
        }
        break;
      case 'size':
        this._size = parseInt(newValue, 10) || 100;
        this.updateStyles();
        break;
      case 'show-name':
        this._showName = newValue !== 'false';
        this.updateDisplay();
        break;
      case 'show-fingerprint':
        this._showFingerprint = newValue !== 'false';
        this.updateDisplay();
        break;
      case 'show-ring':
        this._showRing = newValue !== 'false';
        this.updateStyles();
        break;
      case 'show-badge':
        this._showBadge = newValue !== 'false';
        this.updateStyles();
        break;
      case 'shape':
        this._shape = (newValue as 'circle' | 'rounded' | 'square') || 'circle';
        this.updateStyles();
        break;
      case 'theme':
        this._theme = newValue === 'light' ? 'light' : 'dark';
        this.updateStyles();
        break;
      case 'verifier':
        this._verifierUrl = newValue || DEFAULT_VERIFIER;
        break;
      case 'animated':
        this._animated = newValue !== 'false';
        this.updateDisplay();
        break;
      case 'compact':
        this._compact = newValue === 'true';
        this.updateStyles();
        break;
      case 'click-action':
        this._clickAction = (newValue as 'verify' | 'profile' | 'none') || 'verify';
        break;
      case 'badge-position':
        this._badgePosition = (newValue as 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left') || 'bottom-right';
        this.updateStyles();
        break;
    }
  }

  private handleClick() {
    switch (this._clickAction) {
      case 'verify':
        this.refresh();
        break;
      case 'profile':
        // Open profile page
        if (this._agentId) {
          window.open(`${this._verifierUrl}/agents/${encodeURIComponent(this._agentId)}`, '_blank');
        }
        break;
      case 'none':
        // Do nothing
        break;
    }
  }

  private updateFromAttributes() {
    this._agentId = this.getAttribute('agent-id') || '';
    this._size = parseInt(this.getAttribute('size') || '100', 10);
    this._showName = this.getAttribute('show-name') !== 'false';
    this._showFingerprint = this.getAttribute('show-fingerprint') !== 'false';
    this._showRing = this.getAttribute('show-ring') !== 'false';
    this._showBadge = this.getAttribute('show-badge') !== 'false';
    this._shape = (this.getAttribute('shape') as 'circle' | 'rounded' | 'square') || 'circle';
    this._theme = this.getAttribute('theme') === 'light' ? 'light' : 'dark';
    this._verifierUrl = this.getAttribute('verifier') || DEFAULT_VERIFIER;
    this._animated = this.getAttribute('animated') !== 'false';
    this._compact = this.getAttribute('compact') === 'true';
    this._clickAction = (this.getAttribute('click-action') as 'verify' | 'profile' | 'none') || 'verify';
    this._badgePosition = (this.getAttribute('badge-position') as 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left') || 'bottom-right';
    this.updateStyles();
  }

  private createStyles(): HTMLStyleElement {
    const style = document.createElement('style');
    style.textContent = `
      :host {
        display: inline-block;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }

      .sigaid-face-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        cursor: pointer;
        user-select: none;
      }

      .sigaid-face-container:hover .sigaid-ring {
        filter: brightness(1.2);
      }

      .sigaid-ring {
        position: absolute;
        pointer-events: none;
        transition: box-shadow 0.3s ease, border-color 0.3s ease, filter 0.2s ease;
      }

      .sigaid-ring.circle { border-radius: 50%; }
      .sigaid-ring.rounded { border-radius: 20%; }
      .sigaid-ring.square { border-radius: 4px; }

      .sigaid-ring.pulse {
        animation: pulse 2s ease-in-out infinite;
      }

      .sigaid-ring.hidden {
        display: none;
      }

      @keyframes pulse {
        0%, 100% { opacity: 0.8; }
        50% { opacity: 1; }
      }

      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      @keyframes badge-pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
      }

      .sigaid-face {
        overflow: hidden;
        background: #0a0a0f;
        position: relative;
      }

      .sigaid-face.circle { border-radius: 50%; }
      .sigaid-face.rounded { border-radius: 15%; }
      .sigaid-face.square { border-radius: 4px; }

      .sigaid-face img, .sigaid-face svg {
        display: block;
        width: 100%;
        height: 100%;
      }

      /* Verification Badge */
      .sigaid-badge {
        position: absolute;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: bold;
        color: white;
        border: 2px solid #0a0a0f;
        z-index: 10;
      }

      .sigaid-badge.hidden { display: none; }

      .sigaid-badge.live, .sigaid-badge.fresh {
        background: #00ff88;
        animation: badge-pulse 2s ease-in-out infinite;
      }
      .sigaid-badge.live::after, .sigaid-badge.fresh::after {
        content: '✓';
      }

      .sigaid-badge.cached {
        background: #ffaa00;
      }
      .sigaid-badge.cached::after {
        content: '⏱';
        font-size: 8px;
      }

      .sigaid-badge.failed {
        background: #ff4444;
      }
      .sigaid-badge.failed::after {
        content: '✕';
      }

      .sigaid-badge.loading {
        background: #888;
      }
      .sigaid-badge.loading::after {
        content: '↻';
        animation: spin 1s linear infinite;
        display: inline-block;
      }

      .sigaid-badge.unavailable {
        background: #666;
      }
      .sigaid-badge.unavailable::after {
        content: '?';
      }

      /* Badge positions */
      .sigaid-badge.top-right { top: 0; right: 0; }
      .sigaid-badge.top-left { top: 0; left: 0; }
      .sigaid-badge.bottom-right { bottom: 0; right: 0; }
      .sigaid-badge.bottom-left { bottom: 0; left: 0; }

      .sigaid-name {
        margin-top: 8px;
        font-weight: 600;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
      }

      .sigaid-name.hidden { display: none; }

      /* Status - Always visible */
      .sigaid-status {
        font-size: 11px;
        text-align: center;
        padding: 2px 8px;
        border-radius: 10px;
        margin-top: 4px;
        font-weight: 500;
      }

      .sigaid-status.live, .sigaid-status.fresh {
        background: rgba(0, 255, 136, 0.2);
        color: #00ff88;
      }

      .sigaid-status.cached {
        background: rgba(255, 170, 0, 0.2);
        color: #ffaa00;
      }

      .sigaid-status.failed {
        background: rgba(255, 68, 68, 0.2);
        color: #ff4444;
      }

      .sigaid-status.loading {
        background: rgba(136, 136, 136, 0.2);
        color: #888;
      }

      .sigaid-status.unavailable {
        background: rgba(102, 102, 102, 0.2);
        color: #666;
      }

      /* Compact mode */
      .sigaid-face-container.compact .sigaid-name,
      .sigaid-face-container.compact .sigaid-status {
        display: none;
      }

      /* Theme: Dark */
      :host([theme="dark"]) .sigaid-face-container,
      .sigaid-face-container {
        color: #ffffff;
      }

      :host([theme="dark"]) .sigaid-badge,
      .sigaid-badge {
        border-color: #0a0a0f;
      }

      /* Theme: Light */
      :host([theme="light"]) .sigaid-face-container {
        color: #1a1a2e;
      }

      :host([theme="light"]) .sigaid-face {
        background: #f0f0f5;
      }

      :host([theme="light"]) .sigaid-badge {
        border-color: #f0f0f5;
      }

      :host([theme="light"]) .sigaid-status.live,
      :host([theme="light"]) .sigaid-status.fresh {
        background: rgba(0, 200, 100, 0.15);
        color: #00aa55;
      }

      /* Loading spinner on ring */
      .sigaid-ring.loading {
        border: 3px solid transparent;
        border-top-color: #888;
        animation: spin 1s linear infinite;
      }
    `;
    return style;
  }

  private updateStyles() {
    const ringSize = this._size + 16;
    const ringOffset = -8;

    // Face container
    this.faceContainer.style.width = `${this._size}px`;
    this.faceContainer.style.height = `${this._size}px`;

    // Shape classes
    this.faceContainer.className = `sigaid-face ${this._shape}`;
    this.ringElement.className = `sigaid-ring ${this._shape}`;

    // Ring
    this.ringElement.style.width = `${ringSize}px`;
    this.ringElement.style.height = `${ringSize}px`;
    this.ringElement.style.top = `${ringOffset}px`;
    this.ringElement.style.left = `${ringOffset}px`;

    // Show/hide ring
    if (!this._showRing) {
      this.ringElement.classList.add('hidden');
    }

    // Badge positioning
    const badgeSize = Math.max(16, this._size / 5);
    this.badgeElement.style.width = `${badgeSize}px`;
    this.badgeElement.style.height = `${badgeSize}px`;
    this.badgeElement.style.fontSize = `${badgeSize * 0.5}px`;
    this.badgeElement.className = `sigaid-badge ${this._badgePosition} ${this._status}`;

    // Show/hide badge
    if (!this._showBadge) {
      this.badgeElement.classList.add('hidden');
    }

    // Name styling
    this.nameElement.style.fontSize = `${Math.max(12, this._size / 8)}px`;
    this.nameElement.style.maxWidth = `${this._size + 40}px`;

    // Compact mode
    if (this._compact) {
      this.container.classList.add('compact');
    } else {
      this.container.classList.remove('compact');
    }

    this.updateStatusDisplay();
  }

  private updateStatusDisplay() {
    const colors = STATUS_COLORS[this._status];
    const isLoading = this._status === 'loading';

    // Update ring
    if (this._showRing) {
      this.ringElement.style.border = `3px solid ${colors.ring}`;
      this.ringElement.style.boxShadow = `0 0 15px ${colors.glow}`;
      this.ringElement.classList.remove('hidden');

      if (isLoading) {
        this.ringElement.classList.add('loading');
        this.ringElement.classList.remove('pulse');
      } else {
        this.ringElement.classList.remove('loading');
        if (this._animated && this._status === 'live') {
          this.ringElement.classList.add('pulse');
        } else {
          this.ringElement.classList.remove('pulse');
        }
      }
    }

    // Update badge
    if (this._showBadge) {
      this.badgeElement.className = `sigaid-badge ${this._badgePosition} ${this._status}`;
    } else {
      this.badgeElement.className = 'sigaid-badge hidden';
    }

    // Update status text (always visible)
    const statusTexts: Record<LivenessStatus, string> = {
      live: 'Verified',
      fresh: 'Verified',
      cached: 'Offline',
      failed: 'Unverified',
      loading: 'Verifying...',
      unavailable: 'Unavailable',
    };
    this.statusElement.textContent = statusTexts[this._status];
    this.statusElement.className = `sigaid-status ${this._status}`;
  }

  private updateDisplay() {
    // Update name
    if (this._showName && this._profile) {
      let displayName = this._profile.name;
      if (this._showFingerprint) {
        displayName += ` (${this._profile.fingerprint})`;
      }
      this.nameElement.textContent = displayName;
      this.nameElement.style.display = 'block';
    } else if (this._showFingerprint && this._profile) {
      this.nameElement.textContent = this._profile.fingerprint;
      this.nameElement.style.display = 'block';
    } else {
      this.nameElement.style.display = 'none';
    }
  }

  private async startVerification() {
    this.stopVerification();
    this._status = 'loading';
    this.updateStatusDisplay();

    // Initial verification
    await this.verify();

    // Set up periodic verification
    this.verificationInterval = window.setInterval(() => {
      this.verify();
    }, VERIFICATION_INTERVAL);
  }

  private stopVerification() {
    if (this.verificationInterval) {
      clearInterval(this.verificationInterval);
      this.verificationInterval = null;
    }
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  private async verify() {
    if (!this._agentId) return;

    this.abortController = new AbortController();

    try {
      // Step 1: Get challenge
      const challengeResponse = await fetch(
        `${this._verifierUrl}/liveness/challenge?agent_id=${encodeURIComponent(this._agentId)}`,
        { signal: this.abortController.signal }
      );

      if (!challengeResponse.ok) {
        throw new Error(`Challenge request failed: ${challengeResponse.status}`);
      }

      const challenge = await challengeResponse.json();

      // Step 2: Request agent to sign challenge
      // This would typically involve:
      // - Sending challenge to agent via WebSocket
      // - Agent signs and returns response
      // - We submit response to verifier
      //
      // For now, we'll call the verify endpoint which handles this
      // In a real implementation, this would use WebSocket or postMessage

      const verifyResponse = await fetch(
        `${this._verifierUrl}/liveness/verify`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: this._agentId,
            challenge_id: challenge.challenge_id,
          }),
          signal: this.abortController.signal,
        }
      );

      if (!verifyResponse.ok) {
        throw new Error(`Verification failed: ${verifyResponse.status}`);
      }

      const result: LivenessResult = await verifyResponse.json();

      this._status = result.status;
      if (result.profile) {
        this._profile = result.profile;
        this.updateFace(result.profile.agent_id);
      }

      this.updateDisplay();
      this.updateStatusDisplay();

      // Trigger callback
      if (this.onVerified) {
        this.onVerified(result);
      }

      // Dispatch event
      this.dispatchEvent(new CustomEvent('verified', { detail: result }));

    } catch (error) {
      if ((error as Error).name === 'AbortError') return;

      console.error('SigAid verification error:', error);
      this._status = 'unavailable';
      this.updateStatusDisplay();

      // Try to show face anyway (from cache or static)
      await this.loadStaticFace();

      if (this.onError) {
        this.onError(error as Error);
      }

      this.dispatchEvent(new CustomEvent('error', { detail: error }));
    }
  }

  private async loadStaticFace() {
    if (!this._agentId) return;

    try {
      const response = await fetch(
        `${this._verifierUrl}/agents/${encodeURIComponent(this._agentId)}/face?animated=${this._animated}`
      );

      if (response.ok) {
        const svg = await response.text();
        this.faceContainer.innerHTML = svg;
      }
    } catch (error) {
      // Show placeholder
      this.faceContainer.innerHTML = this.createPlaceholder();
    }
  }

  private updateFace(agentId: string) {
    // Fetch face SVG from verifier
    fetch(`${this._verifierUrl}/agents/${encodeURIComponent(agentId)}/face?animated=${this._animated}`)
      .then(response => response.text())
      .then(svg => {
        this.faceContainer.innerHTML = svg;
      })
      .catch(() => {
        this.faceContainer.innerHTML = this.createPlaceholder();
      });
  }

  private createPlaceholder(): string {
    const size = this._size;
    return `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="${size}" height="${size}">
        <rect width="200" height="200" fill="#1a1a2e"/>
        <circle cx="100" cy="100" r="60" fill="#333" stroke="#444" stroke-width="2"/>
        <text x="100" y="105" text-anchor="middle" fill="#666" font-size="14">?</text>
      </svg>
    `;
  }

  // Public API
  get agentId(): string {
    return this._agentId;
  }

  set agentId(value: string) {
    this.setAttribute('agent-id', value);
  }

  get status(): LivenessStatus {
    return this._status;
  }

  get profile(): AgentProfile | null {
    return this._profile;
  }

  refresh(): void {
    this.verify();
  }
}

// Register custom element
if (typeof window !== 'undefined' && !customElements.get('sigaid-face')) {
  customElements.define('sigaid-face', SigAidFaceElement);
}

// Export for module usage
export default SigAidFaceElement;
