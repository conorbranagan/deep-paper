import ResearchContainer from "@/components/ResearchContainer";
import React from "react";

export default async function PaperPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="min-h-screen bg-gray-50">
      <ResearchContainer initialTab={id} />
    </main>
  );
}
