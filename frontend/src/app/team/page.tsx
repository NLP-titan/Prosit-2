"use client";

import SiteNav from "@/components/SiteNav";
import SiteFooter from "@/components/SiteFooter";
import { Badge } from "@/components/ui/Badge";

const TEAM = [
  {
    name: "Kofi Mensah",
    role: "Lead AI researcher",
    focus: "LLM alignment & agentic systems",
  },
  {
    name: "Ama Osei",
    role: "Systems architect",
    focus: "Multi‑agent systems & orchestration",
  },
  {
    name: "Kwame Addo",
    role: "Product engineer",
    focus: "Human‑in‑the‑loop interfaces",
  },
  {
    name: "Nana Yaa",
    role: "Security researcher",
    focus: "Privacy & model context protocol",
  },
];

export default function TeamPage() {
  return (
    <div className="min-h-screen bg-white text-text-primary">
      <SiteNav />
      <main className="py-12 md:py-20 bg-[#FAFAFA]">
        <section className="page-shell max-w-6xl">
          <div className="text-center mb-16">
            <Badge className="mb-4" variant="soft">
              The lab
            </Badge>
            <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-gray-900 mb-4">
              Meet the researchers
            </h1>
            <p className="text-gray-500 max-w-2xl mx-auto text-base md:text-lg font-light">
              A small team of researchers and engineers in Ghana exploring the
              frontier of NLP and intelligent computing systems.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {TEAM.map((member) => (
              <div
                key={member.name}
                className="bg-white group rounded-[32px] p-6 border border-border hover:border-gray-300 hover:shadow-xl transition-all duration-300"
              >
                <div className="w-full aspect-square bg-[#FAFAFA] rounded-[24px] mb-6 overflow-hidden relative">
                  <div className="absolute inset-0 flex items-center justify-center opacity-20 group-hover:opacity-40 transition-opacity group-hover:scale-110 duration-500">
                    <div className="w-32 h-32 rounded-full border-[16px] border-[#D4F79A]" />
                    <div className="absolute w-16 h-16 bg-black rounded-full mix-blend-overlay" />
                  </div>
                </div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {member.name}
                </h2>
                <p className="text-xs font-medium text-gray-500 mt-1 mb-3">
                  {member.role}
                </p>
                <div className="pt-3 border-t border-gray-100">
                  <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">
                    Focus area
                  </p>
                  <p className="text-sm text-gray-700 mt-1">{member.focus}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

