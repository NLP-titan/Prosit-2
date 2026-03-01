"use client";

import SiteNav from "@/components/SiteNav";
import SiteFooter from "@/components/SiteFooter";
import { Badge } from "@/components/ui/Badge";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white text-text-primary">
      <SiteNav />
      <main className="py-12 md:py-20">
        <section className="page-shell max-w-4xl">
          <Badge className="mb-6" variant="soft">
            About us
          </Badge>
          <h1 className="text-3xl md:text-5xl font-semibold tracking-tight text-gray-900 mb-10 leading-[1.1]">
            Democratizing{" "}
            <span className="text-gray-400">intelligent computing.</span>
          </h1>
          <div className="grid md:grid-cols-2 gap-12 items-start">
            <div className="space-y-6 text-base md:text-lg text-gray-600 leading-relaxed font-light">
              <p>
                <span className="text-gray-900 font-medium">Kruya-Jenjen</span> is an
                AI research lab based in Ghana. We are obsessed with coding
                agents and their potential to transform how software is built.
              </p>
              <p>
                Frontend tools have empowered non‑developers to build beautiful
                interfaces, but the backend remains a barrier. We want to remove
                that barrier without asking people to become infrastructure
                experts.
              </p>
              <p>
                Kruya-Jenjen lets you explain your app like you would to a teammate,
                then turns that explanation into real, running infrastructure.
              </p>
            </div>
            <div className="bg-[#FAFAFA] p-8 md:p-10 rounded-[32px] border border-border">
              <h2 className="text-xl font-semibold mb-6 text-gray-900">
                Our principles
              </h2>
              <ul className="space-y-5 text-sm md:text-base">
                <li className="flex gap-3">
                  <div className="mt-1 h-2 w-2 rounded-full bg-black" />
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      Separation of concerns
                    </h3>
                    <p className="text-gray-600 mt-1">
                      Frontends and backends stay independent, communicating
                      through clear API contracts.
                    </p>
                  </div>
                </li>
                <li className="flex gap-3">
                  <div className="mt-1 h-2 w-2 rounded-full bg-black" />
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      Agentic architecture
                    </h3>
                    <p className="text-gray-600 mt-1">
                      We use the Perceive–Plan–Act loop to generate, execute,
                      and refine backend changes safely.
                    </p>
                  </div>
                </li>
                <li className="flex gap-3">
                  <div className="mt-1 h-2 w-2 rounded-full bg-black" />
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      Human in the loop
                    </h3>
                    <p className="text-gray-600 mt-1">
                      You stay in control. The agent explains what it&apos;s
                      doing and asks before making impactful changes.
                    </p>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

