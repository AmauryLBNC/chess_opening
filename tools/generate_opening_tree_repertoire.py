"""Genere un repertoire d'ouverture en arbre, dans un dossier unique.

Lit data/openings.json, ne garde que les lignes commencant par le premier coup
choisi, construit un arbre de prefixes, puis selectionne des lignes complètes
en respectant la regle :
- au tour du joueur entraine : un seul coup choisi (config explicite ou heuristique
  "le coup le plus joue dans le catalogue depuis cette position");
- au tour de l'adversaire : plusieurs reponses sont gardees (les plus populaires
  parmi les reponses classiques).

Chaque ligne devient un fichier .txt dans un dossier unique, par exemple :
    problemes/repertoire_blanc_e4/1.txt
    problemes/black/repertoire_noir_vs_e4/1.txt

Exemples :
    python tools/generate_opening_tree_repertoire.py --side white --first-move e4 --depth 8 --max-lines 50 --dry-run
    python tools/generate_opening_tree_repertoire.py --side white --first-move e4 --depth 8 --max-lines 50
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from generate_opening_problems import (
    Opening,
    board_to_project_rows,
    load_chess_module,
    load_openings,
    move_to_problem_line,
    parse_pgn_moves,
    parse_uci_moves,
    rotate_rows_180,
    side_root,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]


CLASSICAL_REPLIES_BY_FIRST_MOVE: dict[str, set[str]] = {
    "e2e4": {"e7e5", "c7c5", "c7c6", "e7e6", "d7d6", "d7d5", "g8f6", "g7g6"},
    "d2d4": {"d7d5", "g8f6", "f7f5", "e7e6", "c7c6", "g7g6", "d7d6"},
    "g1f3": {"d7d5", "g8f6", "c7c5", "g7g6", "f7f5", "e7e6"},
    "c2c4": {"e7e5", "c7c5", "g8f6", "e7e6", "g7g6", "c7c6"},
}


WHITE_PLAYER_CONFIG: dict[str, dict[tuple[str, ...], str]] = {
    "e2e4": {
        ("e2e4", "e7e5"): "g1f3",
        ("e2e4", "c7c5"): "g1f3",
        ("e2e4", "c7c6"): "d2d4",
        ("e2e4", "e7e6"): "d2d4",
        ("e2e4", "d7d6"): "d2d4",
        ("e2e4", "d7d5"): "e4d5",
        ("e2e4", "g8f6"): "e4e5",
        ("e2e4", "g7g6"): "d2d4",
    },
    "d2d4": {
        ("d2d4", "d7d5"): "c2c4",
        ("d2d4", "g8f6"): "c2c4",
        ("d2d4", "f7f5"): "g2g3",
        ("d2d4", "e7e6"): "c2c4",
        ("d2d4", "c7c6"): "c2c4",
        ("d2d4", "g7g6"): "c2c4",
        ("d2d4", "d7d6"): "c2c4",
    },
    "c2c4": {
        ("c2c4", "e7e5"): "b1c3",
        ("c2c4", "c7c5"): "g1f3",
        ("c2c4", "g8f6"): "b1c3",
        ("c2c4", "e7e6"): "g1f3",
        ("c2c4", "g7g6"): "g1f3",
        ("c2c4", "c7c6"): "e2e4",
    },
    "g1f3": {
        ("g1f3", "d7d5"): "d2d4",
        ("g1f3", "g8f6"): "c2c4",
        ("g1f3", "c7c5"): "c2c4",
        ("g1f3", "g7g6"): "d2d4",
        ("g1f3", "f7f5"): "d2d4",
    },
}


BLACK_PLAYER_CONFIG: dict[str, dict[tuple[str, ...], str]] = {
    "e2e4": {("e2e4",): "c7c5"},
    "d2d4": {("d2d4",): "g8f6"},
    "c2c4": {("c2c4",): "e7e5"},
    "g1f3": {("g1f3",): "d7d5"},
}


WEIRD_LABEL_SUBSTRINGS: tuple[str, ...] = (
    "barnes", "grob", "amar", "sodium", "kadas", "clemenz", "mieses",
    "ware", "polish_opening", "anderssens_opening", "hungarian_opening",
    "van_geet", "global_opening", "nimzo_larsen", "sokolsky", "basman",
    "durkin", "creepy", "amsterdam_attack", "valencia_opening",
    "saragossa_opening", "spike", "fools_mate",
    "tumbleweed", "patzer", "anti_borg", "venezolana",
    "kings_indian_attack_double_fianchetto",
)


@dataclass
class TreeNode:
    children: dict[str, "TreeNode"] = field(default_factory=dict)
    line_count: int = 0

    def child(self, move: str) -> "TreeNode":
        if move not in self.children:
            self.children[move] = TreeNode()
        return self.children[move]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate a tree-shaped opening repertoire.")
    p.add_argument("--side", choices=["white", "black"], required=True)
    p.add_argument("--first-move", required=True, help="SAN du premier coup, ex e4 d4 c4 Nf3")
    p.add_argument("--depth", type=int, default=8, help="profondeur max en demi-coups")
    p.add_argument("--max-lines", type=int, default=50)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--output-folder", default=None, help="nom du dossier cible (sinon auto)")
    p.add_argument("--min-branch-popularity", type=int, default=2)
    p.add_argument("--max-opponent-branches", type=int, default=4)
    p.add_argument("--prefer-mainlines", action="store_true", default=True)
    p.add_argument("--include-gambits", action="store_true")
    p.add_argument("--exclude-weird-lines", action="store_true", default=True)
    return p


def san_to_uci(chess: Any, san: str) -> str:
    board = chess.Board()
    return board.parse_san(san).uci()


def opening_uci(chess: Any, opening: Opening) -> list[str] | None:
    try:
        if opening.moves_uci:
            return [m.uci() for m in parse_uci_moves(chess, opening.moves_uci)]
        if opening.moves_pgn:
            return [m.uci() for m in parse_pgn_moves(chess, opening.moves_pgn)]
    except Exception:
        return None
    return None


def is_weird(opening: Opening) -> bool:
    label = (opening.label or "").lower()
    return any(token in label for token in WEIRD_LABEL_SUBSTRINGS)


def collect_lines(
    chess: Any,
    openings: list[Opening],
    first_uci: str,
    exclude_weird: bool,
    include_gambits: bool,
) -> list[list[str]]:
    seen: set[tuple[str, ...]] = set()
    lines: list[list[str]] = []
    for op in openings:
        if exclude_weird and is_weird(op):
            continue
        if not include_gambits and "gambit" in (op.label or "").lower():
            continue
        moves = opening_uci(chess, op)
        if not moves or moves[0] != first_uci:
            continue
        key = tuple(moves)
        if key in seen:
            continue
        seen.add(key)
        lines.append(moves)
    return lines


def build_tree(lines: list[list[str]]) -> TreeNode:
    root = TreeNode()
    for line in lines:
        node = root
        node.line_count += 1
        for mv in line:
            node = node.child(mv)
            node.line_count += 1
    return root


def player_to_move(side: str, ply: int) -> bool:
    return ply % 2 == (0 if side == "white" else 1)


def pick_player_move(
    sequence: tuple[str, ...],
    node: TreeNode,
    config: dict[tuple[str, ...], str],
) -> str | None:
    chosen = config.get(sequence)
    if chosen and chosen in node.children:
        return chosen
    if not node.children:
        return None
    items = sorted(node.children.items(), key=lambda kv: (-kv[1].line_count, kv[0]))
    return items[0][0]


def opponent_branches(
    node: TreeNode,
    ply: int,
    classical_replies: set[str],
    min_pop: int,
    max_branches: int,
) -> list[str]:
    classical = classical_replies if ply == 1 else None
    candidates: list[tuple[str, int]] = []
    for mv, child in node.children.items():
        if classical is not None and mv not in classical:
            continue
        if child.line_count < min_pop:
            continue
        candidates.append((mv, child.line_count))
    candidates.sort(key=lambda x: (-x[1], x[0]))
    return [mv for mv, _ in candidates[:max_branches]]


def collect_all_leaves(
    side: str,
    first_uci: str,
    root: TreeNode,
    depth: int,
    config: dict[tuple[str, ...], str],
    classical_replies: set[str],
    min_pop: int,
    max_branches: int,
) -> list[tuple[str, ...]]:
    leaves: list[tuple[str, ...]] = []

    def walk(sequence: tuple[str, ...], node: TreeNode) -> None:
        if len(sequence) >= depth:
            leaves.append(sequence)
            return
        ply = len(sequence)
        if ply == 0:
            if first_uci not in node.children:
                return
            walk((first_uci,), node.children[first_uci])
            return
        if player_to_move(side, ply):
            mv = pick_player_move(sequence, node, config)
            if mv is None or mv not in node.children:
                if len(sequence) >= 2:
                    leaves.append(sequence)
                return
            walk(sequence + (mv,), node.children[mv])
        else:
            moves = opponent_branches(node, ply, classical_replies, min_pop, max_branches)
            if not moves:
                if len(sequence) >= 2:
                    leaves.append(sequence)
                return
            for mv in moves:
                walk(sequence + (mv,), node.children[mv])

    walk((), root)
    return leaves


def select_balanced(leaves: list[tuple[str, ...]], max_lines: int) -> list[tuple[str, ...]]:
    buckets: dict[Any, list[tuple[str, ...]]] = defaultdict(list)
    for leaf in leaves:
        key = leaf[1] if len(leaf) >= 2 else None
        buckets[key].append(leaf)
    for k in buckets:
        buckets[k].sort(key=lambda s: (-len(s), s))
    selected: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    keys = list(buckets.keys())
    if not keys:
        return []
    while len(selected) < max_lines:
        progress = False
        for k in keys:
            if not buckets[k]:
                continue
            cand = buckets[k].pop(0)
            if cand in seen:
                continue
            seen.add(cand)
            selected.append(cand)
            progress = True
            if len(selected) >= max_lines:
                break
        if not progress:
            break
    return selected


def line_to_problem_text(chess: Any, side: str, line_uci: list[str]) -> str:
    move_objs = [chess.Move.from_uci(uci) for uci in line_uci]
    if side == "black":
        if len(move_objs) < 2:
            raise ValueError("ligne trop courte pour cote noir")
        initial = chess.Board()
        initial.push(move_objs[0])
        rows = board_to_project_rows(chess, initial)
        rows = rotate_rows_180(rows)
        problem_moves: list[str] = []
        trial = chess.Board()
        trial.push(move_objs[0])
        for mv in move_objs[1:]:
            problem_moves.append(move_to_problem_line(chess, trial, mv))
            trial.push(mv)
    else:
        initial = chess.Board()
        rows = board_to_project_rows(chess, initial)
        problem_moves = []
        trial = chess.Board()
        for mv in move_objs:
            problem_moves.append(move_to_problem_line(chess, trial, mv))
            trial.push(mv)
    board_text = "\n".join(" ".join(str(v) for v in row) for row in rows)
    moves_text = "\n".join(problem_moves)
    return f"{board_text}\n{moves_text}\n"


def folder_name(side: str, first_san: str, output_folder: str | None) -> str:
    if output_folder:
        return output_folder
    san = first_san.lower().replace("'", "").replace(" ", "_")
    if side == "white":
        return f"repertoire_blanc_{san}"
    return f"repertoire_noir_vs_{san}"


def existing_numeric_files(folder: Path) -> set[int]:
    if not folder.exists():
        return set()
    nums: set[int] = set()
    for path in folder.glob("*.txt"):
        if path.name == "Format.txt" or not path.stem.isdigit():
            continue
        nums.add(int(path.stem))
    return nums


def existing_sequences_text(folder: Path) -> set[tuple[str, ...]]:
    seqs: set[tuple[str, ...]] = set()
    if not folder.exists():
        return seqs
    for path in folder.glob("*.txt"):
        if path.name == "Format.txt" or not path.stem.isdigit():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) < 9:
            continue
        seqs.add(tuple(lines[8:]))
    return seqs


def write_format(folder: Path, count: int) -> None:
    fp = folder / "Format.txt"
    if fp.exists():
        lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            lines[0] = str(count)
        else:
            lines = [str(count)]
        fp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        fp.write_text(f"{count}\n", encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    chess = load_chess_module()

    try:
        first_uci = san_to_uci(chess, args.first_move)
    except Exception as exc:
        print(f"Erreur: premier coup invalide '{args.first_move}': {exc}", file=sys.stderr)
        return 1

    config_root = WHITE_PLAYER_CONFIG if args.side == "white" else BLACK_PLAYER_CONFIG
    config = config_root.get(first_uci, {})
    classical_replies = CLASSICAL_REPLIES_BY_FIRST_MOVE.get(first_uci, set())

    print("# Generation arbre de repertoire")
    print(f"Side : {args.side}")
    print(f"Premier coup : {args.first_move} ({first_uci})")
    print(f"Profondeur max : {args.depth} demi-coups")
    print(f"Max lignes : {args.max_lines}")
    print(f"Mode : {'dry-run' if args.dry_run else 'ecriture reelle'}")
    print(f"Min popularite branche adverse : {args.min_branch_popularity}")
    print(f"Max branches adverses par noeud : {args.max_opponent_branches}")
    print(f"Exclure lignes farfelues : {args.exclude_weird_lines}")
    print(f"Inclure gambits : {args.include_gambits}")
    print()

    openings = load_openings()
    lines = collect_lines(
        chess, openings, first_uci, args.exclude_weird_lines, args.include_gambits
    )
    print(f"Ouvertures lues : {len(openings)}")
    print(f"Lignes catalogue commencant par {args.first_move} : {len(lines)}")

    tree = build_tree(lines)
    leaves = collect_all_leaves(
        args.side, first_uci, tree, args.depth, config, classical_replies,
        args.min_branch_popularity, args.max_opponent_branches,
    )
    print(f"Lignes candidates apres elagage : {len(leaves)}")

    selected = select_balanced(leaves, args.max_lines)
    print(f"Lignes retenues : {len(selected)}")

    branches: dict[str, int] = defaultdict(int)
    for leaf in selected:
        if len(leaf) >= 2:
            branches[leaf[1]] += 1
    print()
    print("Branches principales (apres premier coup) :")
    for mv, count in sorted(branches.items(), key=lambda x: (-x[1], x[0])):
        print(f"- {mv} : {count} ligne(s)")

    target_folder_name = folder_name(args.side, args.first_move, args.output_folder)
    target_dir = side_root(args.side) / target_folder_name
    print()
    print(f"Dossier cible : {target_dir.relative_to(ROOT).as_posix()}")
    print(f"Existait deja : {target_dir.exists()}")

    existing_nums = existing_numeric_files(target_dir)
    existing_seqs = existing_sequences_text(target_dir)
    next_num = (max(existing_nums) + 1) if existing_nums else 1

    print()
    print("Fichiers prevus :")
    plans: list[tuple[Path, str, tuple[str, ...]]] = []
    skipped_dups = 0
    for leaf in selected:
        try:
            content = line_to_problem_text(chess, args.side, list(leaf))
        except Exception as exc:
            print(f"  [skip] {' '.join(leaf)}: {exc}")
            continue
        seq_lines = tuple(content.splitlines()[8:])
        if seq_lines in existing_seqs:
            skipped_dups += 1
            continue
        existing_seqs.add(seq_lines)
        target_file = target_dir / f"{next_num}.txt"
        plans.append((target_file, content, leaf))
        print(
            f"- {target_file.relative_to(ROOT).as_posix()}  "
            f"({len(leaf)} demi-coups)  {' '.join(leaf)}"
        )
        next_num += 1

    print()
    print(f"Doublons exacts ignores : {skipped_dups}")
    print(f"Nombre de fichiers a ecrire : {len(plans)}")

    if not args.dry_run and plans:
        target_dir.mkdir(parents=True, exist_ok=True)
        for path, content, _ in plans:
            path.write_text(content, encoding="utf-8")
        final_count = len(existing_numeric_files(target_dir))
        write_format(target_dir, final_count)
        print()
        print(f"Ecrit {len(plans)} fichier(s).")
        print(f"Format.txt mis a jour : {final_count} problemes au total.")

    print()
    print("Commandes suivantes :")
    print("python scripts/export_problems.py")
    print("npm test")
    print("npm run build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
