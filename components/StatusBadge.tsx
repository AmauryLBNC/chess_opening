import type { StatusKind } from "@/lib/types";

type StatusBadgeProps = {
  readonly kind: StatusKind;
  readonly label: string;
};

const KIND_CLASSES: Record<StatusKind, string> = {
  neutral: "border-[#4b463d] bg-[#2a2823] text-[#e6ddd0]",
  danger: "border-[#7f3131] bg-[#3a1f1f] text-[#ffb4b4]",
  success: "border-[#2f7f4d] bg-[#173a28] text-[#a9f2bd]",
  warning: "border-[#86632d] bg-[#3a2c18] text-[#ffd794]",
};

export function StatusBadge({ kind, label }: StatusBadgeProps) {
  return (
    <div className={`inline-flex min-h-8 items-center rounded-md border px-3 py-1 text-sm font-semibold ${KIND_CLASSES[kind]}`}>
      {label}
    </div>
  );
}
