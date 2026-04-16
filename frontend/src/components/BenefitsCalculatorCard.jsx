import React, { useState } from "react";

const fieldCls =
  "w-full rounded-xl border border-[#c8d5ea] bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-[#0f4ca3]";
const labelCls = "block text-xs font-semibold text-slate-500 mb-1";

export default function BenefitsCalculatorCard({ onResult }) {
  const [ageGroup, setAgeGroup] = useState("working");
  const [weeklyRent, setWeeklyRent] = useState("");
  const [weeklyIncome, setWeeklyIncome] = useState("");
  const [savings, setSavings] = useState("");
  const [weeklyCouncilTax, setWeeklyCouncilTax] = useState("");
  const [result, setResult] = useState(null);

  const calculate = () => {
    const rent = parseFloat(weeklyRent) || 0;
    const income = parseFloat(weeklyIncome) || 0;
    const savingsAmt = parseFloat(savings) || 0;
    const ctWeekly = parseFloat(weeklyCouncilTax) || 25;

    const savingsOver16k = savingsAmt > 16000;
    const tariffIncome = savingsAmt > 6000 ? Math.floor((savingsAmt - 6000) / 250) : 0;
    const totalIncome = income + tariffIncome;

    let hbNote = "";
    let hbAmount = 0;
    let ctrPercent = 0;
    let ctrAmount = 0;

    if (savingsOver16k) {
      hbNote =
        "You are not eligible for Housing Benefit or Council Tax Reduction as your savings exceed £16,000.";
    } else if (ageGroup === "working") {
      hbNote =
        "Working-age residents cannot claim Housing Benefit from Bradford Council — you must claim the housing element of Universal Credit from the DWP instead.";
      const excessIncome = Math.max(0, totalIncome - 120);
      const reduction = Math.max(0, 0.725 - excessIncome * 0.005);
      ctrPercent = Math.min(72.5, Math.round(reduction * 100 * 10) / 10);
      ctrAmount = Math.round(ctWeekly * (ctrPercent / 100) * 100) / 100;
    } else {
      const eligible = rent > 0 && totalIncome < 300;
      if (eligible) {
        const excessIncome = Math.max(0, totalIncome - 130);
        const hbFraction = Math.max(0, 1 - excessIncome * 0.0065);
        hbAmount = Math.round(rent * hbFraction * 100) / 100;
        hbNote = `Estimated weekly Housing Benefit: £${hbAmount.toFixed(2)}`;
      } else {
        hbNote =
          rent <= 0
            ? "Please enter your weekly rent to estimate Housing Benefit."
            : "Based on the income entered, you may not be eligible for Housing Benefit.";
      }
      ctrPercent = Math.min(
        100,
        Math.max(
          0,
          Math.round((1 - Math.max(0, totalIncome - 130) * 0.006) * 100)
        )
      );
      ctrAmount = Math.round(ctWeekly * (ctrPercent / 100) * 100) / 100;
    }

    setResult({ hbNote, hbAmount, ctrPercent, ctrAmount, ageGroup, savingsOver16k });
  };

  const handleSend = () => {
    if (!result) return;
    const summary = result.savingsOver16k
      ? "My savings exceed £16,000 so I am not eligible."
      : ageGroup === "working"
      ? `Working-age estimate: Council Tax Reduction ~${result.ctrPercent}% (~£${result.ctrAmount.toFixed(2)}/week). ${result.hbNote}`
      : `Pension-age estimate: ${result.hbNote}. Council Tax Reduction ~${result.ctrPercent}% (~£${result.ctrAmount.toFixed(2)}/week).`;
    onResult(summary);
  };

  return (
    <div className="fade-slide-in flex items-start gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#dbeafe] text-[#0f4ca3] shadow-sm">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="8" r="3.2" />
          <path d="M5.5 19c1.4-3 4-4.5 6.5-4.5S17 16 18.5 19" />
        </svg>
      </div>

      <div className="w-full max-w-[80%] rounded-[1.5rem] rounded-tl-md bg-white px-5 py-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <span className="text-lg">&#128176;</span>
          <h3 className="text-base font-bold text-[#123b7a]">Benefits Estimator</h3>
        </div>

        <p className="mb-4 text-xs leading-5 text-slate-500">
          This gives a rough estimate only. Your actual entitlement depends on a full assessment by Bradford Council.
        </p>

        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className={labelCls}>Age group</label>
            <div className="flex gap-2">
              {["working", "pension"].map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setAgeGroup(g)}
                  className={`flex-1 rounded-xl border py-2 text-sm font-semibold transition ${
                    ageGroup === g
                      ? "border-[#0f4ca3] bg-[#eef4ff] text-[#0f4ca3]"
                      : "border-[#c8d5ea] bg-white text-slate-600 hover:bg-[#f5f8ff]"
                  }`}
                >
                  {g === "working" ? "Working age" : "Pension age"}
                </button>
              ))}
            </div>
          </div>

          {ageGroup === "pension" && (
            <div>
              <label className={labelCls}>Weekly rent (£)</label>
              <input
                className={fieldCls}
                type="number"
                min="0"
                placeholder="e.g. 120"
                value={weeklyRent}
                onChange={(e) => setWeeklyRent(e.target.value)}
              />
            </div>
          )}

          <div>
            <label className={labelCls}>Weekly income (£)</label>
            <input
              className={fieldCls}
              type="number"
              min="0"
              placeholder="e.g. 200"
              value={weeklyIncome}
              onChange={(e) => setWeeklyIncome(e.target.value)}
            />
          </div>

          <div>
            <label className={labelCls}>Savings / capital (£)</label>
            <input
              className={fieldCls}
              type="number"
              min="0"
              placeholder="e.g. 3000"
              value={savings}
              onChange={(e) => setSavings(e.target.value)}
            />
          </div>

          <div>
            <label className={labelCls}>Weekly Council Tax (£)</label>
            <input
              className={fieldCls}
              type="number"
              min="0"
              placeholder="e.g. 25"
              value={weeklyCouncilTax}
              onChange={(e) => setWeeklyCouncilTax(e.target.value)}
            />
          </div>
        </div>

        <button
          type="button"
          onClick={calculate}
          className="mt-4 w-full rounded-xl bg-[#0f4ca3] py-2.5 text-sm font-semibold text-white shadow transition hover:bg-[#0d438f]"
        >
          Calculate estimate
        </button>

        {result && !result.savingsOver16k && (
          <div className="mt-4 space-y-2">
            {result.ageGroup === "pension" && result.hbAmount > 0 && (
              <div className="rounded-xl border border-[#bbf7d0] bg-[#f0fdf4] px-4 py-3">
                <p className="mb-0.5 text-xs font-semibold text-[#166534]">Housing Benefit estimate</p>
                <p className="text-lg font-bold text-[#14532d]">£{result.hbAmount.toFixed(2)} / week</p>
              </div>
            )}
            {result.hbNote && result.ageGroup === "working" && (
              <div className="rounded-xl border border-[#fed7aa] bg-[#fff7ed] px-4 py-3">
                <p className="mb-0.5 text-xs font-semibold text-[#9a3412]">Housing Benefit</p>
                <p className="text-sm leading-5 text-[#7c2d12]">{result.hbNote}</p>
              </div>
            )}
            <div className="rounded-xl border border-[#bfdbfe] bg-[#eff6ff] px-4 py-3">
              <p className="mb-0.5 text-xs font-semibold text-[#1e40af]">Council Tax Reduction estimate</p>
              <p className="text-lg font-bold text-[#1e3a8a]">
                {result.ctrPercent}%{" "}
                <span className="text-sm font-medium">(~£{result.ctrAmount.toFixed(2)} / week)</span>
              </p>
            </div>
            <button
              type="button"
              onClick={handleSend}
              className="mt-1 w-full rounded-xl border border-[#0f4ca3] py-2 text-sm font-semibold text-[#0f4ca3] transition hover:bg-[#eef4ff]"
            >
              Use this estimate in chat
            </button>
          </div>
        )}

        {result && result.savingsOver16k && (
          <div className="mt-4 rounded-xl border border-[#fecaca] bg-[#fef2f2] px-4 py-3">
            <p className="text-sm text-[#991b1b]">{result.hbNote}</p>
          </div>
        )}

        <p className="mt-3 text-xs leading-5 text-slate-400">
          &#128279;&nbsp;
          <a
            href="https://www.bradford.gov.uk/benefits/benefits/"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-[#0f4ca3] underline"
          >
            Apply on Bradford Council website
          </a>
        </p>
      </div>
    </div>
  );
}
