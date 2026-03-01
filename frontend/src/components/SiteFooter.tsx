"use client";

import Link from "next/link";
import { Terminal, Github, Twitter, Linkedin } from "lucide-react";

export default function SiteFooter() {
  return (
    <footer className="bg-black text-white py-14 md:py-16 mt-4">
      <div className="page-shell max-w-6xl grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-12">
        <div className="col-span-1 md:col-span-2">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
              <Terminal className="w-4 h-4 text-black" />
            </div>
            <span className="font-bold text-xl tracking-tight">
              Kruya-Jenjen.
            </span>
          </div>
          <p className="text-gray-400 max-w-xs font-light text-sm">
            Building the future of API infrastructure through natural
            language and intelligent agents. Based in Ghana.
          </p>
          <div className="flex gap-4 mt-6 text-gray-400">
            <Github className="hover:text-white cursor-pointer transition-colors w-5 h-5" />
            <Twitter className="hover:text-white cursor-pointer transition-colors w-5 h-5" />
            <Linkedin className="hover:text-white cursor-pointer transition-colors w-5 h-5" />
          </div>
        </div>

        <div>
          <h4 className="font-semibold mb-4 uppercase text-[11px] tracking-[0.2em] text-gray-500">
            Product
          </h4>
          <ul className="space-y-3 text-gray-300 font-light text-sm">
            <li>
              <Link
                href="/"
                className="hover:text-white transition-colors"
              >
                Features
              </Link>
            </li>
            <li>
              <a
                href="https://github.com/NLP-titan/Prosit-2"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-white transition-colors"
              >
                Documentation
              </a>
            </li>
            <li>
              <a
                href="#"
                className="hover:text-white transition-colors"
              >
                Integrations
              </a>
            </li>
            <li>
              <a
                href="#"
                className="hover:text-white transition-colors"
              >
                Pricing
              </a>
            </li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold mb-4 uppercase text-[11px] tracking-[0.2em] text-gray-500">
            Company
          </h4>
          <ul className="space-y-3 text-gray-300 font-light text-sm">
            <li>
              <Link
                href="/about"
                className="hover:text-white transition-colors"
              >
                About us
              </Link>
            </li>
            <li>
              <Link
                href="/team"
                className="hover:text-white transition-colors"
              >
                Team
              </Link>
            </li>
            <li>
              <a
                href="#"
                className="hover:text-white transition-colors"
              >
                Research
              </a>
            </li>
            <li>
              <a
                href="#"
                className="hover:text-white transition-colors"
              >
                Contact
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="page-shell max-w-6xl mt-12 pt-6 border-t border-white/10 text-[11px] md:text-xs text-gray-500 flex flex-col md:flex-row justify-between items-center gap-3">
        <p>
          © {new Date().getFullYear()} Kruya-Jenjen AI Research Lab. All rights
          reserved.
        </p>
        <div className="flex gap-6">
          <a
            href="#"
            className="hover:text-white transition-colors"
          >
            Privacy policy
          </a>
          <a
            href="#"
            className="hover:text-white transition-colors"
          >
            Terms of service
          </a>
        </div>
      </div>
    </footer>
  );
}

