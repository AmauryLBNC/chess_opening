import Link from "next/link";

import { problemCount } from "@/lib/problemData";

const MODES = [
  {
    href: "/train/white",
    title: "Entrainement blanc",
    label: "Vue blanche",
    count: problemCount("white"),
  },
  {
    href: "/train/black",
    title: "Entrainement noir",
    label: "Vue noire",
    count: problemCount("black"),
  },
] as const;

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center px-4 py-10 sm:px-6">
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#58b383]">Echiquier</p>
        <h1 className="mt-2 text-3xl font-semibold text-[#f6f1e8] sm:text-5xl">Mode entrainement</h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {MODES.map((mode) => (
          <Link
            key={mode.href}
            href={mode.href}
            className="rounded-lg border border-[#333029] bg-[#1b1b18]/90 p-6 shadow-xl shadow-black/20 transition-colors hover:border-[#58b383] hover:bg-[#22201c] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8f877a]">{mode.label}</p>
                <h2 className="mt-3 text-2xl font-semibold text-[#f6f1e8]">{mode.title}</h2>
              </div>
              <span className="rounded-md border border-[#2f7f4d] bg-[#173a28] px-3 py-1 font-mono text-sm text-[#a9f2bd]">
                {mode.count}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
