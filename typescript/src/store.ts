import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
} from "node:fs";
import { dirname, join } from "node:path";
import {
  CostMeteringRecord,
  type CostMeteringRecordData,
  DepositRecord,
  type DepositRecordData,
} from "./types";

const DEFAULT_STORE_DIR = ".cwep";
const CMR_FILE = "metering.jsonl";
const SETTLEMENT_FILE = "settlements.jsonl";
const DEPOSIT_FILE = "deposits.jsonl";

export class CWEPStore {
  readonly storeDir: string;
  private readonly _cmrPath: string;
  private readonly _settlementPath: string;
  private readonly _depositPath: string;
  private _lastParseErrors: number = 0;

  constructor(storeDir: string = DEFAULT_STORE_DIR) {
    this.storeDir = storeDir;
    mkdirSync(storeDir, { recursive: true });
    this._cmrPath = join(storeDir, CMR_FILE);
    this._settlementPath = join(storeDir, SETTLEMENT_FILE);
    this._depositPath = join(storeDir, DEPOSIT_FILE);
  }

  get lastParseErrors(): number {
    return this._lastParseErrors;
  }

  // ----- CMR operations -----

  appendCmr(cmr: CostMeteringRecord): void {
    this._append(this._cmrPath, cmr.toDict() as unknown as Record<string, unknown>);
  }

  readCmrs(limit: number = 0): CostMeteringRecord[] {
    let records = this._readAll(this._cmrPath);
    if (limit > 0) {
      records = records.slice(-limit);
    }
    return records.map((r) =>
      CostMeteringRecord.fromDict(r as unknown as CostMeteringRecordData)
    );
  }

  cmrCount(): number {
    return this._countLines(this._cmrPath);
  }

  // ----- Settlement operations -----

  appendSettlement(data: Record<string, unknown>): void {
    this._append(this._settlementPath, data);
  }

  readSettlements(limit: number = 0): Record<string, unknown>[] {
    let records = this._readAll(this._settlementPath);
    if (limit > 0) {
      records = records.slice(-limit);
    }
    return records;
  }

  settlementCount(): number {
    return this._countLines(this._settlementPath);
  }

  // ----- Deposit operations -----

  appendDeposit(deposit: DepositRecord): void {
    this._append(this._depositPath, deposit.toDict() as unknown as Record<string, unknown>);
  }

  readDeposits(limit: number = 0): DepositRecord[] {
    let records = this._readAll(this._depositPath);
    if (limit > 0) {
      records = records.slice(-limit);
    }
    return records.map((r) => DepositRecord.fromDict(r as unknown as DepositRecordData));
  }

  depositCount(): number {
    return this._countLines(this._depositPath);
  }

  // ----- Aggregate statistics -----

  statistics(): Record<string, unknown> {
    const cmrs = this.readCmrs();
    let totalCost = 0;
    let totalTokens = 0;
    const agentCosts: Record<string, number> = {};

    for (const c of cmrs) {
      totalCost += c.totals.totalCostUsd;
      totalTokens += c.totals.totalTokens;

      if (c.requestor) {
        const aid = c.requestor.agentId;
        agentCosts[aid] =
          (agentCosts[aid] ?? 0.0) + c.totals.requestorIncurredUsd;
      }
      if (c.responder) {
        const aid = c.responder.agentId;
        agentCosts[aid] =
          (agentCosts[aid] ?? 0.0) + c.totals.responderIncurredUsd;
      }
    }

    return {
      cmr_count: cmrs.length,
      settlement_count: this.settlementCount(),
      deposit_count: this.depositCount(),
      total_cost_usd: totalCost,
      total_tokens: totalTokens,
      agent_costs: agentCosts,
      store_dir: this.storeDir,
    };
  }

  // ----- Internal -----

  private _append(path: string, data: Record<string, unknown>): void {
    const dir = dirname(path);
    if (dir && dir !== ".") {
      mkdirSync(dir, { recursive: true });
    }
    appendFileSync(path, JSON.stringify(data) + "\n", "utf-8");
  }

  private _readAll(path: string): Record<string, unknown>[] {
    if (!existsSync(path)) return [];
    const content = readFileSync(path, "utf-8");
    const records: Record<string, unknown>[] = [];
    let parseErrors = 0;
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        records.push(JSON.parse(trimmed));
      } catch {
        parseErrors++;
      }
    }
    this._lastParseErrors = parseErrors;
    return records;
  }

  private _countLines(path: string): number {
    if (!existsSync(path)) return 0;
    const content = readFileSync(path, "utf-8");
    let count = 0;
    for (const line of content.split("\n")) {
      if (line.trim()) count++;
    }
    return count;
  }
}
