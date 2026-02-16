"use client";

import { useCallback, useState } from "react";
import { getFileTree, getFileContent } from "@/lib/api-client";
import type { FileNode } from "@/lib/types";

export function useFileTree(projectId: string) {
  const [tree, setTree] = useState<FileNode | null>(null);
  const [selectedFile, setSelectedFile] = useState<{
    path: string;
    content: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFileTree(projectId);
      setTree(data);
    } catch (err) {
      console.error("Failed to load file tree:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const openFile = useCallback(
    async (path: string) => {
      try {
        const data = await getFileContent(projectId, path);
        setSelectedFile({ path: data.path, content: data.content });
      } catch (err) {
        console.error("Failed to load file:", err);
      }
    },
    [projectId]
  );

  return { tree, selectedFile, loading, refresh, openFile, setSelectedFile };
}
