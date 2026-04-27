"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Lightbulb, List, RefreshCw, RotateCcw, Undo2 } from "lucide-react";

import { moveToProblemLine } from "@/lib/board";
import { isFinished } from "@/lib/problemSession";
import { orientationLabel } from "@/lib/pieces";
import type { SessionState } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";

type SidePanelProps = {
  readonly state: SessionState;
  readonly onNewProblem: () => void;
  readonly onPrevious: () => void;
  readonly onSolution: () => void;
  readonly onRedo: () => void;
};

type PanelButtonProps = {
  readonly icon: LucideIcon;
  readonly children: string;
  readonly onClick?: () => void;
  readonly disabled?: boolean;
  readonly href?: string;
  readonly variant?: "primary" | "secondary" | "ghost";
};

function buttonClasses(variant: PanelButtonProps["variant"], disabled: boolean): string {
  const base =
    "inline-flex h-11 w-full items-center justify-center gap-2 rounded-md border px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]";
  const variants = {
    primary: "border-[#58b383] bg-[#58b383] text-[#101312] hover:bg-[#7bd99d]",
    secondary: "border-[#4a443b] bg-[#25231f] text-[#f6f1e8] hover:border-[#6f6659] hover:bg-[#2f2c27]",
    ghost: "border-[#39352e] bg-transparent text-[#d5cbbd] hover:bg-[#24221e]",
  };
  return `${base} ${variants[variant ?? "secondary"]} ${disabled ? "pointer-events-none opacity-45" : ""}`;
}

function PanelButton({ icon: Icon, children, onClick, disabled = false, href, variant = "secondary" }: PanelButtonProps) {
  const className = buttonClasses(variant, disabled);
  if (href) {
    return (
      <Link href={href} className={className} aria-disabled={disabled}>
        <Icon size={17} aria-hidden="true" />
        <span>{children}</span>
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} disabled={disabled} className={className}>
      <Icon size={17} aria-hidden="true" />
      <span>{children}</span>
    </button>
  );
}

export function SidePanel({ state, onNewProblem, onPrevious, onSolution, onRedo }: SidePanelProps) {
  const finished = isFinished(state);
  const variantsHref = `/train/${state.side}`;
  const lastMove = state.lastMove ? moveToProblemLine(state.lastMove) : "Aucun coup";

  return (
    <aside className="flex w-full flex-col rounded-lg border border-[#333029] bg-[#1b1b18]/94 p-5 shadow-xl shadow-black/20 lg:min-h-[620px] lg:w-[360px]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#58b383]">Mode probleme</p>
          <h1 className="mt-2 text-2xl font-semibold text-[#f6f1e8]">{state.variant}</h1>
        </div>
        <StatusBadge kind={finished ? "success" : state.statusKind} label={finished ? "GOOD" : "STATUT"} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <div className="rounded-md border border-[#333029] bg-[#22201c] p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Vue</p>
          <p className="mt-2 text-sm font-semibold text-[#f6f1e8]">{orientationLabel(state.side)}</p>
        </div>
        <div className="rounded-md border border-[#333029] bg-[#22201c] p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Progression</p>
          <p className="mt-2 font-mono text-sm text-[#f6f1e8]">
            {state.turnIndex}/{state.problem.moves.length}
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-md border border-[#333029] bg-[#151512] p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Dernier coup</p>
        <p className="mt-2 break-words font-mono text-sm text-[#cfc5b8]">{lastMove}</p>
      </div>

      <div className={`mt-4 rounded-md border p-4 ${finished ? "good-pop border-[#2f7f4d] bg-[#173a28]" : "border-[#333029] bg-[#151512]"}`}>
        <p className={`text-sm font-semibold ${state.statusKind === "danger" ? "text-[#ffb4b4]" : "text-[#f6f1e8]"}`}>
          {state.statusText}
        </p>
      </div>

      <div className="mt-auto grid grid-cols-2 gap-3 pt-6">
        <PanelButton icon={RefreshCw} onClick={onNewProblem} variant="primary">
          Nouveau
        </PanelButton>
        <PanelButton icon={Lightbulb} onClick={onSolution} disabled={finished}>
          Solution
        </PanelButton>
        <PanelButton icon={Undo2} onClick={onPrevious} disabled={state.history.length === 0}>
          Precedent
        </PanelButton>
        <PanelButton icon={RotateCcw} onClick={onRedo}>
          Refaire
        </PanelButton>
        <div className="col-span-2">
          <PanelButton icon={List} href={variantsHref} variant="ghost">
            Variantes
          </PanelButton>
        </div>
      </div>
    </aside>
  );
}
