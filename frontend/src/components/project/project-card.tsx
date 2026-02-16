"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import type { Project } from "@/lib/types";

const statusColors: Record<string, string> = {
  idle: "bg-gray-100 text-gray-800",
  generating: "bg-blue-100 text-blue-800",
  running: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
};

export function ProjectCard({
  project,
  onDelete,
}: {
  project: Project;
  onDelete: (id: string) => void;
}) {
  return (
    <Card className="group hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <Link href={`/projects/${project.id}`} className="flex-1">
            <CardTitle className="text-lg hover:underline cursor-pointer">
              {project.name}
            </CardTitle>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8"
            onClick={(e) => {
              e.preventDefault();
              onDelete(project.id);
            }}
          >
            <Trash2 className="h-4 w-4 text-muted-foreground" />
          </Button>
        </div>
        <CardDescription>
          {project.description || "No description"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Badge
            variant="secondary"
            className={statusColors[project.status] || statusColors.idle}
          >
            {project.status}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {new Date(project.created_at).toLocaleDateString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
