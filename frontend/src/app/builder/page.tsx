"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import SiteNav from "@/components/SiteNav";
import SiteFooter from "@/components/SiteFooter";
import { Project } from "@/lib/types";
import { listProjects, createProject, deleteProject } from "@/lib/api";
import ProjectCard from "@/components/ProjectCard";
import NewProjectDialog from "@/components/NewProjectDialog";
import { Button } from "@/components/ui/Button";
import { Search, Database } from "lucide-react";

export default function BuilderPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  const loadProjects = useCallback(async () => {
    try {
      const list = await listProjects();
      setProjects(list);
    } catch (e) {
      console.error("Failed to load projects:", e);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleCreate = async (name: string, description: string) => {
    try {
      const project = await createProject(name, description);
      setDialogOpen(false);
      router.push(`/projects/${project.id}`);
    } catch (e) {
      console.error("Failed to create project:", e);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Delete this project? This cannot be undone.")) return;
    try {
      await deleteProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      console.error("Failed to delete project:", e);
    }
  };

  const filtered = projects.filter((p) => {
    const q = search.toLowerCase();
    return (
      p.name.toLowerCase().includes(q) ||
      p.description.toLowerCase().includes(q) ||
      p.id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary">
      <SiteNav />
      <main className="py-12 md:py-16">
        <section className="page-shell max-w-5xl">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
            <div>
              <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-text-primary mb-2">
                Your backends
              </h1>
              <p className="text-text-secondary text-sm md:text-base max-w-xl">
                Every project here is a complete backend workspace the agent has
                created for you. Open one to chat, inspect the API, and iterate
                on the design.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1 min-w-[220px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search projects..."
                  className="w-full bg-bg-secondary border border-border rounded-full pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-accent"
                />
              </div>
              <Button
                variant="primary"
                size="md"
                className="whitespace-nowrap"
                type="button"
                onClick={() => setDialogOpen(true)}
              >
                New backend
              </Button>
            </div>
          </div>

          {loading ? (
            <div className="text-text-muted animate-pulse text-center py-12">
              Loading your backends...
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 bg-surface rounded-3xl border border-dashed border-border">
              <Database className="w-10 h-10 mx-auto mb-4 text-text-muted opacity-60" />
              <p className="text-text-secondary mb-4">
                {projects.length === 0
                  ? "You haven't created any backends yet."
                  : "No projects match your search."}
              </p>
              {projects.length === 0 && (
                <Button
                  variant="primary"
                  size="md"
                  type="button"
                  onClick={() => setDialogOpen(true)}
                >
                  Create your first backend
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onClick={() => router.push(`/projects/${project.id}`)}
                  onDelete={(e) => handleDelete(e, project.id)}
                />
              ))}
            </div>
          )}
        </section>
      </main>
      <NewProjectDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreate={handleCreate}
      />
      <SiteFooter />
    </div>
  );
}

