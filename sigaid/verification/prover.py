"""Proof generation for agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sigaid.models.proof import ProofBundle

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair
    from sigaid.models.state import StateEntry
    from sigaid.models.lease import Lease


class Prover:
    """Generates proof bundles for agent verification.

    The Prover creates cryptographic proofs that an agent can present
    to third parties to verify their identity and capabilities.

    Example:
        prover = Prover(keypair)

        # Create proof for a challenge
        proof = prover.create_proof(
            challenge=b"random_challenge",
            lease=current_lease,
            state_head=current_state,
        )

        # Send proof to verifier
        response = await service.verify(proof)
    """

    def __init__(self, keypair: KeyPair):
        """Initialize prover.

        Args:
            keypair: Agent's keypair for signing proofs
        """
        self._keypair = keypair

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return str(self._keypair.to_agent_id())

    def create_proof(
        self,
        challenge: bytes,
        lease: Lease | None = None,
        state_head: StateEntry | None = None,
        user_attestation: bytes | None = None,
        third_party_attestations: list[bytes] | None = None,
    ) -> ProofBundle:
        """Create a proof bundle.

        Args:
            challenge: Challenge bytes from the verifier
            lease: Current lease (optional)
            state_head: Current state chain head (optional)
            user_attestation: Optional user authorization
            third_party_attestations: Optional third-party attestations

        Returns:
            Signed ProofBundle
        """
        return ProofBundle.create(
            agent_id=self.agent_id,
            lease_token=lease.token if lease else "",
            state_head=state_head,
            challenge=challenge,
            keypair=self._keypair,
            user_attestation=user_attestation,
            third_party_attestations=third_party_attestations,
        )

    def sign_challenge(self, challenge: bytes) -> bytes:
        """Sign a challenge directly.

        Args:
            challenge: Challenge bytes

        Returns:
            Signature over challenge
        """
        from sigaid.constants import DOMAIN_VERIFY

        return self._keypair.sign(challenge, domain=DOMAIN_VERIFY)

    def create_attestation(self, data: bytes) -> bytes:
        """Create an attestation signature.

        Args:
            data: Data to attest

        Returns:
            Attestation signature
        """
        from sigaid.constants import DOMAIN_VERIFY

        return self._keypair.sign(data, domain=DOMAIN_VERIFY)
