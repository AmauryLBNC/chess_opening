"use client";

import Link from "next/link";
import { useState } from "react";

import { CreateSidePanel } from "@/components/CreateSidePanel";
import { CreateSummary } from "@/components/CreateSummary";
import { MoveRecorder } from "@/components/MoveRecorder";
import { PositionEditor } from "@/components/PositionEditor";
import { useCreateSession } from "@/hooks/useCreateSession";
import { serializeProblem } from "@/lib/problemSerializer";
import { normalizeVariantName } from "@/lib/variantName";

export default function CreatePage() {
  const session = useCreateSession();
  const [summaryOpen, setSummaryOpen] = useState(false);

  const variantNormalized = normalizeVariantName(session.state.variantInput);
  const fileContent = serializeProblem(session.state.initialBoard, session.state.moves);
  const suggestedFileName = `${variantNormalized || "nouveau_probleme"}.txt`;

  const handleFinish = () => {
    if (variantNormalized.length === 0 || session.state.moves.length === 0) {
      return;
    }
    setSummaryOpen(true);
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-5 sm:px-6 lg:px-8">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#58b383]">Creation</p>
          <h1 className="mt-1 text-2xl font-semibold text-[#f6f1e8] sm:text-3xl">Nouveau probleme</h1>
        </div>
        <Link
          href="/"
          className="rounded-md border border-[#39352e] px-4 py-2 text-sm font-semibold text-[#d5cbbd] transition-colors hover:bg-[#24221e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
        >
          Menu
        </Link>
      </header>

      <div className="flex flex-1 flex-col items-center gap-5 lg:flex-row lg:items-start lg:justify-center">
        {session.state.mode === "edit" ? (
          <PositionEditor
            board={session.state.board}
            orientation={session.state.side}
            flashSquare={session.state.flashSquare}
            onSquareClick={session.handleSquareClick}
          />
        ) : (
          <MoveRecorder
            board={session.state.board}
            orientation={session.state.side}
            selected={session.state.selected}
            lastMove={session.lastMove}
            flashSquare={session.state.flashSquare}
            onSquareClick={session.handleSquareClick}
          />
        )}

        <CreateSidePanel
          state={session.state}
          lastMove={session.lastMove}
          onSideChange={session.setSide}
          onVariantInputChange={session.setVariantInput}
          onToggleEditMode={session.toggleEditMode}
          onSetEditColor={session.setEditColor}
          onResetBoard={session.resetBoardToStandard}
          onClearBoard={session.clearBoard}
          onUndo={session.undoLastMove}
          onFinish={handleFinish}
        />
      </div>

      {summaryOpen ? (
        <CreateSummary
          side={session.state.side}
          variantNormalized={variantNormalized}
          variantRaw={session.state.variantInput}
          movesCount={session.state.moves.length}
          fileContent={fileContent}
          suggestedFileName={suggestedFileName}
          onClose={() => setSummaryOpen(false)}
        />
      ) : null}
    </main>
  );
}
