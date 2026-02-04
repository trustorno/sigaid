#!/usr/bin/env python3
"""Demo: AgentFace - Visual Identity for AI Agents.

This demo shows how each agent gets a unique, recognizable face
derived from their cryptographic identity.

Run:
    python demos/agent_face_demo.py

This will generate:
    - demos/face_gallery.html (view in browser)
    - demos/faces/*.svg (individual face files)
"""

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sigaid.crypto.keys import KeyPair
from sigaid.identity.agent_face import AgentFace, generate_face_gallery


def main():
    print("=" * 60)
    print("AgentFace Demo - Visual Identity for AI Agents")
    print("=" * 60)
    print()

    # Create output directory
    output_dir = Path(__file__).parent / "faces"
    output_dir.mkdir(exist_ok=True)

    # Demo 1: Generate faces for several agents
    print("1. Generating faces for 5 different agents...")
    print("-" * 40)

    for i in range(5):
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()
        face = AgentFace.from_public_key(keypair.public_key_bytes())

        # Save SVG
        svg_path = output_dir / f"agent_{i+1}.svg"
        face.save_svg(svg_path)

        print(f"  Agent {i+1}:")
        print(f"    ID: {agent_id}")
        print(f"    Face fingerprint: {face.fingerprint()}")
        print(f"    Saved: {svg_path}")
        print()

        keypair.clear()

    # Demo 2: Show determinism - same key = same face
    print("2. Demonstrating determinism (same key = same face)...")
    print("-" * 40)

    seed = b"demo_seed_for_determinism_test!!"  # 32 bytes
    kp1 = KeyPair.from_seed(seed)
    kp2 = KeyPair.from_seed(seed)

    face1 = AgentFace.from_public_key(kp1.public_key_bytes())
    face2 = AgentFace.from_public_key(kp2.public_key_bytes())

    print(f"  Key 1 face fingerprint: {face1.fingerprint()}")
    print(f"  Key 2 face fingerprint: {face2.fingerprint()}")
    print(f"  Faces are identical: {face1 == face2}")
    print()

    kp1.clear()
    kp2.clear()

    # Demo 3: Show change sensitivity - 1 bit change = different face
    print("3. Demonstrating change sensitivity (1 bit flip = different face)...")
    print("-" * 40)

    original_key = os.urandom(32)
    modified_key = bytearray(original_key)
    modified_key[0] ^= 0x01  # Flip just 1 bit
    modified_key = bytes(modified_key)

    face_original = AgentFace(original_key)
    face_modified = AgentFace(modified_key)

    print(f"  Original face fingerprint:  {face_original.fingerprint()}")
    print(f"  1-bit-flip face fingerprint: {face_modified.fingerprint()}")
    print(f"  Faces are different: {face_original != face_modified}")

    # Save both for visual comparison
    face_original.save_svg(output_dir / "original.svg")
    face_modified.save_svg(output_dir / "one_bit_flip.svg")
    print(f"  Saved both to {output_dir}/ for visual comparison")
    print()

    # Demo 4: Generate a gallery HTML
    print("4. Generating face gallery (25 random faces)...")
    print("-" * 40)

    gallery_html = generate_face_gallery(count=25, size=150, animated=True)
    gallery_path = Path(__file__).parent / "face_gallery.html"
    gallery_path.write_text(gallery_html)

    print(f"  Gallery saved to: {gallery_path}")
    print(f"  Open in browser to view!")
    print()

    # Demo 5: Show SVG output (for embedding)
    print("5. Example: Embedding face in HTML...")
    print("-" * 40)

    example_face = AgentFace(os.urandom(32))
    print(f"  Data URI (first 100 chars):")
    print(f"  {example_face.to_data_uri()[:100]}...")
    print()
    print("  Usage in HTML:")
    print(f'  <img src="{example_face.to_data_uri()[:50]}..." />')
    print()

    print("=" * 60)
    print("Demo complete!")
    print()
    print("Key insights:")
    print("  - Each agent's face is UNIQUE (2^256 possibilities)")
    print("  - Same key ALWAYS produces the same face")
    print("  - Even 1 bit change produces a visibly different face")
    print("  - Humans can easily recognize and remember faces")
    print()
    print(f"View the gallery: open {gallery_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
