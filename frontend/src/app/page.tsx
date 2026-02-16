"use client";

import { useRouter } from "next/navigation";
import { useProjects } from "@/hooks/use-project";
import { ProjectCard } from "@/components/project/project-card";
import { CreateProjectDialog } from "@/components/project/create-project-dialog";
import { Skeleton } from "@/components/ui/skeleton";

export default function HomePage() {
  const { projects, loading, create, remove } = useProjects();
  const router = useRouter();

  const handleCreate = async (name: string, description: string) => {
    const project = await create(name, description);
    router.push(`/projects/${project.id}`);
    return project;
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">BackendForge</h1>
            <p className="text-sm text-muted-foreground">
              AI-powered backend API builder
            </p>
          </div>
          <CreateProjectDialog onCreate={handleCreate} />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[140px] rounded-xl" />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-20">
            <h2 className="text-lg font-medium text-muted-foreground">
              No projects yet
            </h2>
            <p className="text-sm text-muted-foreground mt-2">
              Create your first backend API project to get started.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onDelete={remove}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
