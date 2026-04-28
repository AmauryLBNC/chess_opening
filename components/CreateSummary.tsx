"use client";

import { useState } from "react";
import { Check, ClipboardCopy, Download, X } from "lucide-react";

import { copyTextToClipboard, downloadTextFile } from "@/lib/download";
import { sideLabel } from "@/lib/pieces";
import type { Side } from "@/lib/types";

type CreateSummaryProps = {
  readonly side: Side;
  readonly variantNormalized: string;
  readonly variantRaw: string;
  readonly movesCount: number;
  readonly fileContent: string;
  readonly suggestedFileName: string;
  readonly onClose: () => void;
};

export function CreateSummary({
  side,
  variantNormalized,
  variantRaw,
  movesCount,
  fileContent,
  suggestedFileName,
  onClose,
}: CreateSummaryProps) {
  const [copied, setCopied] = useState(false);
  const folder = side === "white" ? `problemes/${variantNormalized}/` : `problemes/black/${variantNormalized}/`;

  const handleCopy = async () => {
    const ok = await copyTextToClipboard(fileContent);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const handleDownload = () => {
    downloadTextFile(suggestedFileName, fileContent);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 py-6">
      <div className="relative w-full max-w-2xl rounded-lg border border-[#333029] bg-[#1b1b18] p-6 shadow-2xl shadow-black/50">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 rounded-md p-2 text-[#8f877a] hover:bg-[#24221e] hover:text-[#f6f1e8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
          aria-label="Fermer"
        >
          <X size={18} aria-hidden="true" />
        </button>

        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#58b383]">Recap</p>
        <h2 className="mt-2 text-2xl font-semibold text-[#f6f1e8]">Probleme pret a etre exporte</h2>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-[#333029] bg-[#151512] p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Cote</p>
            <p className="mt-1 text-sm font-semibold text-[#f6f1e8]">{sideLabel(side)}</p>
          </div>
          <div className="rounded-md border border-[#333029] bg-[#151512] p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Ouverture</p>
            <p className="mt-1 break-words font-mono text-sm text-[#f6f1e8]">{variantNormalized}</p>
            {variantRaw !== variantNormalized ? (
              <p className="mt-1 text-xs text-[#8f877a]">Saisi : {variantRaw}</p>
            ) : null}
          </div>
          <div className="rounded-md border border-[#333029] bg-[#151512] p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Coups</p>
            <p className="mt-1 font-mono text-sm text-[#f6f1e8]">{movesCount}</p>
          </div>
        </div>

        <div className="mt-4 rounded-md border border-[#333029] bg-[#0f0f0d] p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8f877a]">Apercu du fichier</p>
          <pre className="mt-2 max-h-60 overflow-auto whitespace-pre font-mono text-xs leading-relaxed text-[#cfc5b8]">
            {fileContent}
          </pre>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={handleDownload}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-[#58b383] bg-[#58b383] px-3 text-sm font-semibold text-[#101312] transition-colors hover:bg-[#7bd99d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
          >
            <Download size={16} aria-hidden="true" />
            Telecharger {suggestedFileName}
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-[#4a443b] bg-[#25231f] px-3 text-sm font-semibold text-[#f6f1e8] transition-colors hover:border-[#6f6659] hover:bg-[#2f2c27] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
          >
            {copied ? <Check size={16} aria-hidden="true" /> : <ClipboardCopy size={16} aria-hidden="true" />}
            {copied ? "Copie !" : "Copier le contenu"}
          </button>
        </div>

        <div className="mt-5 rounded-md border border-[#2f7f4d] bg-[#173a28] p-4 text-sm text-[#cfeedd]">
          <p className="font-semibold text-[#a9f2bd]">Pour integrer ce probleme au repo :</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            <li>
              Place ce fichier dans <span className="font-mono">{folder}</span> en lui donnant le numero suivant
              (ex: <span className="font-mono">{`${folder}3.txt`}</span>).
            </li>
            <li>
              Incremente la premiere ligne de <span className="font-mono">{folder}Format.txt</span>.
            </li>
            <li>
              Relance <span className="font-mono">python scripts/export_problems.py</span>.
            </li>
            <li>Commit et push : Vercel redeploiera automatiquement.</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
