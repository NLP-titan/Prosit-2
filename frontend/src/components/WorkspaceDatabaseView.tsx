"use client";

import { useEffect, useState } from "react";
import { Database } from "lucide-react";
import { Badge } from "./ui/Badge";
import { getDatabasePreview } from "@/lib/api";

interface Props {
  projectId: string;
  swaggerUrl: string | null;
}

type OpenApiSchema = {
  type?: string;
  format?: string;
  properties?: Record<string, OpenApiSchema>;
  items?: OpenApiSchema;
};

interface ModelField {
  name: string;
  typeLabel: string;
}

interface ModelCard {
  name: string;
  description: string;
  fields: ModelField[];
}

function toTitleCase(str: string) {
  return str
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\w\S*/g, (w) => w[0].toUpperCase() + w.slice(1).toLowerCase());
}

function friendlyType(name: string, schema: OpenApiSchema): string {
  if (schema.type === "string" && schema.format === "email") return "Email";
  if (schema.type === "string" && schema.format === "date-time")
    return "Date/Time";
  if (schema.type === "string") {
    return name.toLowerCase().includes("name") ? "Text" : "Short Text";
  }
  if (schema.type === "boolean") return "Yes/No";
  if (schema.type === "integer" || schema.type === "number") return "Number";
  if (schema.type === "array") return "List";
  return "Text";
}

export default function WorkspaceDatabaseView({ projectId, swaggerUrl }: Props) {
  const [models, setModels] = useState<ModelCard[] | null>(null);
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
          const schemas: Record<string, OpenApiSchema> =
            spec.components?.schemas || {};

          const nextModels: ModelCard[] = Object.entries(schemas).map(
            ([name, schema]) => {
              const props = schema.properties || {};
              const fields: ModelField[] = Object.entries(props).map(
                ([fieldName, fieldSchema]) => ({
                  name: toTitleCase(fieldName),
                  typeLabel: friendlyType(fieldName, fieldSchema),
                })
              );

              return {
                name,
                description: `Information about ${toTitleCase(name)}.`,
                fields,
              };
            }
          );

          if (!cancelled) {
            setModels(nextModels);
          }
          return;
        }

        if (projectId) {
          const preview = await getDatabasePreview(projectId);
          const nextModels: ModelCard[] = (preview.models || []).map((m) => ({
            name: m.name,
            description: m.description,
            fields: (m.fields || []).map((f) => ({
              name: toTitleCase(f.name),
              typeLabel: f.typeLabel,
            })),
          }));

          if (!cancelled) {
            setModels(nextModels);
          }
          return;
        }

        if (!cancelled) {
          setModels(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError("We couldn't read the API description yet.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchSpec();
    return () => {
      cancelled = true;
    };
  }, [projectId, swaggerUrl]);

  if (!swaggerUrl && !models && !loading && !error) {
    return (
      <div className="text-xs text-text-muted">
        The agent hasn&apos;t finished setting up your API yet. Once it does,
        we&apos;ll show a simple picture of your data here.
      </div>
    );
  }

  if (loading && !models) {
    return (
      <div className="text-xs text-text-muted animate-pulse">
        Reading your API description…
      </div>
    );
  }

  if (error || !models || models.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-text-muted text-xs bg-[#FAFAFA] border border-dashed border-border rounded-2xl py-6">
        <Database className="w-8 h-8 mb-3 opacity-40" />
        <p>{error || "No data models detected yet."}</p>
      </div>
    );
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {models.map((model) => (
        <div
          key={model.name}
          className="bg-white border border-border rounded-2xl overflow-hidden"
        >
          <div className="p-4 border-b border-border bg-gradient-to-b from-gray-50 to-white flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-[#D4F79A] flex items-center justify-center">
              <Database className="w-4 h-4 text-black" />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900">
                {toTitleCase(model.name)}
              </div>
              <p className="text-[11px] text-gray-500">
                {model.description}
              </p>
            </div>
          </div>
          <div className="p-3 space-y-1">
            {model.fields.map((field) => (
              <div
                key={field.name}
                className="flex items-center justify-between px-2 py-1.5 rounded-xl hover:bg-[#F8F9FA]"
              >
                <span className="text-xs font-medium text-gray-700">
                  {field.name}
                </span>
                <Badge
                  variant="soft"
                  className="bg-gray-100 border-none text-[10px] font-medium normal-case tracking-normal shadow-none"
                >
                  {field.typeLabel}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

