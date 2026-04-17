import React, { useState } from "react";
import ChatModal from "./components/ChatModal";
import {
  quickActions,
  serviceGroups,
  featureTiles,
  starterQueries,
} from "./data/homeData";

export default function App() {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white text-[#123b7a]">
      {/* ── Floating Chat Button ─────────────────────────────────────────── */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          aria-label="Open chat assistant"
          className="fixed bottom-5 right-4 z-40 flex items-center gap-2 rounded-full bg-[#0f4ca3] px-4 py-3 text-white shadow-2xl transition hover:bg-[#0d438f] hover:scale-105 active:scale-95 sm:bottom-6 sm:right-6 sm:gap-2.5 sm:px-5 sm:py-3.5"
          style={{ boxShadow: "0 8px 30px rgba(15,76,163,0.45)" }}
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 16V5h12v11H8l-2 3v-3H6z" />
            <path d="M9 9h6M9 12h4" />
          </svg>
          <span className="text-sm font-semibold">Ask the Assistant</span>
          <span className="flex h-2 w-2 rounded-full bg-green-400 ring-2 ring-green-200" />
        </button>
      )}

      <header className="bg-white px-3 pt-3 sm:px-4 sm:pt-4">
        <div className="mx-auto flex max-w-[1360px] items-center justify-between gap-3 md:flex-row md:items-start md:justify-between">
          <div className="flex items-center gap-3 pl-1 sm:pl-2">
            <img
              src="/images/logo.png"
              alt="Bradford Council"
              className="h-10 object-contain sm:h-14 md:h-16"
            />
          </div>

          <div className="flex flex-1 items-center gap-2 md:ml-6 md:gap-3">
            <div className="relative flex-1">
              <input
                className="h-9 w-full rounded-full border border-[#00539f] bg-white px-4 pr-9 text-[12px] text-slate-700 outline-none sm:h-[30px] sm:px-5"
                placeholder="Search our services"
              />
              <svg
                viewBox="0 0 24 24"
                className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#1f2937]"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="11" cy="11" r="6" />
                <path d="M20 20l-4.2-4.2" />
              </svg>
            </div>

            <button className="shrink-0 rounded-full bg-[#00539f] px-4 py-2 text-[12px] font-semibold text-white shadow-sm hover:bg-[#00498f] sm:px-8 sm:py-3 sm:text-[13px]">
              <span className="hidden sm:inline">Register | Log on</span>
              <span className="sm:hidden">Log on</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1360px] px-4 pb-0">
        <section
          className="relative h-[160px] overflow-hidden bg-cover bg-center bg-no-repeat sm:h-[220px] md:h-[300px]"
          style={{ backgroundImage: "url('/images/hero.jpg')" }}
        >
          <button
            onClick={() => setChatOpen(true)}
            className="absolute right-0 top-1/2 -translate-y-1/2 rounded-l-full bg-[#0b2c78] px-3 py-3 text-white shadow-lg hover:bg-[#092666]"
            aria-label="Open chat"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M6 16V5h12v11H8l-2 3v-3H6z" />
              <path d="M9 9h6M9 12h4" />
            </svg>
          </button>
        </section>

        <section className="px-0 pb-6 pt-0">
          <div className="mx-auto max-w-[1190px] bg-[#f2f2f2] py-5 text-center text-[18px] font-semibold text-[#00539f]">
            City of Bradford Metropolitan District Council
          </div>
        </section>

        <section className="mx-auto max-w-[1190px] pb-8">
          <div className="grid grid-cols-2 gap-5 md:grid-cols-3 xl:grid-cols-6">
            {quickActions.map((item) => (
              <button
                key={item.title}
                className="group flex min-h-[185px] flex-col items-center justify-center bg-[#e6e6e6] px-4 py-6 text-center transition hover:bg-[#dddddd]"
              >
                <div className="mb-4 transition group-hover:scale-105">
                  {item.icon}
                </div>
                <div className="max-w-[160px] text-[12px] leading-4 text-[#00539f]">
                  {item.title}
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="bg-[#efefef] py-10">
          <div className="mx-auto max-w-[1190px]">
            <div className="grid gap-5 md:grid-cols-2">
              {serviceGroups.map((group) => (
                <div key={group.title} className="bg-white p-5 shadow-sm">
                  <h3 className="text-[20px] leading-6 text-[#3f76a8] underline">
                    {group.title}
                  </h3>
                  <ul className="mt-4 space-y-2 text-[13px] text-[#3f76a8] underline">
                    {group.links.map((link) => (
                      <li key={link}>{link}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="mt-10 flex justify-center">
              <button className="bg-[#00539f] px-10 py-3 text-sm font-semibold text-white hover:bg-[#00498f]">
                More Services ...
              </button>
            </div>
          </div>
        </section>

        <section className="border-t border-[#2f79b7] bg-[#e9eef2] py-8 sm:py-10">
          <div className="mx-auto flex max-w-[1190px] flex-col gap-5 px-4 md:flex-row md:items-center md:justify-between md:px-0">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-[#2f79b7] text-white sm:h-14 sm:w-14">
                <svg viewBox="0 0 24 24" className="h-7 w-7 sm:h-8 sm:w-8" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M3 6h18v12H3z" />
                  <path d="M3 7l9 7 9-7" />
                </svg>
              </div>
              <div>
                <h3 className="text-2xl font-light text-[#2f79b7] sm:text-3xl">Stay Connected</h3>
                <p className="mt-2 max-w-[420px] text-sm text-slate-600">
                  Sign up for our Stay Connected emails and get the information that matters to you most in your inbox.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                className="h-10 flex-1 border border-slate-300 bg-white px-3 text-sm outline-none md:w-[220px] md:flex-none"
                placeholder="Your email address"
              />
              <button className="h-10 shrink-0 bg-[#00539f] px-5 text-sm font-semibold text-white">
                Send
              </button>
            </div>
          </div>
        </section>

        <section className="bg-[#ececec] py-10">
          <div className="mx-auto grid max-w-[1190px] gap-8 md:grid-cols-2">
            {featureTiles.map((tile) => (
              <div key={tile.title} className="bg-white shadow-sm">
                <img
                  src={tile.image}
                  alt={tile.title}
                  className="h-[220px] w-full object-cover"
                />
                <div className="mx-3 -mt-5 bg-[#00539f] px-3 py-2 text-xl text-white">
                  {tile.title}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-[#4b4b4b] py-10">
          <div className="mx-auto flex max-w-[1190px] flex-col gap-8 md:flex-row md:items-center md:justify-between">
            <button className="bg-black px-8 py-3 text-sm text-white">
              Contact us now
            </button>
            <div className="flex items-center gap-4 text-white">
              {["f", "x", "w", "i", "in"].map((label) => (
                <div
                  key={label}
                  className="flex h-12 w-12 items-center justify-center rounded-full border border-white text-lg font-semibold"
                >
                  {label}
                </div>
              ))}
            </div>
          </div>
        </section>

        <footer className="bg-black py-10 text-white">
          <div className="mx-auto grid max-w-[1190px] gap-8 md:grid-cols-[1fr_auto_1fr] md:items-end">
            <div className="space-y-3 text-sm underline">
              <div>Cookies</div>
              <div>Privacy Notice</div>
              <div>A to Z</div>
              <div>Accessibility Statement</div>
            </div>

            <div className="text-center text-slate-300">
              <div className="mb-3 flex justify-center">
                <img
                  src="/images/logo.png"
                  alt="Bradford Council"
                  className="h-14 object-contain opacity-90"
                />
              </div>
              <div className="text-xs">
                Copyright 2026 City of Bradford Metropolitan District Council
              </div>
            </div>

            <div />
          </div>
        </footer>
      </main>

      <ChatModal
        chatOpen={chatOpen}
        setChatOpen={setChatOpen}
        starterQueries={starterQueries}
      />
    </div>
  );
}