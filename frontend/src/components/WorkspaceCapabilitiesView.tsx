"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { getCapabilitiesPreview } from "@/lib/api";

interface Props {
  projectId: string;
  swaggerUrl: string | null;
}

type HttpMethod = "get" | "post" | "put" | "patch" | "delete";

interface CapabilityGroup {
  name: string;
  items: string[];
}

function toTitle(str: string) {
  return str
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\w\S*/g, (w) => w[0].toUpperCase() + w.slice(1).toLowerCase());
}

function resourceFromPath(path: string) {
  const parts = path.split("/").filter(Boolean);
  return parts[0] || "general";
}

function describeEndpoint(method: HttpMethod, path: string): string {
  const resource = resourceFromPath(path).replace(/\{.*?\}/g, "").toLowerCase();
  const resourceTitle = toTitle(resource || "resource");

  switch (method) {
    case "get":
      if (path.endsWith("}")) {
        return `Get details for a single ${resourceTitle}`;
      }
      return `Get a list of all ${resourceTitle}`;
    case "post":
      return `Create a new ${resourceTitle}`;
    case "put":
    case "patch":
      return `Update an existing ${resourceTitle}`;
    case "delete":
      return `Delete a ${resourceTitle}`;
    default:
      return `Custom operation on ${resourceTitle}`;
  }
}

export default function WorkspaceCapabilitiesView({ projectId, swaggerUrl }: Props) {
  const [groups, setGroups] = useState<CapabilityGroup[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchSpec = async () => {
      setLoading(true);
      setError(null);
      try {
        if (swaggerUrl) {
          const openApiUrl = swaggerUrl.replace(/\/docs\/?$/, "/openapi.json");
          const res = await fetch(openApiUrl);
          if (!res.ok) throw new Error("Failed to load OpenAPI spec");
          const spec = await res.json();
          const paths: Record<
            string,
            Partial<Record<HttpMethod, unknown>>
          > = spec.paths || {};

          const byGroup = new Map<string, string[]>();

          Object.entries(paths).forEach(([path, methods]) => {
            (["get", "post", "put", "patch", "delete"] as HttpMethod[]).forEach(
              (m) => {
                if (methods[m]) {
                  const groupKey = resourceFromPath(path);
                  const label = describeEndpoint(m, path);
                  const existing = byGroup.get(groupKey) || [];
                  existing.push(label);
                  byGroup.set(groupKey, existing);
                }
              }
            );
          });

          const result: CapabilityGroup[] = Array.from(byGroup.entries()).map(
            ([key, items]) => ({
              name: toTitle(key),
              items,
            })
          );

          if (!cancelled) setGroups(result);
          return;
        }

        if (projectId) {
          const preview = await getCapabilitiesPreview(projectId);
          const result: CapabilityGroup[] = (preview.groups || []).map(
            (g) => ({
              name: g.name,
              items: g.items,
            })
          );
          if (!cancelled) setGroups(result);
          return;
        }

        if (!cancelled) {
          setGroups(null);
        }
      } catch (e) {
        if (!cancelled) setError("We couldn't read the API description yet.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchSpec();
    return () => {
      cancelled = true;
    };
  }, [projectId, swaggerUrl]);

  if (!swaggerUrl && !groups && !loading && !error) {
    return (
      <div className="text-xs text-text-muted">
        When the agent finishes wiring your API, we&apos;ll list what it can do
        here in plain English.
      </div>
    );
  }

  if (loading && !groups) {
    return (
      <div className="text-xs text-text-muted animate-pulse">
        Discovering your app&apos;s capabilities…
      </div>
    );
  }

  if (error || !groups || groups.length === 0) {
    return (
      <div className="text-xs text-text-muted">
        {error || "No capabilities detected yet."}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <div
          key={group.name}
          className="bg-[#FAFAFA] border border-border rounded-2xl p-4"
        >
          <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-black" />
            {group.name}
          </h3>
          <div className="space-y-2">
            {group.items.map((item, idx) => (
              <div
                key={`${group.name}-${idx}`}
                className="flex items-center gap-3 px-3 py-2 rounded-xl bg-white border border-gray-100"
              >
                <div className="w-7 h-7 rounded-full bg-[#E8FBE6] flex items-center justify-center text-green-600 shrink-0">
                  <Check className="w-3.5 h-3.5" />
                </div>
                <span className="text-xs font-medium text-gray-700">
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

