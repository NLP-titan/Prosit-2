"use client";

import { Rocket, ExternalLink } from "lucide-react";

interface Props {
  swaggerUrl: string;
  apiUrl: string;
}

export default function BuildSummary({ swaggerUrl, apiUrl }: Props) {
  return (
    <div className="mx-4 my-3 border border-emerald-800 bg-emerald-950/50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Rocket className="w-5 h-5 text-emerald-400" />
        <h3 className="font-semibold text-emerald-300">Build Complete</h3>
      </div>

      <p className="text-sm text-text-secondary mb-3">
        Your API is up and running. Here&apos;s how to test it:
      </p>

      <div className="space-y-2 mb-3">
        {swaggerUrl && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted w-20 shrink-0">Swagger UI</span>
            <a
              href={swaggerUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent hover:opacity-80 underline flex items-center gap-1"
            >
              {swaggerUrl}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
        {apiUrl && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted w-20 shrink-0">API Base</span>
            <a
              href={apiUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent hover:opacity-80 underline flex items-center gap-1"
            >
              {apiUrl}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </div>

      <div className="text-xs text-text-secondary bg-bg-secondary/50 rounded p-2.5 space-y-1">
        <p className="font-medium text-text-primary mb-1">Quick start:</p>
        <p>1. Open the Swagger UI link above to explore and test all endpoints</p>
        <p>2. Use the &quot;Try it out&quot; button on any endpoint to send requests</p>
        <p>3. You can also use curl or any HTTP client with the API base URL</p>
        <p>4. Ask me if you want to modify the API or add new features</p>
      </div>
    </div>
  );
}
