"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import ThemeToggle from "./ThemeToggle";
import { Button } from "./ui/Button";
import { Terminal } from "lucide-react";

export default function SiteNav() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    pathname === href ||
    (href !== "/" && pathname?.startsWith(href));

  return (
    <nav className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-border">
      <div className="page-shell">
        <div className="flex justify-between items-center h-20">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-2 cursor-pointer"
          >
            <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
              <Terminal className="w-4 h-4 text-[#D4F79A]" />
            </div>
            <span className="font-bold text-xl tracking-tight">
              Mesora.
            </span>
          </Link>

          {/* Desktop Links */}
          <div className="hidden md:flex items-center space-x-8">
            <Link
              href="/"
              className={`text-sm font-medium transition-colors ${
                isActive("/")
                  ? "text-text-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              Platform
            </Link>
            <Link
              href="/builder"
              className={`text-sm font-medium transition-colors ${
                isActive("/builder")
                  ? "text-text-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              Builder
            </Link>
            <Link
              href="/about"
              className={`text-sm font-medium transition-colors ${
                isActive("/about")
                  ? "text-text-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              About
            </Link>
            <Link
              href="/team"
              className={`text-sm font-medium transition-colors ${
                isActive("/team")
                  ? "text-text-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              Team
            </Link>
          </div>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center space-x-4">
            <button className="text-sm font-medium text-text-secondary hover:text-text-primary">
              Log in
            </button>
            <Link href="/builder">
              <Button variant="primary" size="sm">
                Get started
              </Button>
            </Link>
            <ThemeToggle />
          </div>

          {/* Mobile Actions */}
          <div className="md:hidden flex items-center gap-2">
            <ThemeToggle />
            <Link href="/builder">
              <Button variant="primary" size="sm">
                Start
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

