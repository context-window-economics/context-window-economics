import { randomUUID } from "node:crypto";
import {
  AgentInfo,
  AgentPricing,
  ContextState,
  CostFlow,
  CostMeteringRecord,
  TokenFlow,
} from "./types";

export class Meter {
  readonly agentId: string;
  readonly model: string;
  readonly provider: string;
  readonly pricing: AgentPricing;

  constructor(opts: {
    agentId: string;
    model?: string;
    provider?: string;
    pricing?: AgentPricing;
  }) {
    this.agentId = opts.agentId;
    this.model = opts.model ?? "claude-sonnet-4-6";
    this.provider = opts.provider ?? "anthropic";
    this.pricing =
      opts.pricing ?? AgentPricing.fromProvider(this.provider, this.model);
  }

  recordInteraction(opts: {
    responderId: string;
    responderModel?: string;
    responderProvider?: string;
    responderPricing?: AgentPricing;
    requestTokens?: number;
    requestCachedTokens?: number;
    responseTokens?: number;
    responseCachedTokens?: number;
    contextUtilizationPre?: number;
    contextUtilizationPost?: number;
    contextWindowSize?: number;
    interactionId?: string;
    cocChainRef?: string;
  }): CostMeteringRecord {
    const responderModel = opts.responderModel ?? "claude-sonnet-4-6";
    const responderProvider = opts.responderProvider ?? "anthropic";
    const responderPricing =
      opts.responderPricing ??
      AgentPricing.fromProvider(responderProvider, responderModel);

    const requestTokens = opts.requestTokens ?? 0;
    const responseTokens = opts.responseTokens ?? 0;

    const requestor = new AgentInfo({
      agentId: this.agentId,
      model: this.model,
      provider: this.provider,
      pricing: this.pricing,
    });
    const responder = new AgentInfo({
      agentId: opts.responderId,
      model: responderModel,
      provider: responderProvider,
      pricing: responderPricing,
    });

    const flows: Record<string, TokenFlow> = {
      [CostFlow.REQUEST_OUTPUT]: new TokenFlow(requestTokens, 0),
      [CostFlow.REQUEST_INPUT]: new TokenFlow(
        requestTokens,
        opts.requestCachedTokens ?? 0
      ),
      [CostFlow.RESPONSE_OUTPUT]: new TokenFlow(responseTokens, 0),
      [CostFlow.RESPONSE_INPUT]: new TokenFlow(
        responseTokens,
        opts.responseCachedTokens ?? 0
      ),
    };

    const cmr = new CostMeteringRecord({
      interactionId: opts.interactionId ?? randomUUID(),
      timestamp: new Date().toISOString(),
      requestor,
      responder,
      flows,
      contextState: new ContextState({
        responderUtilizationPre: opts.contextUtilizationPre ?? 0.0,
        responderUtilizationPost: opts.contextUtilizationPost ?? 0.0,
        responderWindowSize: opts.contextWindowSize ?? 1_000_000,
      }),
      cocChainRef: opts.cocChainRef ?? null,
    });
    cmr.computeCosts();
    return cmr;
  }

  recordFlows(opts: {
    responderId: string;
    responderModel?: string;
    responderProvider?: string;
    responderPricing?: AgentPricing;
    roTokens?: number;
    riTokens?: number;
    riCached?: number;
    soTokens?: number;
    siTokens?: number;
    siCached?: number;
    interactionId?: string;
    cocChainRef?: string;
  }): CostMeteringRecord {
    const responderModel = opts.responderModel ?? "claude-sonnet-4-6";
    const responderProvider = opts.responderProvider ?? "anthropic";
    const responderPricing =
      opts.responderPricing ??
      AgentPricing.fromProvider(responderProvider, responderModel);

    const requestor = new AgentInfo({
      agentId: this.agentId,
      model: this.model,
      provider: this.provider,
      pricing: this.pricing,
    });
    const responder = new AgentInfo({
      agentId: opts.responderId,
      model: responderModel,
      provider: responderProvider,
      pricing: responderPricing,
    });

    const flows: Record<string, TokenFlow> = {
      [CostFlow.REQUEST_OUTPUT]: new TokenFlow(opts.roTokens ?? 0),
      [CostFlow.REQUEST_INPUT]: new TokenFlow(
        opts.riTokens ?? 0,
        opts.riCached ?? 0
      ),
      [CostFlow.RESPONSE_OUTPUT]: new TokenFlow(opts.soTokens ?? 0),
      [CostFlow.RESPONSE_INPUT]: new TokenFlow(
        opts.siTokens ?? 0,
        opts.siCached ?? 0
      ),
    };

    const cmr = new CostMeteringRecord({
      interactionId: opts.interactionId ?? randomUUID(),
      timestamp: new Date().toISOString(),
      requestor,
      responder,
      flows,
      cocChainRef: opts.cocChainRef ?? null,
    });
    cmr.computeCosts();
    return cmr;
  }
}

export function computeFlowCost(
  tokens: number,
  ratePerMtok: number,
  cachedTokens: number = 0,
  cacheRatePerMtok: number = 0.0
): number {
  const regular = tokens - cachedTokens;
  return (
    (regular * ratePerMtok) / 1_000_000 +
    (cachedTokens * cacheRatePerMtok) / 1_000_000
  );
}

export interface InteractionCostEstimate {
  ro: number;
  ri: number;
  so: number;
  si: number;
  total: number;
  requestor_incurred: number;
  responder_incurred: number;
}

export function estimateInteractionCost(opts: {
  requestTokens: number;
  responseTokens: number;
  requestorModel?: string;
  requestorProvider?: string;
  responderModel?: string;
  responderProvider?: string;
}): InteractionCostEstimate {
  const rp = AgentPricing.fromProvider(
    opts.requestorProvider ?? "anthropic",
    opts.requestorModel ?? "claude-sonnet-4-6"
  );
  const sp = AgentPricing.fromProvider(
    opts.responderProvider ?? "anthropic",
    opts.responderModel ?? "claude-sonnet-4-6"
  );

  const ro = rp.outputCost(opts.requestTokens);
  const ri = sp.inputCost(opts.requestTokens);
  const so = sp.outputCost(opts.responseTokens);
  const si = rp.inputCost(opts.responseTokens);

  return {
    ro,
    ri,
    so,
    si,
    total: ro + ri + so + si,
    requestor_incurred: ro + si,
    responder_incurred: ri + so,
  };
}
