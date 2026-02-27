"use client";

import SiteNav from "@/components/SiteNav";
import SiteFooter from "@/components/SiteFooter";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ArrowRight, Layout, Server, Lock } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-text-primary">
      <SiteNav />

      <main className="pb-16">
        {/* Hero Section */}
        <section className="pt-6 pb-12 md:pb-24">
          <div className="page-shell">
            <div className="bg-[#F4F4F4] rounded-[40px] px-6 py-16 md:py-28 text-center flex flex-col items-center relative overflow-hidden">
              <Badge className="mb-8" variant="soft">
                Mesora AI Research
              </Badge>
              <h1 className="text-4xl md:text-6xl lg:text-7xl font-semibold tracking-tight text-[#111] mb-6 max-w-4xl leading-[1.1]">
                Build robust backend APIs{" "}
                <br className="hidden md:block" />
                <span className="text-gray-400">without writing code.</span>
              </h1>
              <p className="text-lg md:text-xl text-gray-600 mb-10 max-w-2xl font-light">
                Describe what your application should do in plain English.
                Mesora&apos;s coding agents design, scaffold, and deploy a
                production-grade FastAPI + PostgreSQL backend for you.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button
                  variant="primary"
                  size="lg"
                  className="gap-2"
                  onClick={() => {
                    window.location.href = "/builder";
                  }}
                >
                  Start building free
                  <ArrowRight className="w-4 h-4" />
                </Button>
                <Button
                  variant="secondary"
                  size="lg"
                  type="button"
                  onClick={() => {
                    window.location.href = "/builder";
                  }}
                >
                  View your projects
                </Button>
              </div>

              {/* Abstract decoration */}
              <div className="absolute top-10 left-10 w-24 h-24 bg-white rounded-full mix-blend-overlay blur-2xl opacity-50" />
              <div className="absolute bottom-10 right-10 w-32 h-32 bg-[#D4F79A] rounded-full mix-blend-multiply blur-3xl opacity-20" />
            </div>
          </div>
        </section>

        {/* Logos Section */}
        <section className="py-12 border-y border-border bg-white">
          <div className="page-shell">
            <p className="text-center text-xs md:text-sm font-medium text-gray-400 mb-8 uppercase tracking-[0.2em]">
              Powered by modern web standards
            </p>
            <div className="flex flex-wrap justify-center items-center gap-12 md:gap-24 opacity-60 grayscale">
              <span className="text-xl font-bold tracking-tighter">
                RESTful
              </span>
              <span className="text-xl font-bold tracking-tighter">
                OpenAPI
              </span>
              <span className="text-xl font-bold tracking-tighter">
                FastAPI
              </span>
              <span className="text-xl font-bold tracking-tighter">
                PostgreSQL
              </span>
              <span className="text-xl font-bold tracking-tighter">
                Docker
              </span>
            </div>
          </div>
        </section>

        {/* Philosophy / Features Section */}
        <section className="py-20 md:py-24 bg-white">
          <div className="page-shell">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-gray-900 mb-4">
                Separation of concerns,
                <br />
                built in from day one.
              </h2>
              <p className="text-gray-600 max-w-2xl mx-auto text-lg">
                Design from the frontend and let Mesora generate a clean,
                well-defined API interface and backend infrastructure for your
                app.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {/* Feature Card 1 */}
              <div className="bg-[#FAFAFA] rounded-3xl p-8 border border-border hover:shadow-lg transition-shadow">
                <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center border border-border mb-6 shadow-sm">
                  <Layout className="text-gray-900 w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">
                  Independent frontends
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  Build your UI in React, Lovable, or any tool you love.
                  Connect to your Mesora backend via standard API protocols.
                </p>
              </div>

              {/* Feature Card 2 */}
              <div className="bg-[#D4F79A] rounded-3xl p-8 border border-[#c2eb7d] hover:shadow-lg transition-shadow">
                <div className="w-12 h-12 bg-white/60 rounded-2xl flex items-center justify-center mb-6 shadow-sm backdrop-blur-sm">
                  <Server className="text-gray-900 w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">
                  Agentic backends
                </h3>
                <p className="text-gray-900 leading-relaxed opacity-90">
                  Our coding agents perceive your requirements, plan the
                  architecture, and deploy a scalable, secure backend in
                  minutes.
                </p>
              </div>

              {/* Feature Card 3 */}
              <div className="bg-[#111111] rounded-3xl p-8 text-white hover:shadow-xl transition-shadow">
                <div className="w-12 h-12 bg-white/10 rounded-2xl flex items-center justify-center border border-white/10 mb-6">
                  <Lock className="text-white w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">
                  Secure by design
                </h3>
                <p className="text-gray-400 leading-relaxed">
                  Authentication, role-based access control, and validation
                  come baked in so you can focus on the experience, not
                  plumbing.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="py-20 md:py-24 bg-[#FAFAFA] border-t border-border">
          <div className="page-shell">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
              <div className="md:col-span-12 mb-4 md:mb-8">
                <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-gray-900">
                  The ReAct loop in action
                </h2>
              </div>

              <div className="md:col-span-8 bg-white p-8 md:p-10 rounded-[32px] border border-border shadow-sm flex flex-col justify-between">
                <div>
                  <Badge className="mb-4" variant="soft">
                    Perceive &amp; plan
                  </Badge>
                  <h3 className="text-2xl font-semibold mb-4">
                    Describe your data model
                  </h3>
                  <p className="text-gray-600 mb-8 max-w-md">
                    Tell Mesora what resources your application needs. The agent
                    reasons about your description and designs an optimal schema
                    and API surface.
                  </p>
                </div>
                <div className="bg-[#F8F9FA] rounded-2xl p-4 md:p-6 font-mono text-xs md:text-sm text-gray-600 border border-gray-100 text-left">
                  <span className="text-purple-600">type</span>{" "}
                  <span className="text-blue-600">User</span> {"{"}
                  <br />
                  &nbsp;&nbsp;id:{" "}
                  <span className="text-green-600">UUID</span>;
                  <br />
                  &nbsp;&nbsp;email:{" "}
                  <span className="text-green-600">String</span> @unique;
                  <br />
                  &nbsp;&nbsp;role:{" "}
                  <span className="text-green-600">Role</span> @default(USER);
                  <br />
                  {"}"}
                </div>
              </div>

              <div className="md:col-span-4 bg-white p-8 md:p-10 rounded-[32px] border border-border shadow-sm flex flex-col justify-between">
                <div>
                  <Badge className="mb-4" variant="soft">
                    Act
                  </Badge>
                  <h3 className="text-2xl font-semibold mb-4">
                    Instant deployment
                  </h3>
                  <p className="text-gray-600">
                    Code generation, tool use, and deployment steps run in
                    sequence while you watch the agent&apos;s progress.
                  </p>
                </div>
                <div className="mt-8 flex justify-center">
                  <div className="w-20 h-20 md:w-24 md:h-24 rounded-full border-8 border-gray-100 border-t-[#D4F79A] animate-spin" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* About teaser (full page at /about) */}
        <section className="py-20 md:py-24 bg-white">
          <div className="page-shell max-w-4xl">
            <Badge className="mb-6" variant="soft">
              About us
            </Badge>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-gray-900 mb-10 leading-[1.1]">
              Democratizing{" "}
              <span className="text-gray-400">intelligent computing.</span>
            </h2>
            <div className="grid md:grid-cols-2 gap-12 items-start">
              <div className="space-y-6 text-base md:text-lg text-gray-600 leading-relaxed font-light">
                <p>
                  <span className="text-gray-900 font-medium">Mesora</span> is
                  an AI research lab based in Ghana. We are obsessed with
                  coding agents and their potential to transform how software is
                  built.
                </p>
                <p>
                  Frontend tools have empowered non‑developers to build
                  beautiful interfaces, but the backend remains a barrier. We
                  want to remove that barrier without asking people to become
                  infrastructure experts.
                </p>
                <p>
                  Mesora lets you explain your app like you would to a teammate,
                  then turns that explanation into real, running infrastructure.
                </p>
              </div>
              <div className="bg-[#FAFAFA] p-8 md:p-10 rounded-[32px] border border-border">
                <h3 className="text-xl font-semibold mb-6 text-gray-900">
                  Our principles
                </h3>
                <ul className="space-y-5 text-sm md:text-base">
                  <li className="flex gap-3">
                    <div className="mt-1 h-2 w-2 rounded-full bg-black" />
                    <div>
                      <h4 className="font-semibold text-gray-900">
                        Separation of concerns
                      </h4>
                      <p className="text-gray-600 mt-1">
                        Frontends and backends stay independent, communicating
                        through clear API contracts.
                      </p>
                    </div>
                  </li>
                  <li className="flex gap-3">
                    <div className="mt-1 h-2 w-2 rounded-full bg-black" />
                    <div>
                      <h4 className="font-semibold text-gray-900">
                        Agentic architecture
                      </h4>
                      <p className="text-gray-600 mt-1">
                        We use the Perceive–Plan–Act loop to generate,
                        execute, and refine backend changes safely.
                      </p>
                    </div>
                  </li>
                  <li className="flex gap-3">
                    <div className="mt-1 h-2 w-2 rounded-full bg-black" />
                    <div>
                      <h4 className="font-semibold text-gray-900">
                        Human in the loop
                      </h4>
                      <p className="text-gray-600 mt-1">
                        You stay in control. The agent explains what it&apos;s
                        doing and asks before making impactful changes.
                      </p>
                    </div>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Team teaser (full page at /team) */}
        <section className="py-20 md:py-24 bg-[#FAFAFA]">
          <div className="page-shell max-w-6xl">
            <div className="text-center mb-16">
              <Badge className="mb-4" variant="soft">
                The lab
              </Badge>
              <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-gray-900 mb-4">
                Meet the researchers
              </h2>
              <p className="text-gray-500 max-w-2xl mx-auto text-base md:text-lg font-light">
                A small team of researchers and engineers in Ghana exploring the
                frontier of NLP and intelligent computing systems.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
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
              ].map((member) => (
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
                  <h3 className="text-lg font-semibold text-gray-900">
                    {member.name}
                  </h3>
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
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 md:py-24 bg-white">
          <div className="page-shell max-w-4xl text-center">
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight mb-6">
              Ready to build your backend?
            </h2>
            <p className="text-lg md:text-xl text-gray-500 mb-10 max-w-2xl mx-auto">
              Join the next generation of creators building full‑stack
              experiences without wrestling with servers, databases, and
              boilerplate.
            </p>
            <Button
              variant="primary"
              size="lg"
              onClick={() => {
                window.location.href = "/builder";
              }}
            >
              Start your project
            </Button>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
