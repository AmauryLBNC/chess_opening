import { pieceImagePath, pieceLabel } from "@/lib/pieces";

type PieceProps = {
  readonly piece: number;
};

export function Piece({ piece }: PieceProps) {
  const src = pieceImagePath(piece);
  if (!src) {
    return null;
  }

  return (
    <img
      src={src}
      alt={pieceLabel(piece)}
      width={80}
      height={80}
      loading="eager"
      decoding="async"
      draggable={false}
      className="piece-image h-[78%] w-[78%] select-none object-contain transition-transform duration-150 ease-out group-hover:scale-[1.04]"
    />
  );
}
