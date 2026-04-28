"use client";

import Link from "next/link";
import { CheckCircle2, Eraser, Pencil, RotateCcw, Undo2 } from "lucide-react";

import { StatusBadge } from "@/components/StatusBadge";
import { moveToProblemLine } from "@/lib/board";
import { orientationLabel, sideLabel } from "@/lib/pieces";
import { variantNames } from "@/lib/problemData";
import { isValidVariantName } from "@/lib/variantName";
import type { CreateState } from "@/hooks/useCreateSession";
import type { ProblemMove, Side } from "@/lib/types";

type CreateSidePanelProps = {
  readonly state: CreateState;
  readonly lastMove: ProblemMove | null;
  readonly onSideChange: (side: Side) => void;
  readonly onVariantInputChange: (value: string) => void;
  readonly onToggleEditMode: () => void;
  readonly onSetEditColor: (color: Side) => void;
  readonly onResetBoard: () => void;
  readonly onClearBoard: () => void;
  readonly onUndo: () => void;
  readonly onFinish: () => void;
};

const SECONDARY_BTN =
  "inline-flex h-10 items-center justify-center gap-2 rounded-md border border-[#4a443b] bg-[#25231f] px-3 text-sm font-semibold text-[#f6f1e8] transition-colors hover:border-[#6f6659] hover:bg-[#2f2c27] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d] disabled:pointer-events-none disabled:opacity-45";
const PRIMARY_BTN =
  "inline-flex h-11 items-center justify-center gap-2 rounded-md border border-[#58b383] bg-[#58b383] px-3 text-sm font-semibold text-[#101312] transition-colors hover:bg-[#7bd99d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d] disabled:pointer-events-none disabled:opacity-45";
const TOGGLE_ACTIVE = "border-[#58b383] bg-[#58b383] text-[#101312]";
const TOGGLE_INACTIVE = "border-[#4a443b] bg-[#25231f] text-[#f6f1e8]";

export function CreateSidePanel({
  state,
  lastMove,
  onSideChange,
  onVariantInputChange,
  onToggleEditMode,
  onSetEditColor,
  onResetBoard,
  onClearBoard,
  onUndo,
  onFinish,
}: CreateSidePanelProps) {
  const existing = variantNames(state.side);
  const turnLabel = state.turn === "white" ? "Aux blancs" : "Aux noirs";
  const lastMoveText = lastMove ? moveToProblemLine(lastMove) : "Aucun coup";
  const variantValid = isValidVariantName(state.variantInput);
  const canFinish = state.mode === "record" && variantValid && state.moves.length > 0;
  const finishTitle = !variantValid
    ? "Saisis un nom d'ouverture valide"
    : state.moves.length === 0
      ? "Joue au moins un coup"
      : state.mode !== "record"
        ? "Quitte le mode edition"
        : "";

  return (
    <aside className="flex w-full flex-col gap-5 rounded-lg border border-[#333029] bg-[#1b1b18]/94 p-5 shadow-xl shadow-black/20 lg:min-h-[620px] lg:w-[380px]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#58b383]">Creation</p>
          <h1 className="mt-2 text-2xl font-semibold text-[#f6f1e8]">Nouveau probleme</h1>
        </div>
        <StatusBadge kind={state.turn === "white" ? "neutral" : "warning"} label={turnLabel} />
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Cote</p>
        <div className="grid grid-cols-2 gap-2">
          {(["white", "black"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onSideChange(s)}
              className={`h-10 rounded-md border px-3 text-sm font-semibold transition-colors ${
                state.side === s ? TOGGLE_ACTIVE : TOGGLE_INACTIVE
              }`}
            >
              {sideLabel(s)}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-[#8f877a]">{orientationLabel(state.side)}</p>
      </div>

      <div>
        <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]" htmlFor="variant-input">
          Ouverture
        </label>
        <input
          id="variant-input"
          type="text"
          list="existing-variants"
          value={state.variantInput}
          onChange={(event) => onVariantInputChange(event.target.value)}
          placeholder="defense_francaise"
          className="w-full rounded-md border border-[#4a443b] bg-[#151512] px-3 py-2 text-sm text-[#f6f1e8] placeholder:text-[#5e574c] focus:border-[#58b383] focus:outline-none"
        />
        <datalist id="existing-variants">
          {existing.map((name) => (
            <option key={name} value={name} />
          ))}
        </datalist>
        <p className="mt-2 text-xs text-[#8f877a]">
          {existing.length} ouverture(s) {sideLabel(state.side)} existante(s). Saisis un nom existant pour ajouter une ligne, ou un nouveau nom.
        </p>
      </div>

      <div className="rounded-md border border-[#333029] bg-[#151512] p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Position de depart</p>
            <p className="mt-1 text-sm text-[#cfc5b8]">
              {state.mode === "edit" ? "Mode edition actif" : "Position figee"}
            </p>
          </div>
          <button
            type="button"
            onClick={onToggleEditMode}
            className={SECONDARY_BTN}
            disabled={state.mode === "record" && state.history.length > 0}
            title={state.history.length > 0 ? "Annule les coups avant de revenir en edition" : ""}
          >
            <Pencil size={15} aria-hidden="true" />
            {state.mode === "edit" ? "Terminer" : "Modifier"}
          </button>
        </div>

        {state.mode === "edit" ? (
          <div className="mt-3 grid gap-2">
            <div className="grid grid-cols-2 gap-2">
              {(["white", "black"] as const).map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => onSetEditColor(c)}
                  className={`h-9 rounded-md border px-3 text-xs font-semibold transition-colors ${
                    state.editColor === c ? TOGGLE_ACTIVE : TOGGLE_INACTIVE
                  }`}
                >
                  Pieces {sideLabel(c)}s
                </button>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button type="button" onClick={onResetBoard} className={SECONDARY_BTN}>
                <RotateCcw size={14} aria-hidden="true" />
                Standard
              </button>
              <button type="button" onClick={onClearBoard} className={SECONDARY_BTN}>
                <Eraser size={14} aria-hidden="true" />
                Vider
              </button>
            </div>
            <p className="text-xs text-[#8f877a]">
              Clique sur une case pour cycler : vide → pion → cavalier → fou → tour → dame → roi.
            </p>
          </div>
        ) : null}
      </div>

      <div className="rounded-md border border-[#333029] bg-[#151512] p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Coups enregistres</p>
        <p className="mt-2 font-mono text-sm text-[#f6f1e8]">{state.moves.length}</p>
        <p className="mt-3 text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Dernier coup</p>
        <p className="mt-1 break-words font-mono text-sm text-[#cfc5b8]">{lastMoveText}</p>
      </div>

      <div className="rounded-md border border-[#333029] bg-[#151512] p-3">
        <p className={`text-sm ${state.flashSquare ? "text-[#ffb4b4]" : "text-[#f6f1e8]"}`}>{state.statusText}</p>
      </div>

      <div className="mt-auto grid gap-3">
        <button
          type="button"
          onClick={onUndo}
          disabled={state.history.length === 0}
          className={SECONDARY_BTN}
        >
          <Undo2 size={15} aria-hidden="true" />
          Annuler dernier coup
        </button>
        <button
          type="button"
          onClick={onFinish}
          disabled={!canFinish}
          title={finishTitle}
          className={PRIMARY_BTN}
        >
          <CheckCircle2 size={16} aria-hidden="true" />
          Terminer
        </button>
        <Link
          href="/"
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-[#39352e] bg-transparent px-3 text-sm font-semibold text-[#d5cbbd] transition-colors hover:bg-[#24221e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
        >
          Menu
        </Link>
      </div>
    </aside>
  );
}
