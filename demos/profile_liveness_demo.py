#!/usr/bin/env python3
"""Demo: Agent Profile and Liveness Verification.

This demo shows:
1. Creating an agent with a named profile
2. Liveness verification (challenge-response)
3. Face generation with verification status

Run:
    python demos/profile_liveness_demo.py
"""

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sigaid.identity import KeyPair, AgentProfile, AgentFace
from sigaid.verification import (
    LivenessVerifier,
    LivenessProver,
    LivenessChallenge,
    LivenessStatus,
)


def main():
    print("=" * 60)
    print("Agent Profile & Liveness Verification Demo")
    print("=" * 60)
    print()

    output_dir = Path(__file__).parent / "profiles"
    output_dir.mkdir(exist_ok=True)

    # Demo 1: Create agents with profiles
    print("1. Creating agents with named profiles...")
    print("-" * 40)

    agents = [
        ("Alice", "The helpful assistant"),
        ("Bob", "Security monitor"),
        ("Charlie", "Data analyst"),
    ]

    profiles = []
    for name, description in agents:
        kp = KeyPair.generate()
        profile = AgentProfile.create(
            kp,
            name,
            metadata={"description": description}
        )
        profiles.append((kp, profile))

        print(f"  {profile.short_display}")
        print(f"    Description: {description}")
        print(f"    Verified: {profile.verify()}")
        print(f"    Face: {profile.face.describe().split('|')[0].strip()}")

        # Save face
        profile.face.save_svg(output_dir / f"{name.lower()}.svg")
        print()

    # Demo 2: Liveness verification
    print("2. Simulating liveness verification...")
    print("-" * 40)

    verifier = LivenessVerifier()

    for kp, profile in profiles:
        prover = LivenessProver(kp, profile)

        # Step 1: Verifier creates challenge
        challenge = verifier.create_challenge(agent_id=profile.agent_id)
        print(f"  Challenge for {profile.name}: {challenge.challenge_id[:16]}...")

        # Step 2: Agent signs challenge
        response = prover.respond(challenge)

        # Step 3: Verifier verifies response
        result = verifier.verify(challenge, response)

        print(f"  Status: {result.status.value}")
        print(f"  Verified: {result.is_verified}")
        print()

    # Demo 3: Show verification status aging
    print("3. Verification status states...")
    print("-" * 40)

    status_info = {
        LivenessStatus.LIVE: ("< 30 seconds ago", "Green pulsing ring"),
        LivenessStatus.FRESH: ("< 5 minutes ago", "Green solid ring"),
        LivenessStatus.CACHED: ("Agent offline", "Yellow ring"),
        LivenessStatus.FAILED: ("Verification failed", "Red ring"),
        LivenessStatus.LOADING: ("In progress", "Spinning ring"),
        LivenessStatus.UNAVAILABLE: ("Service down", "Gray ring"),
    }

    for status, (meaning, visual) in status_info.items():
        print(f"  {status.value:12} - {meaning:20} - {visual}")

    print()

    # Demo 4: Generate HTML page with profiles
    print("4. Generating profile gallery...")
    print("-" * 40)

    html_content = generate_profile_gallery(profiles)
    gallery_path = Path(__file__).parent / "profile_gallery.html"
    gallery_path.write_text(html_content)
    print(f"  Gallery saved to: {gallery_path}")

    # Cleanup
    for kp, _ in profiles:
        kp.clear()

    print()
    print("=" * 60)
    print("Demo complete!")
    print()
    print("Key concepts:")
    print("  - Agents have cryptographic IDs + human-readable names")
    print("  - Names are signed by the agent's key (can't be forged)")
    print("  - Liveness verification proves the agent is live")
    print("  - Face + status ring = visual trust indicator")
    print()
    print(f"View the gallery: open {gallery_path}")
    print("=" * 60)


def generate_profile_gallery(profiles: list) -> str:
    """Generate HTML gallery with agent profiles."""

    cards_html = []
    for kp, profile in profiles:
        face_uri = profile.face.to_data_uri(150, animated=True)
        description = profile.metadata.get("description", "")

        cards_html.append(f'''
        <div class="card">
            <div class="status-ring live">
                <img src="{face_uri}" width="150" height="150" />
            </div>
            <div class="name">{profile.name}</div>
            <div class="fingerprint">{profile.fingerprint}</div>
            <div class="description">{description}</div>
            <div class="status">Verified</div>
        </div>
        ''')

    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>SigAid Agent Profiles</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            background: linear-gradient(135deg, #0a0a15 0%, #1a1a2e 50%, #0f0f1a 100%);
            min-height: 100vh;
            margin: 0;
            padding: 30px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #fff;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 40px;
        }}
        .gallery {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            width: 220px;
        }}
        .status-ring {{
            display: inline-block;
            padding: 8px;
            border-radius: 50%;
            margin-bottom: 15px;
        }}
        .status-ring.live {{
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.4);
            border: 3px solid #00ff88;
            animation: pulse 2s ease-in-out infinite;
        }}
        .status-ring.cached {{
            box-shadow: 0 0 15px rgba(255, 170, 0, 0.3);
            border: 3px solid #ffaa00;
        }}
        .status-ring.failed {{
            box-shadow: 0 0 15px rgba(255, 68, 68, 0.3);
            border: 3px solid #ff4444;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 0.8; }}
            50% {{ opacity: 1; }}
        }}
        .status-ring img {{
            display: block;
            border-radius: 50%;
        }}
        .name {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        .fingerprint {{
            font-family: monospace;
            font-size: 12px;
            color: #888;
            margin-bottom: 10px;
        }}
        .description {{
            font-size: 13px;
            color: #aaa;
            margin-bottom: 15px;
        }}
        .status {{
            display: inline-block;
            padding: 4px 12px;
            background: rgba(0, 255, 136, 0.2);
            border: 1px solid #00ff88;
            border-radius: 20px;
            font-size: 11px;
            color: #00ff88;
            text-transform: uppercase;
        }}

        /* Widget embed example */
        .widget-example {{
            margin-top: 50px;
            padding: 30px;
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }}
        .widget-example h2 {{
            margin-top: 0;
        }}
        .code {{
            background: #111;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 13px;
            overflow-x: auto;
        }}
        .code .tag {{ color: #ff79c6; }}
        .code .attr {{ color: #50fa7b; }}
        .code .value {{ color: #f1fa8c; }}
    </style>
</head>
<body>
    <h1>SigAid Agent Profiles</h1>
    <p class="subtitle">Each agent has a unique face + name, verified by cryptographic signature</p>

    <div class="gallery">
        {''.join(cards_html)}
    </div>

    <div class="widget-example">
        <h2>Embed in Your App</h2>
        <p style="color: #888;">Add verified agent faces anywhere with a single line:</p>
        <div class="code">
            <span class="tag">&lt;sigaid-face</span>
            <span class="attr">agent-id</span>=<span class="value">"aid_xxx"</span>
            <span class="tag">&gt;&lt;/sigaid-face&gt;</span><br>
            <span class="tag">&lt;script</span>
            <span class="attr">src</span>=<span class="value">"https://cdn.sigaid.io/widget.js"</span>
            <span class="tag">&gt;&lt;/script&gt;</span>
        </div>
        <p style="color: #666; font-size: 12px; margin-top: 15px;">
            The widget verifies the agent in real-time and shows the appropriate status ring.
        </p>
    </div>
</body>
</html>
'''


if __name__ == "__main__":
    main()
