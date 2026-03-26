"""Token metering for agent interactions.

Tracks input/output tokens per agent across all four cost flows:
  RO (requestor output), RI (responder input),
  SO (responder output), SI (requestor input).

Computes real-time costs from provider pricing and generates CMRs.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .schema import (
    AgentInfo,
    AgentPricing,
    ContextState,
    CostFlow,
    CostMeteringRecord,
    InteractionTotals,
    TokenFlow,
)


class Meter:
    """Token meter that tracks agent interaction costs and produces CMRs.

    Usage:
        meter = Meter(agent_id="did:example:my-agent", model="claude-sonnet-4-6",
                      provider="anthropic")
        cmr = meter.record_interaction(
            responder_id="did:example:other-agent",
            responder_model="claude-opus-4-6",
            responder_provider="anthropic",
            request_tokens=10000,
            response_tokens=3000,
        )
    """

    def __init__(
        self,
        agent_id: str,
        model: str = "claude-sonnet-4-6",
        provider: str = "anthropic",
        pricing: Optional[AgentPricing] = None,
    ):
        self.agent_id = agent_id
        self.model = model
        self.provider = provider
        if pricing is not None:
            self.pricing = pricing
        else:
            self.pricing = AgentPricing.from_provider(provider, model)

    def record_interaction(
        self,
        responder_id: str,
        responder_model: str = "claude-sonnet-4-6",
        responder_provider: str = "anthropic",
        responder_pricing: Optional[AgentPricing] = None,
        request_tokens: int = 0,
        request_cached_tokens: int = 0,
        response_tokens: int = 0,
        response_cached_tokens: int = 0,
        context_utilization_pre: float = 0.0,
        context_utilization_post: float = 0.0,
        context_window_size: int = 1_000_000,
        interaction_id: Optional[str] = None,
        coc_chain_ref: Optional[str] = None,
    ) -> CostMeteringRecord:
        """Record a complete agent interaction and generate a CMR.

        Args:
            responder_id: The responder agent's identifier.
            responder_model: The responder's LLM model.
            responder_provider: The responder's LLM provider.
            responder_pricing: Optional explicit pricing; auto-resolved if None.
            request_tokens: Tokens in the request (same for RO and RI).
            request_cached_tokens: Cached tokens in the request (RI only).
            response_tokens: Tokens in the response (same for SO and SI).
            response_cached_tokens: Cached tokens in the response (SI only).
            context_utilization_pre: Responder's context utilization before.
            context_utilization_post: Responder's context utilization after.
            context_window_size: Responder's total context window size.
            interaction_id: Optional UUID; auto-generated if None.
            coc_chain_ref: Optional Chain of Consciousness reference.

        Returns:
            A fully populated CostMeteringRecord with computed costs.
        """
        if responder_pricing is None:
            responder_pricing = AgentPricing.from_provider(
                responder_provider, responder_model
            )

        requestor = AgentInfo(
            agent_id=self.agent_id,
            model=self.model,
            provider=self.provider,
            pricing=self.pricing,
        )
        responder = AgentInfo(
            agent_id=responder_id,
            model=responder_model,
            provider=responder_provider,
            pricing=responder_pricing,
        )

        flows = {
            CostFlow.REQUEST_OUTPUT.value: TokenFlow(
                tokens=request_tokens, cached_tokens=0
            ),
            CostFlow.REQUEST_INPUT.value: TokenFlow(
                tokens=request_tokens, cached_tokens=request_cached_tokens
            ),
            CostFlow.RESPONSE_OUTPUT.value: TokenFlow(
                tokens=response_tokens, cached_tokens=0
            ),
            CostFlow.RESPONSE_INPUT.value: TokenFlow(
                tokens=response_tokens, cached_tokens=response_cached_tokens
            ),
        }

        cmr = CostMeteringRecord(
            interaction_id=interaction_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            requestor=requestor,
            responder=responder,
            flows=flows,
            context_state=ContextState(
                responder_utilization_pre=context_utilization_pre,
                responder_utilization_post=context_utilization_post,
                responder_window_size=context_window_size,
            ),
            coc_chain_ref=coc_chain_ref,
        )
        cmr.compute_costs()
        return cmr

    def record_flows(
        self,
        responder_id: str,
        responder_model: str = "claude-sonnet-4-6",
        responder_provider: str = "anthropic",
        responder_pricing: Optional[AgentPricing] = None,
        ro_tokens: int = 0,
        ri_tokens: int = 0,
        ri_cached: int = 0,
        so_tokens: int = 0,
        si_tokens: int = 0,
        si_cached: int = 0,
        interaction_id: Optional[str] = None,
        coc_chain_ref: Optional[str] = None,
    ) -> CostMeteringRecord:
        """Record an interaction with explicit per-flow token counts.

        Use when RO/RI or SO/SI token counts differ (e.g., protocol overhead).
        """
        if responder_pricing is None:
            responder_pricing = AgentPricing.from_provider(
                responder_provider, responder_model
            )

        requestor = AgentInfo(
            agent_id=self.agent_id,
            model=self.model,
            provider=self.provider,
            pricing=self.pricing,
        )
        responder = AgentInfo(
            agent_id=responder_id,
            model=responder_model,
            provider=responder_provider,
            pricing=responder_pricing,
        )

        flows = {
            CostFlow.REQUEST_OUTPUT.value: TokenFlow(tokens=ro_tokens),
            CostFlow.REQUEST_INPUT.value: TokenFlow(tokens=ri_tokens, cached_tokens=ri_cached),
            CostFlow.RESPONSE_OUTPUT.value: TokenFlow(tokens=so_tokens),
            CostFlow.RESPONSE_INPUT.value: TokenFlow(tokens=si_tokens, cached_tokens=si_cached),
        }

        cmr = CostMeteringRecord(
            interaction_id=interaction_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            requestor=requestor,
            responder=responder,
            flows=flows,
            coc_chain_ref=coc_chain_ref,
        )
        cmr.compute_costs()
        return cmr


def compute_flow_cost(
    tokens: int,
    rate_per_mtok: float,
    cached_tokens: int = 0,
    cache_rate_per_mtok: float = 0.0,
) -> float:
    """Compute cost for a single token flow.

    Args:
        tokens: Total tokens in the flow.
        rate_per_mtok: Rate per million tokens (input or output).
        cached_tokens: Number of tokens served from cache.
        cache_rate_per_mtok: Cache hit rate per million tokens.

    Returns:
        Cost in USD.
    """
    regular = tokens - cached_tokens
    return (regular * rate_per_mtok / 1_000_000
            + cached_tokens * cache_rate_per_mtok / 1_000_000)


def estimate_interaction_cost(
    request_tokens: int,
    response_tokens: int,
    requestor_model: str = "claude-sonnet-4-6",
    requestor_provider: str = "anthropic",
    responder_model: str = "claude-sonnet-4-6",
    responder_provider: str = "anthropic",
) -> Dict[str, float]:
    """Quick cost estimate for an interaction without creating a full CMR.

    Returns:
        Dict with keys: ro, ri, so, si, total, requestor_incurred, responder_incurred.
    """
    rp = AgentPricing.from_provider(requestor_provider, requestor_model)
    sp = AgentPricing.from_provider(responder_provider, responder_model)

    ro = rp.output_cost(request_tokens)
    ri = sp.input_cost(request_tokens)
    so = sp.output_cost(response_tokens)
    si = rp.input_cost(response_tokens)

    return {
        "ro": ro,
        "ri": ri,
        "so": so,
        "si": si,
        "total": ro + ri + so + si,
        "requestor_incurred": ro + si,
        "responder_incurred": ri + so,
    }
