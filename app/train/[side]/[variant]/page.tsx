import { notFound } from "next/navigation";

import { TrainingScreen } from "@/components/TrainingScreen";
import { getOpeningMetadata } from "@/lib/openings";
import { isSide, problems, SIDES, variantNames } from "@/lib/problemData";

export const dynamicParams = false;

export function generateStaticParams() {
  return SIDES.flatMap((side) => variantNames(side).map((variant) => ({ side, variant })));
}

type TrainingPageProps = {
  readonly params: Promise<{
    readonly side: string;
    readonly variant: string;
  }>;
};

export default async function TrainingPage({ params }: TrainingPageProps) {
  const { side: rawSide, variant: rawVariant } = await params;
  if (!isSide(rawSide)) {
    notFound();
  }

  const variant = decodeURIComponent(rawVariant);
  const variantProblems = problems[rawSide][variant];
  if (!variantProblems || variantProblems.length === 0) {
    notFound();
  }

  return <TrainingScreen side={rawSide} variant={variant} problems={variantProblems} opening={getOpeningMetadata(variant, rawSide)} />;
}
