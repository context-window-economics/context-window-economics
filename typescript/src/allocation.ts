import {
  AllocationMethod,
  CostFlow,
  CostMeteringRecord,
  SettlementProposal,
} from "./types";

// ---------------------------------------------------------------------------
// Rule-based allocation (Tier 2)
// ---------------------------------------------------------------------------

export function allocateRequestorPays(
  cmr: CostMeteringRecord
): SettlementProposal {
  const total = cmr.totals.totalCostUsd;
  const responderIncurred = cmr.totals.responderIncurredUsd;
  return new SettlementProposal({
    method: AllocationMethod.REQUESTOR_PAYS,
    requestorPaysUsd: total,
    responderPaysUsd: 0.0,
    netTransferUsd: responderIncurred,
    transferDirection: "requestor_to_responder",
  });
}

export function allocateResponderPays(
  cmr: CostMeteringRecord
): SettlementProposal {
  const total = cmr.totals.totalCostUsd;
  const requestorIncurred = cmr.totals.requestorIncurredUsd;
  return new SettlementProposal({
    method: AllocationMethod.RESPONDER_PAYS,
    requestorPaysUsd: 0.0,
    responderPaysUsd: total,
    netTransferUsd: requestorIncurred,
    transferDirection: "responder_to_requestor",
  });
}

export function allocateEqualSplit(
  cmr: CostMeteringRecord
): SettlementProposal {
  const total = cmr.totals.totalCostUsd;
  const half = total / 2.0;
  const reqIncurred = cmr.totals.requestorIncurredUsd;
  const respIncurred = cmr.totals.responderIncurredUsd;

  let net: number;
  let direction: string;
  if (reqIncurred > half) {
    net = reqIncurred - half;
    direction = "responder_to_requestor";
  } else {
    net = respIncurred - half;
    direction = "requestor_to_responder";
  }

  return new SettlementProposal({
    method: AllocationMethod.EQUAL_SPLIT,
    requestorPaysUsd: half,
    responderPaysUsd: half,
    netTransferUsd: Math.abs(net),
    transferDirection: direction,
  });
}

export function allocateProportional(
  cmr: CostMeteringRecord
): SettlementProposal {
  const ro = cmr.flows[CostFlow.REQUEST_OUTPUT].tokens;
  const ri = cmr.flows[CostFlow.REQUEST_INPUT].tokens;
  const so = cmr.flows[CostFlow.RESPONSE_OUTPUT].tokens;
  const si = cmr.flows[CostFlow.RESPONSE_INPUT].tokens;

  const totalTokens = ro + ri + so + si;
  if (totalTokens === 0) {
    return new SettlementProposal({
      method: AllocationMethod.PROPORTIONAL,
      requestorPaysUsd: 0.0,
      responderPaysUsd: 0.0,
      netTransferUsd: 0.0,
      transferDirection: "",
    });
  }

  const reqTokens = ro + si;
  const reqShare = reqTokens / totalTokens;

  const total = cmr.totals.totalCostUsd;
  const reqPays = total * reqShare;
  const respPays = total * (1.0 - reqShare);

  const reqIncurred = cmr.totals.requestorIncurredUsd;
  let net = reqPays - reqIncurred;
  let direction: string;
  if (net >= 0) {
    direction = "requestor_to_responder";
  } else {
    direction = "responder_to_requestor";
    net = -net;
  }

  return new SettlementProposal({
    method: AllocationMethod.PROPORTIONAL,
    requestorPaysUsd: reqPays,
    responderPaysUsd: respPays,
    netTransferUsd: net,
    transferDirection: direction,
  });
}

// ---------------------------------------------------------------------------
// Shapley value allocation (Tier 3)
// ---------------------------------------------------------------------------

export function allocateShapley(
  cmr: CostMeteringRecord,
  standaloneCostB: number = 0.0
): SettlementProposal {
  const ro = cmr.flows[CostFlow.REQUEST_OUTPUT].costUsd;
  const ri = cmr.flows[CostFlow.REQUEST_INPUT].costUsd;
  const so = cmr.flows[CostFlow.RESPONSE_OUTPUT].costUsd;
  const si = cmr.flows[CostFlow.RESPONSE_INPUT].costUsd;

  const joint = ro + ri + so + si;
  const standaloneA = ro;

  let shapleyA = (joint + standaloneA - standaloneCostB) / 2.0;
  let shapleyB = (joint + standaloneCostB - standaloneA) / 2.0;

  shapleyA = Math.max(0.0, shapleyA);
  shapleyB = Math.max(0.0, shapleyB);

  const reqIncurred = cmr.totals.requestorIncurredUsd;
  let net = shapleyA - reqIncurred;
  let direction: string;
  if (net >= 0) {
    direction = "requestor_to_responder";
  } else {
    direction = "responder_to_requestor";
    net = -net;
  }

  return new SettlementProposal({
    method: AllocationMethod.SHAPLEY,
    requestorPaysUsd: shapleyA,
    responderPaysUsd: shapleyB,
    netTransferUsd: net,
    transferDirection: direction,
    parameters: { standalone_cost_b: standaloneCostB },
  });
}

// ---------------------------------------------------------------------------
// Nash bargaining allocation (Tier 3)
// ---------------------------------------------------------------------------

export function allocateNash(
  cmr: CostMeteringRecord,
  valueA: number,
  valueB: number,
  alpha: number = 0.5,
  disagreementA: number = 0.0,
  disagreementB: number = 0.0
): SettlementProposal {
  const totalCost = cmr.totals.totalCostUsd;
  const surplus =
    valueA + valueB - totalCost - (disagreementA + disagreementB);

  if (surplus <= 0) {
    return allocateProportional(cmr);
  }

  let paymentA = valueA - disagreementA - alpha * surplus;
  paymentA = Math.max(0.0, Math.min(totalCost, paymentA));
  const paymentB = totalCost - paymentA;

  const reqIncurred = cmr.totals.requestorIncurredUsd;
  let net = paymentA - reqIncurred;
  let direction: string;
  if (net >= 0) {
    direction = "requestor_to_responder";
  } else {
    direction = "responder_to_requestor";
    net = -net;
  }

  return new SettlementProposal({
    method: AllocationMethod.NASH_BARGAINING,
    requestorPaysUsd: paymentA,
    responderPaysUsd: paymentB,
    netTransferUsd: net,
    transferDirection: direction,
    parameters: {
      alpha,
      value_a: valueA,
      value_b: valueB,
      disagreement_a: disagreementA,
      disagreement_b: disagreementB,
      surplus,
    },
  });
}

// ---------------------------------------------------------------------------
// Dispatcher
// ---------------------------------------------------------------------------

export function allocate(
  cmr: CostMeteringRecord,
  method: string = AllocationMethod.SHAPLEY,
  kwargs: Record<string, number> = {}
): SettlementProposal {
  const dispatch: Record<string, () => SettlementProposal> = {
    [AllocationMethod.REQUESTOR_PAYS]: () => allocateRequestorPays(cmr),
    [AllocationMethod.RESPONDER_PAYS]: () => allocateResponderPays(cmr),
    [AllocationMethod.EQUAL_SPLIT]: () => allocateEqualSplit(cmr),
    [AllocationMethod.PROPORTIONAL]: () => allocateProportional(cmr),
    [AllocationMethod.SHAPLEY]: () =>
      allocateShapley(cmr, kwargs.standalone_cost_b ?? 0.0),
    [AllocationMethod.NASH_BARGAINING]: () =>
      allocateNash(
        cmr,
        kwargs.value_a ?? 0.0,
        kwargs.value_b ?? 0.0,
        kwargs.alpha ?? 0.5,
        kwargs.disagreement_a ?? 0.0,
        kwargs.disagreement_b ?? 0.0
      ),
    [AllocationMethod.BENEFICIARY_PAYS]: () => allocateProportional(cmr),
  };

  const fn = dispatch[method];
  if (!fn) {
    throw new Error(`Unknown allocation method: ${method}`);
  }
  return fn();
}
