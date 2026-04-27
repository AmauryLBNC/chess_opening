import type { ReactNode } from "react";

import type { Coord } from "@/lib/types";
import { coordToAlgebraic } from "@/lib/board";

type SquareProps = {
  readonly coord: Coord;
  readonly isLight: boolean;
  readonly isSelected: boolean;
  readonly isLegalTarget: boolean;
  readonly isLastMove: boolean;
  readonly isFlash: boolean;
  readonly onSelect: (coord: Coord) => void;
  readonly children: ReactNode;
};

export function Square({
  coord,
  isLight,
  isSelected,
  isLegalTarget,
  isLastMove,
  isFlash,
  onSelect,
  children,
}: SquareProps) {
  const background = isLight ? "bg-[#edd9b4]" : "bg-[#af8861]";

  return (
    <button
      type="button"
      aria-label={coordToAlgebraic(coord)}
      onClick={() => onSelect(coord)}
      className={[
        "group relative flex aspect-square items-center justify-center overflow-hidden border-0 p-0 outline-none",
        "transition-[box-shadow,filter] duration-150 focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-[#7bd99d]",
        background,
        isSelected ? "z-10 ring-4 ring-inset ring-[#f1d66a]" : "",
        isLastMove ? "after:absolute after:inset-0 after:bg-[#f1d66a]/25" : "",
        isFlash ? "false-move-flash" : "",
      ].join(" ")}
    >
      {isLegalTarget ? (
        <span className="pointer-events-none absolute h-[24%] w-[24%] rounded-full bg-[#2f7f4d]/70 shadow-[0_0_0_7px_rgba(47,127,77,0.16)]" />
      ) : null}
      <span className="relative z-[1] flex h-full w-full items-center justify-center">{children}</span>
    </button>
  );
}
