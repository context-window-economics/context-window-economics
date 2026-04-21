import { describe, it, beforeEach, afterEach } from "node:test";
import * as assert from "node:assert/strict";
import { rmSync, existsSync } from "node:fs";

import {
  PROTOCOL_VERSION,
  SCHEMA_VERSION,
  CostFlow,
  AllocationMethod,
  SettlementTier,
  QoSTier,
  CongestionLevel,
  ReputationTier,
  DepositStatus,
  BackPressureStatus,
  AgentPricing,
  AgentInfo,
  TokenFlow,
  InteractionTotals,
  ContextState,
  SettlementProposal,
  CostMeteringRecord,
  DepositRecord,
  QoSConfig,
  BackPressureSignal,
  ContextReservation,
} from "../src/types";

import { Meter, computeFlowCost, estimateInteractionCost } from "../src/metering";

import {
  allocate,
  allocateRequestorPays,
  allocateResponderPays,
  allocateEqualSplit,
  allocateProportional,
  allocateShapley,
  allocateNash,
} from "../src/allocation";

import {
  PaymentRail,
  SettlementReceipt,
  SettlementEngine,
  SettlementBatch,
  cmrHash,
  verifyCmrPair,
} from "../src/settlement";

import {
  classifyReputation,
  depositMultiplierForTier,
  calculateDeposit,
  maxRequestTokens,
  checkAccess,
  createDeposit,
  resolveDeposit,
} from "../src/spam";

import {
  congestionMultiplier,
  congestionLevel,
  effectiveTokenPrice,
  positionMultiplier,
  qosConfigForTier,
  checkQosLimits,
  generateBackPressure,
} from "../src/congestion";

import {
  cacheAmortizedCost,
  compressionRoi,
  memoryVsContextCrossover,
  CacheTracker,
} from "../src/caching";

import { CWEPStore } from "../src/store";

// Helper: create a CMR with known values
function makeCmr(): CostMeteringRecord {
  const meter = new Meter({
    agentId: "did:web:requestor",
    model: "claude-sonnet-4-6",
    provider: "anthropic",
  });
  return meter.recordInteraction({
    responderId: "did:web:responder",
    responderModel: "claude-sonnet-4-6",
    responderProvider: "anthropic",
    requestTokens: 10000,
    responseTokens: 3000,
  });
}

// ========================================================================
// types.ts
// ========================================================================

describe("types.ts — constants", () => {
  it("PROTOCOL_VERSION is 1.0.0", () => {
    assert.equal(PROTOCOL_VERSION, "1.0.0");
  });

  it("SCHEMA_VERSION is 1.0.0", () => {
    assert.equal(SCHEMA_VERSION, "1.0.0");
  });

  it("CostFlow has 4 values", () => {
    const values = Object.values(CostFlow);
    assert.equal(values.length, 4);
  });

  it("AllocationMethod has 7 values", () => {
    assert.equal(Object.values(AllocationMethod).length, 7);
  });

  it("QoSTier has 4 values", () => {
    assert.equal(Object.values(QoSTier).length, 4);
  });
});

describe("types.ts — AgentPricing", () => {
  it("fromProvider creates valid pricing", () => {
    const p = AgentPricing.fromProvider("anthropic", "claude-sonnet-4-6");
    assert.equal(p.inputRatePerMtok, 3.0);
    assert.equal(p.outputRatePerMtok, 15.0);
    assert.equal(p.cacheHitRatePerMtok, 0.3);
  });

  it("fromProvider throws on unknown", () => {
    assert.throws(() => AgentPricing.fromProvider("anthropic", "nonexistent"));
    assert.throws(() => AgentPricing.fromProvider("nonexistent", "anything"));
  });

  it("inputCost computes correctly", () => {
    const p = AgentPricing.fromProvider("anthropic", "claude-sonnet-4-6");
    const cost = p.inputCost(1_000_000);
    assert.ok(Math.abs(cost - 3.0) < 0.001);
  });

  it("inputCost with cached tokens", () => {
    const p = AgentPricing.fromProvider("anthropic", "claude-sonnet-4-6");
    const cost = p.inputCost(1_000_000, 500_000);
    const expected = (500_000 * 3.0) / 1_000_000 + (500_000 * 0.3) / 1_000_000;
    assert.ok(Math.abs(cost - expected) < 0.001);
  });

  it("outputCost computes correctly", () => {
    const p = AgentPricing.fromProvider("anthropic", "claude-sonnet-4-6");
    const cost = p.outputCost(1_000_000);
    assert.ok(Math.abs(cost - 15.0) < 0.001);
  });

  it("round-trips through toDict/fromDict", () => {
    const p = AgentPricing.fromProvider("anthropic", "claude-opus-4-6");
    const d = p.toDict();
    const p2 = AgentPricing.fromDict(d);
    assert.equal(p.inputRatePerMtok, p2.inputRatePerMtok);
    assert.equal(p.outputRatePerMtok, p2.outputRatePerMtok);
    assert.equal(p.cacheHitRatePerMtok, p2.cacheHitRatePerMtok);
  });
});

describe("types.ts — CostMeteringRecord", () => {
  it("creates with defaults", () => {
    const cmr = new CostMeteringRecord();
    assert.equal(cmr.cwepVersion, PROTOCOL_VERSION);
    assert.ok(cmr.interactionId.length > 0);
    assert.equal(Object.keys(cmr.flows).length, 4);
  });

  it("computeCosts produces correct totals", () => {
    const cmr = makeCmr();
    assert.ok(cmr.totals.totalCostUsd > 0);
    assert.ok(cmr.totals.totalTokens === 26000);
    const sum =
      cmr.totals.requestorIncurredUsd + cmr.totals.responderIncurredUsd;
    assert.ok(Math.abs(sum - cmr.totals.totalCostUsd) < 0.0001);
  });

  it("round-trips through toDict/fromDict", () => {
    const cmr = makeCmr();
    const d = cmr.toDict();
    const cmr2 = CostMeteringRecord.fromDict(d);
    assert.equal(cmr.interactionId, cmr2.interactionId);
    assert.equal(cmr.totals.totalTokens, cmr2.totals.totalTokens);
    assert.ok(
      Math.abs(cmr.totals.totalCostUsd - cmr2.totals.totalCostUsd) < 0.0001
    );
  });

  it("round-trips through JSON", () => {
    const cmr = makeCmr();
    const json = cmr.toJson();
    const cmr2 = CostMeteringRecord.fromJson(json);
    assert.equal(cmr.interactionId, cmr2.interactionId);
  });
});

describe("types.ts — DepositRecord", () => {
  it("creates with defaults", () => {
    const dr = new DepositRecord();
    assert.ok(dr.depositId.length > 0);
    assert.equal(dr.status, DepositStatus.COMMITTED);
    assert.equal(dr.reputationTier, ReputationTier.UNKNOWN);
  });

  it("round-trips through toDict/fromDict", () => {
    const dr = new DepositRecord({
      requestorId: "agent-a",
      responderId: "agent-b",
      amountUsd: 0.05,
    });
    const d = dr.toDict();
    const dr2 = DepositRecord.fromDict(d);
    assert.equal(dr.requestorId, dr2.requestorId);
    assert.equal(dr.amountUsd, dr2.amountUsd);
  });
});

describe("types.ts — other data structures", () => {
  it("QoSConfig round-trips", () => {
    const q = new QoSConfig({ tier: QoSTier.PRIORITY });
    const d = q.toDict();
    const q2 = QoSConfig.fromDict(d);
    assert.equal(q2.tier, QoSTier.PRIORITY);
  });

  it("BackPressureSignal round-trips", () => {
    const bp = new BackPressureSignal({ cwepStatus: BackPressureStatus.CONGESTED });
    const d = bp.toDict();
    const bp2 = BackPressureSignal.fromDict(d);
    assert.equal(bp2.cwepStatus, BackPressureStatus.CONGESTED);
  });

  it("ContextReservation round-trips", () => {
    const cr = new ContextReservation({ capacityTokens: 50_000 });
    const d = cr.toDict();
    const cr2 = ContextReservation.fromDict(d);
    assert.equal(cr2.capacityTokens, 50_000);
  });
});

// ========================================================================
// metering.ts
// ========================================================================

describe("metering.ts — Meter", () => {
  it("recordInteraction produces valid CMR", () => {
    const cmr = makeCmr();
    assert.ok(cmr.requestor !== null);
    assert.ok(cmr.responder !== null);
    assert.equal(cmr.requestor!.agentId, "did:web:requestor");
    assert.equal(cmr.responder!.agentId, "did:web:responder");
    assert.ok(cmr.totals.totalCostUsd > 0);
  });

  it("recordFlows with explicit per-flow tokens", () => {
    const meter = new Meter({ agentId: "agent-a" });
    const cmr = meter.recordFlows({
      responderId: "agent-b",
      roTokens: 10000,
      riTokens: 10500,
      soTokens: 3000,
      siTokens: 3000,
    });
    assert.equal(cmr.flows[CostFlow.REQUEST_OUTPUT].tokens, 10000);
    assert.equal(cmr.flows[CostFlow.REQUEST_INPUT].tokens, 10500);
    assert.ok(cmr.totals.totalCostUsd > 0);
  });

  it("recordInteraction with caching", () => {
    const meter = new Meter({ agentId: "agent-a" });
    const cmrNocache = meter.recordInteraction({
      responderId: "agent-b",
      requestTokens: 10000,
      responseTokens: 3000,
    });
    const cmrCached = meter.recordInteraction({
      responderId: "agent-b",
      requestTokens: 10000,
      responseTokens: 3000,
      requestCachedTokens: 8000,
    });
    assert.ok(cmrCached.totals.totalCostUsd < cmrNocache.totals.totalCostUsd);
  });
});

describe("metering.ts — computeFlowCost", () => {
  it("computes basic cost", () => {
    const cost = computeFlowCost(1_000_000, 3.0);
    assert.ok(Math.abs(cost - 3.0) < 0.001);
  });

  it("computes with cache", () => {
    const cost = computeFlowCost(1_000_000, 3.0, 500_000, 0.3);
    const expected = (500_000 * 3.0) / 1_000_000 + (500_000 * 0.3) / 1_000_000;
    assert.ok(Math.abs(cost - expected) < 0.001);
  });
});

describe("metering.ts — estimateInteractionCost", () => {
  it("returns all cost components", () => {
    const est = estimateInteractionCost({
      requestTokens: 10000,
      responseTokens: 3000,
    });
    assert.ok("ro" in est);
    assert.ok("ri" in est);
    assert.ok("so" in est);
    assert.ok("si" in est);
    assert.ok("total" in est);
    assert.ok("requestor_incurred" in est);
    assert.ok("responder_incurred" in est);
    assert.ok(
      Math.abs(est.total - (est.requestor_incurred + est.responder_incurred)) <
        0.0001
    );
  });

  it("opus costs more than sonnet", () => {
    const sonnet = estimateInteractionCost({
      requestTokens: 10000,
      responseTokens: 3000,
    });
    const opus = estimateInteractionCost({
      requestTokens: 10000,
      responseTokens: 3000,
      requestorModel: "claude-opus-4-6",
      responderModel: "claude-opus-4-6",
    });
    assert.ok(opus.total > sonnet.total);
  });
});

// ========================================================================
// allocation.ts
// ========================================================================

describe("allocation.ts — rule-based", () => {
  it("requestor_pays assigns 100% to requestor", () => {
    const cmr = makeCmr();
    const p = allocateRequestorPays(cmr);
    assert.equal(p.method, AllocationMethod.REQUESTOR_PAYS);
    assert.ok(Math.abs(p.requestorPaysUsd - cmr.totals.totalCostUsd) < 0.0001);
    assert.equal(p.responderPaysUsd, 0.0);
    assert.equal(p.transferDirection, "requestor_to_responder");
  });

  it("responder_pays assigns 100% to responder", () => {
    const cmr = makeCmr();
    const p = allocateResponderPays(cmr);
    assert.equal(p.method, AllocationMethod.RESPONDER_PAYS);
    assert.equal(p.requestorPaysUsd, 0.0);
    assert.ok(Math.abs(p.responderPaysUsd - cmr.totals.totalCostUsd) < 0.0001);
    assert.equal(p.transferDirection, "responder_to_requestor");
  });

  it("equal_split gives each agent 50%", () => {
    const cmr = makeCmr();
    const p = allocateEqualSplit(cmr);
    const half = cmr.totals.totalCostUsd / 2.0;
    assert.ok(Math.abs(p.requestorPaysUsd - half) < 0.0001);
    assert.ok(Math.abs(p.responderPaysUsd - half) < 0.0001);
  });

  it("proportional splits by token share", () => {
    const cmr = makeCmr();
    const p = allocateProportional(cmr);
    assert.equal(p.method, AllocationMethod.PROPORTIONAL);
    assert.ok(
      Math.abs(
        p.requestorPaysUsd + p.responderPaysUsd - cmr.totals.totalCostUsd
      ) < 0.0001
    );
  });

  it("proportional handles zero tokens", () => {
    const cmr = new CostMeteringRecord();
    const p = allocateProportional(cmr);
    assert.equal(p.requestorPaysUsd, 0.0);
    assert.equal(p.responderPaysUsd, 0.0);
  });
});

describe("allocation.ts — Shapley", () => {
  it("Shapley with no standalone cost", () => {
    const cmr = makeCmr();
    const p = allocateShapley(cmr);
    assert.equal(p.method, AllocationMethod.SHAPLEY);
    assert.ok(p.requestorPaysUsd > 0);
    assert.ok(p.responderPaysUsd > 0);
    assert.ok(p.requestorPaysUsd > p.responderPaysUsd);
  });

  it("Shapley with standalone cost B", () => {
    const cmr = makeCmr();
    const p1 = allocateShapley(cmr, 0.0);
    const p2 = allocateShapley(cmr, 0.01);
    assert.ok(p2.responderPaysUsd > p1.responderPaysUsd);
  });
});

describe("allocation.ts — Nash", () => {
  it("Nash with positive surplus", () => {
    const cmr = makeCmr();
    const p = allocateNash(cmr, 1.0, 0.5, 0.5);
    assert.equal(p.method, AllocationMethod.NASH_BARGAINING);
    assert.ok(
      Math.abs(
        p.requestorPaysUsd + p.responderPaysUsd - cmr.totals.totalCostUsd
      ) < 0.0001
    );
  });

  it("Nash falls back to proportional on negative surplus", () => {
    const cmr = makeCmr();
    const p = allocateNash(cmr, 0.001, 0.001, 0.5);
    assert.equal(p.method, AllocationMethod.PROPORTIONAL);
  });

  it("alpha=1.0 favors requestor", () => {
    const cmr = makeCmr();
    const p1 = allocateNash(cmr, 1.0, 0.5, 0.0);
    const p2 = allocateNash(cmr, 1.0, 0.5, 1.0);
    assert.ok(p2.requestorPaysUsd < p1.requestorPaysUsd);
  });
});

describe("allocation.ts — dispatcher", () => {
  it("allocate dispatches correctly", () => {
    const cmr = makeCmr();
    for (const method of [
      AllocationMethod.REQUESTOR_PAYS,
      AllocationMethod.RESPONDER_PAYS,
      AllocationMethod.EQUAL_SPLIT,
      AllocationMethod.PROPORTIONAL,
      AllocationMethod.SHAPLEY,
    ]) {
      const p = allocate(cmr, method);
      assert.ok(p.method.length > 0);
    }
  });

  it("allocate throws on unknown method", () => {
    const cmr = makeCmr();
    assert.throws(() => allocate(cmr, "nonexistent"));
  });

  it("allocate passes kwargs to Nash", () => {
    const cmr = makeCmr();
    const p = allocate(cmr, AllocationMethod.NASH_BARGAINING, {
      value_a: 1.0,
      value_b: 0.5,
      alpha: 0.5,
    });
    assert.equal(p.method, AllocationMethod.NASH_BARGAINING);
  });
});

// ========================================================================
// settlement.ts
// ========================================================================

describe("settlement.ts — SettlementEngine", () => {
  it("Tier 1 returns null proposal", () => {
    const engine = new SettlementEngine({
      tier: SettlementTier.TIER_1_METERING,
    });
    const cmr = makeCmr();
    assert.equal(engine.propose(cmr), null);
  });

  it("Tier 2 returns proposal above threshold", () => {
    const engine = new SettlementEngine({
      tier: SettlementTier.TIER_2_RULE_BASED,
      method: AllocationMethod.SHAPLEY,
      thresholdUsd: 0.001,
    });
    const cmr = makeCmr();
    const p = engine.propose(cmr);
    assert.ok(p !== null);
    assert.equal(p!.method, AllocationMethod.SHAPLEY);
  });

  it("Tier 2 returns null below threshold", () => {
    const engine = new SettlementEngine({
      tier: SettlementTier.TIER_2_RULE_BASED,
      thresholdUsd: 100.0,
    });
    const cmr = makeCmr();
    assert.equal(engine.propose(cmr), null);
  });

  it("settle executes payment", () => {
    const engine = new SettlementEngine({
      tier: SettlementTier.TIER_3_DYNAMIC,
      thresholdUsd: 0.001,
    });
    const cmr = makeCmr();
    const receipt = engine.settle(cmr);
    assert.ok(receipt !== null);
    assert.equal(receipt!.status, "completed");
    assert.ok(receipt!.amountUsd > 0);
  });

  it("verifyProposals detects agreement", () => {
    const engine = new SettlementEngine();
    const p1 = new SettlementProposal({ requestorPaysUsd: 0.10 });
    const p2 = new SettlementProposal({ requestorPaysUsd: 0.10 });
    const [agreed, disc] = engine.verifyProposals(p1, p2, 0.20);
    assert.ok(agreed);
    assert.equal(disc, 0.0);
  });

  it("verifyProposals detects disagreement", () => {
    const engine = new SettlementEngine({ tolerance: 0.01 });
    const p1 = new SettlementProposal({ requestorPaysUsd: 0.10 });
    const p2 = new SettlementProposal({ requestorPaysUsd: 0.15 });
    const [agreed, _disc] = engine.verifyProposals(p1, p2, 0.20);
    assert.ok(!agreed);
  });
});

describe("settlement.ts — SettlementBatch", () => {
  it("accumulates CMRs", () => {
    const batch = new SettlementBatch();
    assert.equal(batch.count, 0);
    batch.add(makeCmr());
    assert.equal(batch.count, 1);
    batch.add(makeCmr());
    assert.equal(batch.count, 2);
  });

  it("flush resets batch", () => {
    const batch = new SettlementBatch({ thresholdUsd: 0.0001 });
    batch.add(makeCmr());
    const result = batch.flush();
    assert.ok(result.net_amount_usd as number > 0);
    assert.equal(result.interaction_count, 1);
    assert.equal(batch.count, 0);
  });

  it("empty flush returns zeros", () => {
    const batch = new SettlementBatch();
    const result = batch.flush();
    assert.equal(result.net_amount_usd, 0.0);
    assert.equal(result.interaction_count, 0);
  });
});

describe("settlement.ts — CMR utilities", () => {
  it("cmrHash produces 64-char hex", () => {
    const cmr = makeCmr();
    const hash = cmrHash(cmr);
    assert.equal(hash.length, 64);
  });

  it("cmrHash is deterministic", () => {
    const cmr = makeCmr();
    assert.equal(cmrHash(cmr), cmrHash(cmr));
  });

  it("verifyCmrPair matches identical CMRs", () => {
    const cmr = makeCmr();
    assert.ok(verifyCmrPair(cmr, cmr));
  });

  it("verifyCmrPair rejects different interaction IDs", () => {
    const a = makeCmr();
    const b = makeCmr();
    assert.ok(!verifyCmrPair(a, b));
  });
});

describe("settlement.ts — PaymentRail", () => {
  it("default rail returns successful receipt", () => {
    const rail = new PaymentRail();
    const receipt = rail.settle("a", "b", 0.05, "int-1");
    assert.equal(receipt.status, "completed");
    assert.equal(receipt.amountUsd, 0.05);
  });

  it("stream open/close", () => {
    const rail = new PaymentRail();
    const handle = rail.streamOpen("a", "b", 0.001);
    assert.ok(handle.includes("stream"));
    const receipt = rail.streamClose(handle);
    assert.equal(receipt.status, "closed");
  });
});

// ========================================================================
// spam.ts
// ========================================================================

describe("spam.ts", () => {
  it("classifyReputation tiers", () => {
    assert.equal(classifyReputation(90), ReputationTier.HIGH);
    assert.equal(classifyReputation(60), ReputationTier.MEDIUM);
    assert.equal(classifyReputation(20), ReputationTier.LOW);
    assert.equal(classifyReputation(-1), ReputationTier.UNKNOWN);
  });

  it("depositMultiplierForTier", () => {
    assert.equal(depositMultiplierForTier(ReputationTier.HIGH), 0.0);
    assert.equal(depositMultiplierForTier(ReputationTier.UNKNOWN), 5.0);
  });

  it("calculateDeposit for unknown agent", () => {
    const [amount, tier] = calculateDeposit(10000, 3.0);
    assert.equal(tier, ReputationTier.UNKNOWN);
    assert.ok(amount > 0);
  });

  it("calculateDeposit for high-rep agent is zero", () => {
    const [amount, tier] = calculateDeposit(10000, 3.0, 90);
    assert.equal(tier, ReputationTier.HIGH);
    assert.equal(amount, 0.0);
  });

  it("maxRequestTokens progressive limits", () => {
    assert.equal(maxRequestTokens(10, 2), 1_000);
    assert.equal(maxRequestTokens(30, 10), 10_000);
    assert.equal(maxRequestTokens(50, 50), 100_000);
    assert.equal(maxRequestTokens(90, 200), -1);
  });

  it("checkAccess allows within limits", () => {
    const [allowed, reason] = checkAccess(10, 2, 500);
    assert.ok(allowed);
    assert.equal(reason, "within_limits");
  });

  it("checkAccess rejects over limit", () => {
    const [allowed, reason] = checkAccess(10, 2, 5000);
    assert.ok(!allowed);
    assert.ok(reason.includes("exceeds"));
  });

  it("checkAccess unlimited for high rep", () => {
    const [allowed, reason] = checkAccess(90, 200, 999999);
    assert.ok(allowed);
    assert.equal(reason, "unlimited");
  });

  it("createDeposit returns committed record", () => {
    const dep = createDeposit({
      requestorId: "a",
      responderId: "b",
      estimatedRequestTokens: 10000,
      responderInputRatePerMtok: 3.0,
    });
    assert.equal(dep.status, DepositStatus.COMMITTED);
    assert.ok(dep.amountUsd > 0);
  });

  it("resolveDeposit refunds non-spam", () => {
    const dep = createDeposit({
      requestorId: "a",
      responderId: "b",
      estimatedRequestTokens: 10000,
      responderInputRatePerMtok: 3.0,
    });
    resolveDeposit(dep, false);
    assert.equal(dep.status, DepositStatus.REFUNDED);
  });

  it("resolveDeposit forfeits spam", () => {
    const dep = createDeposit({
      requestorId: "a",
      responderId: "b",
      estimatedRequestTokens: 10000,
      responderInputRatePerMtok: 3.0,
    });
    resolveDeposit(dep, true);
    assert.equal(dep.status, DepositStatus.FORFEITED);
  });
});

// ========================================================================
// congestion.ts
// ========================================================================

describe("congestion.ts", () => {
  it("congestionMultiplier ranges", () => {
    assert.equal(congestionMultiplier(0.0), 1.0);
    assert.equal(congestionMultiplier(0.3), 1.0);
    assert.ok(congestionMultiplier(0.6) > 1.0);
    assert.ok(congestionMultiplier(0.85) > congestionMultiplier(0.6));
    assert.ok(congestionMultiplier(0.97) > congestionMultiplier(0.85));
  });

  it("congestionLevel classifications", () => {
    assert.equal(congestionLevel(0.3), CongestionLevel.ABUNDANT);
    assert.equal(congestionLevel(0.6), CongestionLevel.MODERATE);
    assert.equal(congestionLevel(0.85), CongestionLevel.HEAVY);
    assert.equal(congestionLevel(0.97), CongestionLevel.CRITICAL);
  });

  it("effectiveTokenPrice returns all components", () => {
    const result = effectiveTokenPrice({
      baseRatePerMtok: 3.0,
      tokens: 10000,
      utilization: 0.6,
      qosTier: QoSTier.STANDARD,
    });
    assert.ok("btc" in result);
    assert.ok("cp" in result);
    assert.ok("po" in result);
    assert.ok("total" in result);
    assert.ok(result.cp > 0);
    assert.ok(
      Math.abs(result.total - (result.btc + result.cp + result.po)) < 0.0001
    );
  });

  it("effectiveTokenPrice priority costs more", () => {
    const standard = effectiveTokenPrice({
      baseRatePerMtok: 3.0,
      tokens: 10000,
      qosTier: QoSTier.STANDARD,
    });
    const priority = effectiveTokenPrice({
      baseRatePerMtok: 3.0,
      tokens: 10000,
      qosTier: QoSTier.PRIORITY,
    });
    assert.ok(priority.total > standard.total);
  });

  it("positionMultiplier at boundaries", () => {
    assert.equal(positionMultiplier(0, 1000), 0.0);
    assert.equal(positionMultiplier(100, 0), 0.0);
    assert.ok(positionMultiplier(500, 1000) > 0);
    assert.ok(positionMultiplier(500, 1000) < 1.0);
    assert.ok(Math.abs(positionMultiplier(1000, 1000) - 1.0) < 0.001);
  });

  it("qosConfigForTier returns correct tier", () => {
    const economy = qosConfigForTier(QoSTier.ECONOMY);
    assert.equal(economy.tier, QoSTier.ECONOMY);
    assert.equal(economy.maxRequestSizeTokens, 200_000);

    const reserved = qosConfigForTier(QoSTier.RESERVED);
    assert.equal(reserved.tier, QoSTier.RESERVED);
    assert.equal(reserved.maxRequestSizeTokens, 1_000_000);
  });

  it("checkQosLimits allows within limits", () => {
    const config = qosConfigForTier(QoSTier.STANDARD);
    const result = checkQosLimits(config, 100_000, 0.5);
    assert.ok(result.allowed);
  });

  it("checkQosLimits rejects oversized request", () => {
    const config = qosConfigForTier(QoSTier.ECONOMY);
    const result = checkQosLimits(config, 500_000, 0.5);
    assert.ok(!result.size_ok);
    assert.ok(!result.allowed);
  });

  it("generateBackPressure status transitions", () => {
    const ok = generateBackPressure(0.3);
    assert.equal(ok.cwepStatus, BackPressureStatus.OK);
    assert.equal(ok.availableTiers.length, 4);

    const congested = generateBackPressure(0.7);
    assert.equal(congested.cwepStatus, BackPressureStatus.CONGESTED);
    assert.equal(congested.availableTiers.length, 3);

    const overloaded = generateBackPressure(0.97);
    assert.equal(overloaded.cwepStatus, BackPressureStatus.OVERLOADED);
    assert.equal(overloaded.availableTiers.length, 2);
  });
});

// ========================================================================
// caching.ts
// ========================================================================

describe("caching.ts", () => {
  it("cacheAmortizedCost produces savings", () => {
    const result = cacheAmortizedCost({
      contextTokens: 100_000,
      inputRatePerMtok: 3.0,
      numInteractions: 10,
    });
    assert.ok(result.amortized_cost < result.uncached_cost);
    assert.ok(result.savings_pct > 0);
    assert.ok(result.first_cost > result.subsequent_cost);
  });

  it("cacheAmortizedCost handles 1 interaction", () => {
    const result = cacheAmortizedCost({
      contextTokens: 100_000,
      inputRatePerMtok: 3.0,
      numInteractions: 1,
    });
    assert.ok(Math.abs(result.amortized_cost - result.first_cost) < 0.0001);
  });

  it("compressionRoi positive ROI", () => {
    const result = compressionRoi({
      uncompressedTokens: 100_000,
      compressedTokens: 30_000,
      inputRatePerMtok: 3.0,
      compressorOutputRatePerMtok: 15.0,
      compressorTokens: 5_000,
    });
    assert.ok(result.net_savings > 0);
    assert.ok(result.roi > 0);
    assert.ok(result.compression_ratio > 1.0);
  });

  it("compressionRoi with no compressor cost", () => {
    const result = compressionRoi({
      uncompressedTokens: 100_000,
      compressedTokens: 30_000,
      inputRatePerMtok: 3.0,
    });
    assert.equal(result.cost, 0);
    assert.equal(result.roi, 0);
    assert.ok(result.savings > 0);
  });

  it("memoryVsContextCrossover finds crossover", () => {
    const result = memoryVsContextCrossover({
      contextTokens: 100_000,
      inputRatePerMtok: 3.0,
    });
    assert.ok(result.crossover_point > 0);
    assert.ok(result.memory_costs.length > 0);
    assert.ok(result.context_costs.length > 0);
  });

  it("CacheTracker tracks hits and misses", () => {
    const tracker = new CacheTracker();
    tracker.recordHit(50_000, 3.0);
    tracker.recordHit(30_000, 3.0);
    tracker.recordMiss(10_000);
    assert.equal(tracker.hits, 2);
    assert.equal(tracker.misses, 1);
    assert.ok(tracker.hitRate > 0.6);
    assert.ok(tracker.estimatedSavingsUsd > 0);
    assert.equal(tracker.totalInteractions, 3);

    const summary = tracker.summary();
    assert.equal(summary.hits, 2);
    assert.equal(summary.misses, 1);
  });
});

// ========================================================================
// store.ts
// ========================================================================

describe("store.ts — CWEPStore", () => {
  const testDir = ".cwep-test-" + Date.now();

  afterEach(() => {
    try {
      rmSync(testDir, { recursive: true, force: true });
    } catch {
      // ignore cleanup errors
    }
  });

  it("creates store directory", () => {
    const store = new CWEPStore(testDir);
    assert.ok(existsSync(testDir));
    assert.equal(store.cmrCount(), 0);
  });

  it("appends and reads CMRs", () => {
    const store = new CWEPStore(testDir);
    const cmr = makeCmr();
    store.appendCmr(cmr);
    assert.equal(store.cmrCount(), 1);

    const read = store.readCmrs();
    assert.equal(read.length, 1);
    assert.equal(read[0].interactionId, cmr.interactionId);
  });

  it("appends and reads deposits", () => {
    const store = new CWEPStore(testDir);
    const dep = new DepositRecord({
      requestorId: "a",
      responderId: "b",
      amountUsd: 0.05,
    });
    store.appendDeposit(dep);
    assert.equal(store.depositCount(), 1);

    const read = store.readDeposits();
    assert.equal(read.length, 1);
    assert.equal(read[0].requestorId, "a");
  });

  it("appends and reads settlements", () => {
    const store = new CWEPStore(testDir);
    store.appendSettlement({ method: "shapley", amount: 0.05 });
    assert.equal(store.settlementCount(), 1);

    const read = store.readSettlements();
    assert.equal(read.length, 1);
    assert.equal(read[0].method, "shapley");
  });

  it("statistics aggregates correctly", () => {
    const store = new CWEPStore(testDir);
    store.appendCmr(makeCmr());
    store.appendCmr(makeCmr());
    store.appendDeposit(new DepositRecord());

    const stats = store.statistics();
    assert.equal(stats.cmr_count, 2);
    assert.equal(stats.deposit_count, 1);
    assert.ok((stats.total_cost_usd as number) > 0);
  });

  it("lastParseErrors tracks corrupt lines", () => {
    const store = new CWEPStore(testDir);
    store.appendCmr(makeCmr());
    const { appendFileSync } = require("node:fs");
    const { join } = require("node:path");
    appendFileSync(join(testDir, "metering.jsonl"), "NOT_JSON\n", "utf-8");
    store.appendCmr(makeCmr());

    const cmrs = store.readCmrs();
    assert.equal(cmrs.length, 2);
    assert.equal(store.lastParseErrors, 1);
  });

  it("limit parameter works", () => {
    const store = new CWEPStore(testDir);
    for (let i = 0; i < 5; i++) {
      store.appendCmr(makeCmr());
    }
    const limited = store.readCmrs(2);
    assert.equal(limited.length, 2);
  });
});
