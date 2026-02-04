"""SigAid Authority API routers."""

import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import blake3
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SigAidAgent, SigAidLease, SigAidStateEntry, SigAidReputation, SigAidAPIKey, AgentStatus, ActionType
from ..schemas import (
    AgentCreate, AgentResponse,
    LeaseAcquireRequest, LeaseResponse, LeaseRenewRequest, LeaseReleaseRequest, LeaseStatusResponse, LeaseError,
    StateEntryCreate, StateEntryResponse, StateHeadResponse, StateHistoryResponse,
    VerifyRequest, VerifyResponse,
    APIKeyCreate, APIKeyResponse,
)
from ..services.tokens import get_token_service, TokenExpiredError, TokenInvalidError
from ..services.crypto import CryptoService

router = APIRouter()


# === Helper Functions ===

def verify_api_key(x_api_key: Optional[str] = Header(None), db: Session = Depends(get_db)) -> SigAidAPIKey:
    """Verify API key for protected endpoints."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    key_hash = blake3.blake3(x_api_key.encode()).digest()
    api_key = db.query(SigAidAPIKey).filter(
        SigAidAPIKey.key_hash == key_hash,
        SigAidAPIKey.is_active == True
    ).first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="API key expired")

    # Update last used
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return api_key


def get_agent_with_reputation(db: Session, agent: SigAidAgent) -> AgentResponse:
    """Build agent response with reputation data."""
    reputation = agent.reputation

    return AgentResponse(
        agent_id=agent.agent_id,
        public_key=base64.b64encode(agent.public_key).decode(),
        status=agent.status.value,
        created_at=agent.created_at,
        revoked_at=agent.revoked_at,
        metadata=agent.agent_metadata or {},
        total_transactions=reputation.total_transactions if reputation else 0,
        successful_transactions=reputation.successful_transactions if reputation else 0,
        age_days=reputation.age_days if reputation else 0,
        reputation_score=reputation.score if reputation else 0.0,
    )


# === Agent Endpoints ===

@router.post("/agents", response_model=AgentResponse, status_code=201)
def create_agent(request: AgentCreate, db: Session = Depends(get_db)):
    """Register a new agent."""
    # Check if agent already exists
    existing = db.query(SigAidAgent).filter(SigAidAgent.agent_id == request.agent_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Agent already exists")

    # Decode and validate public key
    try:
        public_key = base64.b64decode(request.public_key)
        if len(public_key) != 32:
            raise ValueError("Invalid key length")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid public key format")

    # Create agent
    agent = SigAidAgent(
        agent_id=request.agent_id,
        public_key=public_key,
        status=AgentStatus.ACTIVE,
        agent_metadata=request.metadata,
    )
    db.add(agent)

    # Create initial reputation
    reputation = SigAidReputation(agent_id=request.agent_id)
    db.add(reputation)

    db.commit()
    db.refresh(agent)

    return get_agent_with_reputation(db, agent)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent information."""
    agent = db.query(SigAidAgent).filter(SigAidAgent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return get_agent_with_reputation(db, agent)


@router.delete("/agents/{agent_id}", status_code=204)
def revoke_agent(agent_id: str, db: Session = Depends(get_db)):
    """Revoke an agent."""
    agent = db.query(SigAidAgent).filter(SigAidAgent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = AgentStatus.REVOKED
    agent.revoked_at = datetime.now(timezone.utc)

    # Also release any active lease
    db.query(SigAidLease).filter(SigAidLease.agent_id == agent_id).delete()

    db.commit()


# === Lease Endpoints ===

@router.post("/leases", response_model=LeaseResponse, responses={409: {"model": LeaseError}})
def acquire_lease(request: LeaseAcquireRequest, db: Session = Depends(get_db)):
    """Acquire exclusive lease for an agent."""
    # Verify agent exists and is active
    agent = db.query(SigAidAgent).filter(SigAidAgent.agent_id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.status != AgentStatus.ACTIVE:
        raise HTTPException(status_code=403, detail=f"Agent is {agent.status.value}")

    # Verify signature against agent's public key
    if not CryptoService.verify_lease_request(
        public_key=agent.public_key,
        agent_id=request.agent_id,
        session_id=request.session_id,
        timestamp=request.timestamp,
        nonce=request.nonce,
        signature_hex=request.signature,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Try to acquire advisory lock atomically
    lock_acquired = db.execute(
        text("SELECT pg_try_advisory_lock(hashtext(:agent_id))"),
        {"agent_id": request.agent_id}
    ).scalar()

    if not lock_acquired:
        # Lock not acquired - check who holds it
        existing_lease = db.query(SigAidLease).filter(SigAidLease.agent_id == request.agent_id).first()
        if existing_lease and existing_lease.expires_at > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=409,
                detail=LeaseError(
                    error="lease_held",
                    message="Lease held by another session",
                    holder_session_id=existing_lease.session_id
                ).model_dump()
            )

    try:
        # Clean up any expired lease
        db.query(SigAidLease).filter(
            SigAidLease.agent_id == request.agent_id,
            SigAidLease.expires_at < datetime.now(timezone.utc)
        ).delete()

        # Check for active lease
        existing = db.query(SigAidLease).filter(SigAidLease.agent_id == request.agent_id).first()
        if existing:
            if existing.expires_at > datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=409,
                    detail=LeaseError(
                        error="lease_held",
                        message="Lease held by another session",
                        holder_session_id=existing.session_id
                    ).model_dump()
                )
            else:
                # Expired lease - remove it
                db.delete(existing)

        # Generate PASETO token
        token_service = get_token_service()
        lease_token, token_jti, expires_at = token_service.create_lease_token(
            agent_id=request.agent_id,
            session_id=request.session_id,
            ttl_seconds=request.ttl_seconds,
            sequence=0,
        )

        # Create lease record
        now = datetime.now(timezone.utc)
        lease = SigAidLease(
            agent_id=request.agent_id,
            session_id=request.session_id,
            token_jti=token_jti,
            sequence=0,
            acquired_at=now,
            expires_at=expires_at,
        )
        db.add(lease)
        db.commit()
        db.refresh(lease)

        return LeaseResponse(
            agent_id=lease.agent_id,
            session_id=lease.session_id,
            lease_token=lease_token,
            acquired_at=lease.acquired_at,
            expires_at=lease.expires_at,
            sequence=lease.sequence,
        )
    except HTTPException:
        # Release lock on known errors, then re-raise
        if lock_acquired:
            db.execute(
                text("SELECT pg_advisory_unlock(hashtext(:agent_id))"),
                {"agent_id": request.agent_id}
            )
        raise
    except Exception:
        # Release lock on unexpected errors
        if lock_acquired:
            db.execute(
                text("SELECT pg_advisory_unlock(hashtext(:agent_id))"),
                {"agent_id": request.agent_id}
            )
        raise


@router.put("/leases/{agent_id}", response_model=LeaseResponse)
def renew_lease(agent_id: str, request: LeaseRenewRequest, db: Session = Depends(get_db)):
    """Renew an existing lease."""
    lease = db.query(SigAidLease).filter(SigAidLease.agent_id == agent_id).first()
    if not lease:
        raise HTTPException(status_code=404, detail="No active lease")

    if lease.session_id != request.session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")

    if lease.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Lease expired")

    # Verify current token
    token_service = get_token_service()
    try:
        payload = token_service.verify_lease_token(request.current_token)
        if payload["agent_id"] != agent_id:
            raise HTTPException(status_code=403, detail="Token agent mismatch")
        if payload["session_id"] != request.session_id:
            raise HTTPException(status_code=403, detail="Token session mismatch")
    except TokenExpiredError:
        raise HTTPException(status_code=410, detail="Token expired")
    except TokenInvalidError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Generate new token with refreshed expiration
    new_sequence = lease.sequence + 1
    new_token, new_jti, new_expires = token_service.create_lease_token(
        agent_id=agent_id,
        session_id=request.session_id,
        ttl_seconds=request.ttl_seconds,
        sequence=new_sequence,
    )

    # Update lease
    lease.token_jti = new_jti
    lease.sequence = new_sequence
    lease.expires_at = new_expires
    lease.last_renewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(lease)

    return LeaseResponse(
        agent_id=lease.agent_id,
        session_id=lease.session_id,
        lease_token=new_token,
        acquired_at=lease.acquired_at,
        expires_at=lease.expires_at,
        sequence=lease.sequence,
    )


@router.delete("/leases/{agent_id}", status_code=204)
def release_lease(agent_id: str, request: LeaseReleaseRequest, db: Session = Depends(get_db)):
    """Release a lease."""
    lease = db.query(SigAidLease).filter(SigAidLease.agent_id == agent_id).first()
    if not lease:
        raise HTTPException(status_code=404, detail="No active lease")

    if lease.session_id != request.session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")

    # Verify token
    token_service = get_token_service()
    try:
        payload = token_service.verify_lease_token(request.token)
        if payload["agent_id"] != agent_id:
            raise HTTPException(status_code=403, detail="Token agent mismatch")
    except (TokenExpiredError, TokenInvalidError):
        # Allow release even with expired/invalid token if session matches
        pass

    # Release advisory lock
    db.execute(
        text("SELECT pg_advisory_unlock(hashtext(:agent_id))"),
        {"agent_id": agent_id}
    )

    db.delete(lease)
    db.commit()


@router.get("/leases/{agent_id}", response_model=LeaseStatusResponse)
def get_lease_status(agent_id: str, db: Session = Depends(get_db)):
    """Check lease status for an agent."""
    lease = db.query(SigAidLease).filter(SigAidLease.agent_id == agent_id).first()

    if not lease or lease.expires_at < datetime.now(timezone.utc):
        return LeaseStatusResponse(
            agent_id=agent_id,
            active=False,
        )

    return LeaseStatusResponse(
        agent_id=agent_id,
        active=True,
        session_id=lease.session_id,
        expires_at=lease.expires_at,
    )


# === State Chain Endpoints ===

@router.post("/state/{agent_id}", response_model=StateEntryResponse, status_code=201)
def append_state_entry(agent_id: str, request: StateEntryCreate, db: Session = Depends(get_db)):
    """Append a new entry to the agent's state chain."""
    # Verify agent exists
    agent = db.query(SigAidAgent).filter(SigAidAgent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if request.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Agent ID mismatch")

    # Verify lease is held
    lease = db.query(SigAidLease).filter(
        SigAidLease.agent_id == agent_id,
        SigAidLease.expires_at > datetime.now(timezone.utc)
    ).first()
    if not lease:
        raise HTTPException(status_code=403, detail="No active lease")

    # Get current head
    current_head = db.query(SigAidStateEntry).filter(
        SigAidStateEntry.agent_id == agent_id
    ).order_by(SigAidStateEntry.sequence.desc()).first()

    expected_sequence = (current_head.sequence + 1) if current_head else 0
    if request.sequence != expected_sequence:
        raise HTTPException(
            status_code=409,
            detail=f"Sequence mismatch: expected {expected_sequence}, got {request.sequence}"
        )

    # Verify prev_hash
    if current_head:
        expected_prev_hash = base64.b64encode(current_head.entry_hash).decode()
        if request.prev_hash != expected_prev_hash:
            raise HTTPException(status_code=409, detail="Previous hash mismatch - possible fork")
    else:
        # Genesis entry should have zero prev_hash
        zero_hash = base64.b64encode(bytes(32)).decode()
        if request.prev_hash != zero_hash:
            raise HTTPException(status_code=400, detail="Genesis entry must have zero prev_hash")

    # Decode binary fields
    prev_hash = base64.b64decode(request.prev_hash)
    entry_hash = base64.b64decode(request.entry_hash)
    signature = base64.b64decode(request.signature)
    action_data_hash = base64.b64decode(request.action_data_hash) if request.action_data_hash else None

    # Verify signature and entry hash
    if not CryptoService.verify_state_entry(
        public_key=agent.public_key,
        agent_id=agent_id,
        sequence=request.sequence,
        prev_hash=prev_hash,
        timestamp=request.timestamp,
        action_type=request.action_type,
        action_summary=request.action_summary,
        action_data_hash=action_data_hash,
        signature=signature,
        entry_hash=entry_hash,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature or entry hash")

    # Create entry
    try:
        action_type = ActionType(request.action_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action type: {request.action_type}")

    entry = SigAidStateEntry(
        agent_id=agent_id,
        sequence=request.sequence,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        action_type=action_type,
        action_summary=request.action_summary,
        action_data_hash=action_data_hash,
        signature=signature,
    )
    db.add(entry)

    # Update reputation
    if agent.reputation:
        agent.reputation.total_transactions += 1
        if action_type == ActionType.TRANSACTION:
            agent.reputation.successful_transactions += 1
        agent.reputation.last_activity_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(entry)

    return StateEntryResponse(
        agent_id=entry.agent_id,
        sequence=entry.sequence,
        prev_hash=base64.b64encode(entry.prev_hash).decode(),
        entry_hash=base64.b64encode(entry.entry_hash).decode(),
        action_type=entry.action_type.value,
        action_summary=entry.action_summary,
        action_data_hash=base64.b64encode(entry.action_data_hash).decode() if entry.action_data_hash else None,
        signature=base64.b64encode(entry.signature).decode(),
        created_at=entry.created_at,
    )


@router.get("/state/{agent_id}", response_model=StateHeadResponse)
def get_state_head(agent_id: str, db: Session = Depends(get_db)):
    """Get the current state chain head for an agent."""
    entry = db.query(SigAidStateEntry).filter(
        SigAidStateEntry.agent_id == agent_id
    ).order_by(SigAidStateEntry.sequence.desc()).first()

    if not entry:
        raise HTTPException(status_code=404, detail="No state entries")

    return StateHeadResponse(
        agent_id=entry.agent_id,
        sequence=entry.sequence,
        entry_hash=base64.b64encode(entry.entry_hash).decode(),
        created_at=entry.created_at,
    )


@router.get("/state/{agent_id}/history", response_model=StateHistoryResponse)
def get_state_history(
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get state chain history for an agent."""
    query = db.query(SigAidStateEntry).filter(
        SigAidStateEntry.agent_id == agent_id
    ).order_by(SigAidStateEntry.sequence.desc())

    total = query.count()
    entries = query.offset(offset).limit(limit).all()

    return StateHistoryResponse(
        agent_id=agent_id,
        entries=[
            StateEntryResponse(
                agent_id=e.agent_id,
                sequence=e.sequence,
                prev_hash=base64.b64encode(e.prev_hash).decode(),
                entry_hash=base64.b64encode(e.entry_hash).decode(),
                action_type=e.action_type.value,
                action_summary=e.action_summary,
                action_data_hash=base64.b64encode(e.action_data_hash).decode() if e.action_data_hash else None,
                signature=base64.b64encode(e.signature).decode(),
                created_at=e.created_at,
            )
            for e in entries
        ],
        total_count=total,
    )


# === Verification Endpoint ===

@router.post("/verify", response_model=VerifyResponse)
def verify_proof(
    request: VerifyRequest,
    db: Session = Depends(get_db),
    api_key: SigAidAPIKey = Depends(verify_api_key)
):
    """Verify an agent's proof bundle."""
    proof = request.proof

    agent_id = proof.get("agent_id")
    if not agent_id:
        return VerifyResponse(valid=False, agent_id="", error_message="Missing agent_id")

    # Get agent
    agent = db.query(SigAidAgent).filter(SigAidAgent.agent_id == agent_id).first()
    if not agent:
        return VerifyResponse(valid=False, agent_id=agent_id, error_message="Agent not found")

    if agent.status != AgentStatus.ACTIVE:
        return VerifyResponse(
            valid=False,
            agent_id=agent_id,
            error_message=f"Agent is {agent.status.value}"
        )

    # Check lease if required
    lease_active = False
    if request.require_lease:
        lease = db.query(SigAidLease).filter(
            SigAidLease.agent_id == agent_id,
            SigAidLease.expires_at > datetime.now(timezone.utc)
        ).first()
        lease_active = lease is not None

        if not lease_active:
            return VerifyResponse(
                valid=False,
                agent_id=agent_id,
                lease_active=False,
                error_message="No active lease"
            )

    # Verify challenge response signature if provided
    challenge_response = proof.get("challenge_response")
    challenge = proof.get("challenge")
    if challenge_response and challenge:
        try:
            sig = bytes.fromhex(challenge_response)
            msg = challenge.encode("utf-8") if isinstance(challenge, str) else bytes.fromhex(challenge)
            if not CryptoService.verify_signature(
                agent.public_key, msg, sig, domain="sigaid.verify.v1"
            ):
                return VerifyResponse(
                    valid=False,
                    agent_id=agent_id,
                    lease_active=lease_active,
                    error_message="Invalid challenge response signature"
                )
        except (ValueError, TypeError) as e:
            return VerifyResponse(
                valid=False,
                agent_id=agent_id,
                lease_active=lease_active,
                error_message=f"Invalid challenge/response format: {e}"
            )

    # Check reputation if required
    if request.min_reputation_score is not None:
        if agent.reputation and agent.reputation.score < request.min_reputation_score:
            return VerifyResponse(
                valid=False,
                agent_id=agent_id,
                lease_active=lease_active,
                error_message=f"Reputation score {agent.reputation.score} below minimum {request.min_reputation_score}"
            )

    return VerifyResponse(
        valid=True,
        agent_id=agent_id,
        lease_active=lease_active,
        state_verified=True,
        agent_info=get_agent_with_reputation(db, agent),
    )


# === API Key Management ===

@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
def create_api_key(request: APIKeyCreate, db: Session = Depends(get_db)):
    """Create a new API key."""
    # Generate random key
    raw_key = secrets.token_urlsafe(32)
    key_hash = blake3.blake3(raw_key.encode()).digest()

    api_key = SigAidAPIKey(
        key_hash=key_hash,
        name=request.name,
        rate_limit_per_minute=request.rate_limit_per_minute,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyResponse(
        api_key=raw_key,  # Only returned once!
        name=api_key.name,
        created_at=api_key.created_at,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
    )
