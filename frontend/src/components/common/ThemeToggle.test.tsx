import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { THEME_STORAGE_KEY } from "../../store/themeStore";
import { ThemeToggle } from "./ThemeToggle";

describe("ThemeToggle", () => {
  it("bascule entre thème sombre et clair et mémorise le choix", () => {
    document.documentElement.classList.add("dark");
    render(<ThemeToggle />);

    fireEvent.click(screen.getByRole("button", { name: "Passer au thème clair" }));
    expect(document.documentElement).not.toHaveClass("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");

    fireEvent.click(screen.getByRole("button", { name: "Passer au thème sombre" }));
    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });
});
