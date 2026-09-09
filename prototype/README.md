# TradingAgents web prototype

A standalone, Korean-language interactive UI concept. Open `index.html` directly, or serve this directory:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory prototype
```

Visit http://127.0.0.1:8765. No build or package installation is required. Fonts and icons are local/system resources; the interface makes no external font requests.

## Included flows

- Research dashboard with synthetic chart period switching, analyst report tabs, debate summary, and portfolio decision.
- New research dialog: sample symbol, date, provider, analyst selection, and research depth.
- Nine-second simulated stage progression, followed by a sample report and session history entry.
- Session-only provider/model preferences and Markdown sample report download.
- Responsive desktop/mobile layout, keyboard-operable controls, and native dialog.

All numbers, charts, analysis, and decisions are fabricated demonstration content. Changing settings does not invoke the CLI, financial data providers, models, or order execution. History and preferences reset on refresh.

## Design revision 02

The Apple-inspired visual layer lives in `apple.css`, over the original structural styles in `style.css`. It follows the user-supplied [apple-design skill](https://github.com/dickwu/apple-design-skill/blob/main/SKILL.md) and its accessibility, color, layout, typography, materials, icons, and dark-mode references.

The review identified undersized secondary text, weak text contrast, inconsistent symbol glyphs, and competing decorative labels. The revision increases the type scale, uses system fonts and consistent inline SVG icons, separates blue actions from green positive states, simplifies headings, and adds more space around primary content. Neutral, opaque content cards sit below translucent navigation surfaces. Existing research workflows remain intact.

The interface follows system light/dark appearance, supports increased contrast and reduced motion/transparency preferences, and uses a bottom navigation bar on mobile with safe-area padding. It includes a skip link, a named native dialog, visible keyboard focus, and pressed states for chart period controls. Mobile primary navigation, tabs, and form controls have 44px or larger interaction heights. This is an independent design interpretation, not an Apple product or an assertion of full HIG/WCAG conformance.

## Proposed production integration

Keep the existing Python graph as the execution layer. Map the form to validated server-side CLI-equivalent settings, submit a background research job, and stream graph stage events and report updates to the browser. Store job IDs, state, checkpoints, and reports server-side for history and resume. Keep credentials server-side and render structured report content safely. Model/provider availability must come from the existing registry; the prototype's free-text model settings are only a design placeholder. Add explicit loading, no-data, error, cancellation, and resume flows when the backend contract is implemented.
