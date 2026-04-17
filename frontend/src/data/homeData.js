import React from "react";

export const quickActions = [
  {
    title: "Check your bin dates",
    icon: (
      <svg
        viewBox="0 0 64 64"
        className="h-24 w-24 text-[#00539f]"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <rect x="18" y="16" width="20" height="22" rx="2" />
        <path d="M22 12h12" />
        <path d="M25 10h6" />
        <circle cx="22" cy="42" r="3" />
        <circle cx="34" cy="42" r="3" />
        <path d="M14 30h8v14H12V34z" />
        <path d="M40 24h10l4 7v13H40z" />
        <path d="M24 22h8M24 28h8" />
        <path d="M46 28h4" />
      </svg>
    ),
  },
  {
    title: "Council Tax – report a change or ask a question",
    icon: (
      <svg
        viewBox="0 0 64 64"
        className="h-24 w-24 text-[#00539f]"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M14 28l18-14 18 14" />
        <path d="M18 26v14h12V30H18z" />
        <path d="M36 34l10 8" />
        <path d="M36 40l10-8" />
        <path d="M42 42v8h10V42" />
        <path d="M48 22v8" />
      </svg>
    ),
  },
  {
    title: "Benefits support",
    icon: (
      <svg viewBox="0 0 64 64" className="h-24 w-24 text-[#00539f]" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="14" y="18" width="36" height="28" rx="3" />
        <path d="M14 26h36" />
        <path d="M24 34h4" />
        <path d="M24 40h12" />
        <path d="M36 34h6" />
      </svg>
    ),
  },
  {
    title: "Blue Badge",
    icon: (
      <svg viewBox="0 0 64 64" className="h-24 w-24 text-[#00539f]" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="32" cy="20" r="6" />
        <path d="M20 44c0-8 5-14 12-14s12 6 12 14" />
        <rect x="12" y="44" width="40" height="8" rx="2" />
        <path d="M28 48h8" />
      </svg>
    ),
  },
  {
    title: "Library services",
    icon: (
      <svg viewBox="0 0 64 64" className="h-24 w-24 text-[#00539f]" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="12" y="14" width="10" height="36" rx="1" />
        <rect x="26" y="14" width="10" height="36" rx="1" />
        <rect x="40" y="14" width="10" height="36" rx="1" />
        <path d="M12 50h40" />
        <path d="M16 22h2M16 28h2M16 34h2" />
      </svg>
    ),
  },
  {
    title: "School admissions",
    icon: (
      <svg viewBox="0 0 64 64" className="h-24 w-24 text-[#00539f]" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M14 28l18-14 18 14v24H14z" />
        <rect x="24" y="36" width="16" height="16" rx="1" />
        <path d="M32 20v6" />
        <path d="M28 26h8" />
      </svg>
    ),
  },
];

export const serviceGroups = [
  {
    title: "Benefits",
    links: [
      "Housing Benefit and Council Tax Reduction",
      "MyInfo",
      "What benefits are available?",
    ],
  },
  {
    title: "Births, deaths and marriages",
    links: [
      "Get a copy certificate",
      "Marriages and Civil Partnerships",
      "Register a birth",
    ],
  },
  {
    title: "Children, young people and families",
    links: [
      "Bradford's Special Education Needs and Disabilities Local Offer",
      "Looking for early education and childcare",
      "Talk to us about a child",
    ],
  },
  {
    title: "Clean Air Zone",
    links: [
      "How to pay the CAZ penalty charge",
      "How to pay the daily CAZ charge",
      "Where is the Clean Air Zone?",
    ],
  },
  {
    title: "Council Tax",
    links: [
      "Pay your Council Tax",
      "Reduce your bill",
      "Report a change or ask a question about your Council Tax",
    ],
  },
  {
    title: "Education and skills",
    links: [
      "Apply for a place at school",
      "School closures",
      "Schools finder",
    ],
  },
  {
    title: "Libraries",
    links: [
      "Find your local library",
      "Log in to your library account",
      "Renew, borrow and reserve items",
    ],
  },
  {
    title: "Parking, roads and transport",
    links: [
      "Map of roadworks",
      "Parking permits",
      "Pay a parking or bus lane fine",
    ],
  },
  {
    title: "Recycling and waste",
    links: [
      "Check your bin collection dates",
      "Garden waste collection service",
      "New bins or repairs",
    ],
  },
];

export const featureTiles = [
  {
    title: "What's on",
    image:
      "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=900&q=80",
  },
  {
    title: "Bradford news",
    image:
      "https://images.unsplash.com/photo-1470004914212-05527e49370b?auto=format&fit=crop&w=900&q=80",
  },
  {
    title: "Visit Bradford",
    image:
      "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80",
  },
  {
    title: "Bradford Theatres",
    image:
      "https://images.unsplash.com/photo-1518998053901-5348d3961a04?auto=format&fit=crop&w=900&q=80",
  },
];

export const starterQueries = [
  "Bin collection",
  "Council tax",
  "Benefits support",
  "Blue Badge",
  "Library services",
  "School admissions",
];