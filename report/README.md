# UBS Financial Elite Challenge 2026 — Report

**LONG** Xiaomi Corporation (1810.HK) **/ SHORT** SenseTime Group (0020.HK)

This folder contains the complete LaTeX report and source materials for the competition submission.

---

## 📂 Folder Structure

```
report/
├── main.tex              # Main 20-page LaTeX report
├── refs.bib              # Bibliography (BibLaTeX format)
├── figures/              # Generated PDF figures
│   ├── generate_all.py   # Python script to regenerate all 10 charts
│   ├── fig1_xiaomi_revenue.pdf
│   ├── fig2_profitability.pdf
│   ├── fig3_stock_performance.pdf
│   ├── fig4_ev_deliveries.pdf
│   ├── fig5_valuation_bubble.pdf
│   ├── fig6_pair_spread.pdf
│   ├── fig7_risk_heatmap.pdf
│   ├── fig8_ai_workflow.pdf
│   ├── fig9_catalysts.pdf
│   └── fig10_sentiment.pdf
└── README.md             # This file
```

---

## 🚀 How to Generate the Final PDF

### Option 1 — Online (Easiest, 30 seconds)

1. Go to **[https://www.overleaf.com](https://www.overleaf.com)** (free signup with email).
2. Click **"New Project"** → **"Upload Project"**.
3. Compress the entire `report/` folder to a `.zip` file.
4. Upload the zip file.
5. Set compiler to **`XeLaTeX`** or **`LuaLaTeX`** (top right → Menu → Compiler).
6. Click **"Recompile"**. Done!
7. Click the download button (next to "Recompile") to save as PDF.

### Option 2 — Local (if you have a LaTeX installation)

```bash
cd report
xelatex main.tex
biber main          # for the bibliography
xelatex main.tex
xelatex main.tex    # run twice more to resolve all references
```

You can also use **TeXShop** (Mac) / **TeXstudio** (Windows) / **VS Code with LaTeX Workshop**.

---

## 📊 Regenerating Charts (optional)

If you want to update charts with the latest data:

```bash
cd report/figures
python generate_all.py
```

This pulls fresh data from Yahoo Finance and saves 10 PDFs.

**Required Python packages** (already installed in the parent project):
- `matplotlib`, `numpy`, `yfinance`

---

## ✅ Compliance with UBS Competition Rules

| Rule | Compliance |
|------|------------|
| 20-page limit (excl. appendix) | ✅ Main body: ~20 pages |
| English language | ✅ |
| One stock from pool | ✅ Xiaomi 1810.HK (in tech pool) |
| Other from same sector, NOT in pool | ✅ SenseTime 0020.HK (HK Tech, not in pool) |
| Long/short pair logic | ✅ Clearly explained throughout Sections 1–7 |
| Fundamental + valuation + AI module | ✅ Sections 3–6 (fundamental), 5 (valuation), 8 (AI) |
| AI module advantages & limitations | ✅ Section 9 dedicated |

---

## 🎯 Report Highlights

- **Executive summary** with one-glance recommendation table
- **Multi-segment fundamental analysis** for both companies
- **SOTP valuation** for Xiaomi (target: HK$47.30, +51%)
- **Scenario-weighted DCF** for SenseTime (target: HK$1.31, −29%)
- **6 valuation lenses** showing convergence direction
- **Information Ratio = 0.67** (institutional-grade)
- **10 professional figures** (revenue, profitability, performance, EV trajectory, valuation bubble, pair P&L, risk heatmap, AI architecture, catalyst timeline, sentiment tracking)
- **Multi-model AI pipeline** (DeepSeek + Gemini + quant screener)
- **Honest discussion** of AI limitations

---

## 📝 Notes for the Author

- All numbers cross-checked against primary sources (Xiaomi 2025 Annual Report, SenseTime 2025 Results, Counterpoint, IDC, CnEVPost).
- Citations use BibLaTeX with numeric style.
- Figures use UBS color palette (red `#E60000`, black, accent green/blue).
- TeX file is self-contained — no additional package downloads beyond standard TeX Live distribution.
- If Overleaf complains about a package, switch the compiler to **XeLaTeX** (most reliable).

---

## 📞 Need Help?

If LaTeX compilation fails:
1. Check that compiler is set to **XeLaTeX** (not pdfLaTeX).
2. Verify `figures/` folder is uploaded with all 10 PDFs.
3. Run `biber` between latex passes to resolve bibliography.

Good luck with the competition! 🏆
