import Link from "next/link";
import { notFound } from "next/navigation";

import { formatOpeningDetails, getOpeningsWithProblems } from "@/lib/openings";
import { isSide, SIDES } from "@/lib/problemData";
import { sideLabel } from "@/lib/pieces";

export const dynamicParams = false;

export function generateStaticParams() {
  return SIDES.map((side) => ({ side }));
}

type VariantListPageProps = {
  readonly params: Promise<{
    readonly side: string;
  }>;
};

export default async function VariantListPage({ params }: VariantListPageProps) {
  const { side: rawSide } = await params;
  if (!isSide(rawSide)) {
    notFound();
  }

  const openings = getOpeningsWithProblems(rawSide);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#58b383]">Entrainement {sideLabel(rawSide)}</p>
          <h1 className="mt-2 text-3xl font-semibold text-[#f6f1e8]">Variantes</h1>
        </div>
        <Link
          href="/"
          className="rounded-md border border-[#39352e] px-4 py-2 text-sm font-semibold text-[#d5cbbd] transition-colors hover:bg-[#24221e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
        >
          Menu
        </Link>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {openings.map((opening) => (
          <Link
            key={opening.folder}
            href={`/train/${rawSide}/${encodeURIComponent(opening.folder)}`}
            className="rounded-lg border border-[#333029] bg-[#1b1b18]/90 p-5 shadow-xl shadow-black/20 transition-colors hover:border-[#58b383] hover:bg-[#22201c] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#8f877a]">Ouverture</p>
            <div className="mt-3 flex items-center justify-between gap-4">
              <div className="min-w-0">
                <h2 className="text-xl font-semibold text-[#f6f1e8]">{opening.displayName}</h2>
                <p className="mt-2 text-sm text-[#cfc5b8]">{formatOpeningDetails(opening)}</p>
                <p className="mt-2 truncate font-mono text-xs text-[#8f877a]">
                  {opening.label ? `label: ${opening.label}` : `dossier: ${opening.folder}`}
                </p>
              </div>
              <span className="shrink-0 rounded-md border border-[#4b463d] bg-[#25231f] px-3 py-1 font-mono text-sm text-[#e6ddd0]">
                {opening.problemCount ?? 0}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
