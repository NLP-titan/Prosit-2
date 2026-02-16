"use client";

import { use } from "react";
import { WorkspaceLayout } from "@/components/workspace/workspace-layout";

export default function ProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  return <WorkspaceLayout projectId={projectId} />;
}
