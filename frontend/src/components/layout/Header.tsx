import { Link, NavLink } from "react-router-dom";

import { ThemeToggle } from "../common/ThemeToggle";

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line/[0.07] bg-surface/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-[1440px] items-center justify-between px-5 sm:px-8">
        <Link aria-label="MarketView, accueil" className="flex items-center gap-3" to="/">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-accent text-on-accent">
            <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
              <path d="M3 17.5 8.3 12l3.5 3.5L21 6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.1" />
              <path d="M15.5 6H21v5.5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.1" />
            </svg>
          </span>
          <span className="text-[17px] font-semibold tracking-[-0.04em] text-fg">
            market<span className="text-accent">view</span>
          </span>
        </Link>

        <nav aria-label="Navigation principale" className="flex items-center gap-2 text-sm">
          <NavLink
            className={({ isActive }) =>
              `rounded-full px-4 py-2 transition ${isActive ? "bg-line/[0.08] text-fg" : "text-muted hover:text-fg"}`
            }
            end
            to="/"
          >
            Marchés
          </NavLink>
          <span className="hidden items-center gap-2 rounded-full border border-line/[0.08] px-3 py-1.5 text-xs text-muted sm:inline-flex">
            <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-[0_0_10px_rgb(var(--c-accent))]" />
            Marchés en direct
          </span>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
