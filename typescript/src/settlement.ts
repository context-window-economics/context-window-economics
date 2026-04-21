import { createHash } from "node:crypto";
import { allocate } from "./allocation";
import {
  AllocationMethod,
  CostMeteringRecord,
  DEFAULT_BATCH_THRESHOLD_USD,
  DEFAULT_BATCH_WINDOW_SECONDS,
  DEFAULT_SETTLEMENT_THRESHOLD,
  SettlementProposal,
  SettlementTier,
} from "./types";

// ---------------------------------------------------------------------------
// Payment rail abstraction
// ---------------------------------------------------------------------------

export interface SettlementReceiptData {
  interaction_id: string;
  from_agent: string;
  to_agent: string;
  amount_usd: number;
  status: string;
  timestamp: string;
  tx_ref: string | null;
}

export class SettlementReceipt {
  interactionId: string;
  fromAgent: string;
  toAgent: string;
  amountUsd: number;
  status: string;
  timestamp: string;
  txRef: string | null;

  constructor(opts?: Partial<{
    interactionId: string;
    fromAgent: string;
    toAgent: string;
    amountUsd: number;
    status: string;
    timestamp: string;
    txRef: string | null;
  }>) {
    this.interactionId = opts?.interactionId ?? "";
    this.fromAgent = opts?.fromAgent ?? "";
    this.toAgent = opts?.toAgent ?? "";
    this.amountUsd = opts?.amountUsd ?? 0.0;
    this.status = opts?.status ?? "completed";
    this.timestamp = opts?.timestamp ?? new Date().toISOString();
    this.txRef = opts?.txRef ?? null;
  }

  toDict(): SettlementReceiptData {
    return {
      interaction_id: this.interactionId,
      from_agent: this.fromAgent,
      to_agent: this.toAgent,
      amount_usd: this.amountUsd,
      status: this.status,
      timestamp: this.timestamp,
      tx_ref: this.txRef,
    };
  }
}

export class PaymentRail {
  commitDeposit(_amountUsd: number, _escrowId: string): boolean {
    return true;
  }

  releaseDeposit(_escrowId: string, _toAgent: string): boolean {
    return true;
  }

  forfeitDeposit(_escrowId: string): boolean {
    return true;
  }

  settle(
    fromAgent: string,
    toAgent: string,
    amountUsd: number,
    interactionId: string
  ): SettlementReceipt {
    return new SettlementReceipt({
      interactionId,
      fromAgent,
      toAgent,
      amountUsd,
      status: "completed",
      timestamp: new Date().toISOString(),
    });
  }

  streamOpen(fromAgent: string, toAgent: string, _rateUsdPerSecond: number): string {
    return `stream-${fromAgent}-${toAgent}`;
  }

  streamClose(handle: string): SettlementReceipt {
    return new SettlementReceipt({
      interactionId: handle,
      status: "closed",
      timestamp: new Date().toISOString(),
    });
  }
}

// ---------------------------------------------------------------------------
// Settlement Engine
// ---------------------------------------------------------------------------

export class SettlementEngine {
  readonly tier: string;
  readonly method: string;
  readonly thresholdUsd: number;
  readonly paymentRail: PaymentRail;
  readonly tolerance: number;
  readonly allocationKwargs: Record<string, number>;

  constructor(opts?: Partial<{
    tier: string;
    method: string;
    thresholdUsd: number;
    paymentRail: PaymentRail;
    tolerance: number;
    allocationKwargs: Record<string, number>;
  }>) {
    this.tier = opts?.tier ?? SettlementTier.TIER_1_METERING;
    this.method = opts?.method ?? AllocationMethod.SHAPLEY;
    this.thresholdUsd = opts?.thresholdUsd ?? DEFAULT_SETTLEMENT_THRESHOLD;
    this.paymentRail = opts?.paymentRail ?? new PaymentRail();
    this.tolerance = opts?.tolerance ?? 0.05;
    this.allocationKwargs = opts?.allocationKwargs ?? {};
  }

  propose(cmr: CostMeteringRecord): SettlementProposal | null {
    if (this.tier === SettlementTier.TIER_1_METERING) return null;
    if (cmr.totals.totalCostUsd < this.thresholdUsd) return null;
    return allocate(cmr, this.method, this.allocationKwargs);
  }

  settle(
    cmr: CostMeteringRecord,
    proposal?: SettlementProposal | null
  ): SettlementReceipt | null {
    if (proposal === undefined || proposal === null) {
      proposal = this.propose(cmr);
    }
    if (!proposal) return null;
    if (proposal.netTransferUsd < this.thresholdUsd) return null;

    cmr.settlement = proposal;

    let fromAgent: string;
    let toAgent: string;
    if (proposal.transferDirection === "requestor_to_responder") {
      fromAgent = cmr.requestor?.agentId ?? "";
      toAgent = cmr.responder?.agentId ?? "";
    } else {
      fromAgent = cmr.responder?.agentId ?? "";
      toAgent = cmr.requestor?.agentId ?? "";
    }

    return this.paymentRail.settle(
      fromAgent,
      toAgent,
      proposal.netTransferUsd,
      cmr.interactionId
    );
  }

  verifyProposals(
    proposalA: SettlementProposal,
    proposalB: SettlementProposal,
    totalCost: number
  ): [boolean, number] {
    const discrepancy = Math.abs(
      proposalA.requestorPaysUsd - proposalB.requestorPaysUsd
    );
    const threshold = totalCost * this.tolerance;
    return [discrepancy <= threshold, discrepancy];
  }
}

// ---------------------------------------------------------------------------
// Settlement Batching
// ---------------------------------------------------------------------------

export class SettlementBatch {
  readonly windowSeconds: number;
  readonly thresholdUsd: number;
  readonly method: string;
  readonly allocationKwargs: Record<string, number>;
  private _cmrs: CostMeteringRecord[] = [];
  private _started: Date | null = null;

  constructor(opts?: Partial<{
    windowSeconds: number;
    thresholdUsd: number;
    method: string;
    allocationKwargs: Record<string, number>;
  }>) {
    this.windowSeconds = opts?.windowSeconds ?? DEFAULT_BATCH_WINDOW_SECONDS;
    this.thresholdUsd = opts?.thresholdUsd ?? DEFAULT_BATCH_THRESHOLD_USD;
    this.method = opts?.method ?? AllocationMethod.SHAPLEY;
    this.allocationKwargs = opts?.allocationKwargs ?? {};
  }

  add(cmr: CostMeteringRecord): void {
    if (this._started === null) {
      this._started = new Date();
    }
    this._cmrs.push(cmr);
  }

  get count(): number {
    return this._cmrs.length;
  }

  shouldFlush(): boolean {
    if (this._cmrs.length === 0) return false;

    if (this._started !== null) {
      const elapsed = (Date.now() - this._started.getTime()) / 1000;
      if (elapsed >= this.windowSeconds) return true;
    }

    const net = this._computeNet();
    return Math.abs(net) >= this.thresholdUsd;
  }

  flush(): Record<string, unknown> {
    if (this._cmrs.length === 0) {
      return {
        net_amount_usd: 0.0,
        direction: "",
        interaction_count: 0,
        cmr_ids: [],
      };
    }

    let net = this._computeNet();
    const cmrIds = this._cmrs.map((c) => c.interactionId);
    const count = this._cmrs.length;

    let direction: string;
    if (net >= 0) {
      direction = "requestor_to_responder";
    } else {
      direction = "responder_to_requestor";
      net = -net;
    }

    const result = {
      net_amount_usd: net,
      direction,
      interaction_count: count,
      cmr_ids: cmrIds,
    };

    this._cmrs = [];
    this._started = null;
    return result;
  }

  private _computeNet(): number {
    let totalNet = 0.0;
    for (const cmr of this._cmrs) {
      const proposal = allocate(cmr, this.method, this.allocationKwargs);
      if (proposal.transferDirection === "requestor_to_responder") {
        totalNet += proposal.netTransferUsd;
      } else {
        totalNet -= proposal.netTransferUsd;
      }
    }
    return totalNet;
  }
}

// ---------------------------------------------------------------------------
// CMR verification utilities
// ---------------------------------------------------------------------------

function sortedStringify(value: unknown): string {
  if (value === null || value === undefined) return JSON.stringify(value);
  if (Array.isArray(value)) {
    return "[" + value.map(sortedStringify).join(",") + "]";
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    return "{" + keys.map(k => JSON.stringify(k) + ":" + sortedStringify(obj[k])).join(",") + "}";
  }
  return JSON.stringify(value);
}

export function cmrHash(cmr: CostMeteringRecord): string {
  const data = sortedStringify(cmr.toDict());
  return createHash("sha256").update(data, "utf-8").digest("hex");
}

export function verifyCmrPair(
  cmrA: CostMeteringRecord,
  cmrB: CostMeteringRecord
): boolean {
  if (cmrA.interactionId !== cmrB.interactionId) return false;

  for (const flowKey of Object.keys(cmrA.flows)) {
    if (!(flowKey in cmrB.flows)) return false;
    if (cmrA.flows[flowKey].tokens !== cmrB.flows[flowKey].tokens) return false;
  }
  return true;
}
