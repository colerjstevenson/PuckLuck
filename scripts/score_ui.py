from __future__ import annotations

import json
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, Tk, StringVar, Text, messagebox
from tkinter import ttk
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.game_service import SCORE_WEIGHTS, load_players, score_lineup  # type: ignore[import-not-found]  # noqa: E402


SLOTS = ["F1", "F2", "F3", "D1", "D2", "G"]
SLOT_GROUPS = {
    "F1": "Forward",
    "F2": "Forward",
    "F3": "Forward",
    "D1": "Defense",
    "D2": "Defense",
    "G": "Goalie",
}


@dataclass(frozen=True)
class PlayerOption:
    label: str
    player_id: str
    name: str
    position_group: str


class AutocompleteCombobox(ttk.Combobox):
    def __init__(self, master: Any, *, values: list[str], **kwargs: Any) -> None:
        super().__init__(master, values=values, **kwargs)
        self._all_values = list(values)
        self.bind("<KeyRelease>", self._handle_keyrelease)
        self.bind("<FocusIn>", self._show_all_values)
        self.bind("<Control-space>", self._show_all_values)

    def _show_all_values(self, _event: object | None = None) -> None:
        self.configure(values=self._all_values)

    def _find_matches(self, text: str) -> list[str]:
        starts_with: list[str] = []
        word_starts_with: list[str] = []
        contains: list[str] = []

        for value in self._all_values:
            lowered = value.lower()
            if lowered.startswith(text):
                starts_with.append(value)
            elif any(part.startswith(text) for part in lowered.split()):
                word_starts_with.append(value)
            elif text in lowered:
                contains.append(value)

        return starts_with + word_starts_with + contains

    def _open_dropdown_preserve_cursor(self, cursor_pos: int) -> None:
        try:
            self.tk.call("ttk::combobox::Post", self)
        except Exception:
            try:
                self.event_generate("<Down>")
            except Exception:
                return

        # Keep typing focus in the entry and restore insertion point.
        self.after_idle(lambda: (self.focus_set(), self.icursor(cursor_pos)))

    def _handle_keyrelease(self, event: Any) -> None:
        if event.keysym in {"Up", "Down", "Left", "Right", "Return", "Escape", "Tab"}:
            return

        cursor_pos = self.index("insert")
        text = self.get().strip().lower()
        if not text:
            self.configure(values=self._all_values)
            return

        matches = self._find_matches(text)
        self.configure(values=matches or self._all_values)

        if not matches or text in {value.lower() for value in matches}:
            return

        # If there is one clear prefix match, complete it inline while preserving what was typed.
        if len(matches) == 1 and matches[0].lower().startswith(text):
            match = matches[0]
            self.set(match)
            self.icursor(len(text))
            self.select_range(len(text), END)
            return

        self._open_dropdown_preserve_cursor(cursor_pos)


def _sort_key(player: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(player.get("name", "")).lower(),
        str(player.get("positionGroup", "")).lower(),
        str(player.get("id", "")),
    )


def _format_player_label(player: dict[str, Any], *, include_id: bool) -> str:
    name = str(player.get("name", "Unknown Player"))
    player_id = str(player.get("id", ""))
    if include_id:
        return f"{name} ({player_id})"
    return name


def _build_player_options(players: list[dict[str, Any]]) -> tuple[dict[str, list[PlayerOption]], dict[str, PlayerOption], dict[str, PlayerOption]]:
    grouped: dict[str, list[PlayerOption]] = {"Forward": [], "Defense": [], "Goalie": []}
    by_id: dict[str, PlayerOption] = {}
    by_label: dict[str, PlayerOption] = {}

    name_counts_by_group: dict[str, Counter[str]] = {
        "Forward": Counter(),
        "Defense": Counter(),
        "Goalie": Counter(),
    }

    for player in players:
        group = str(player.get("positionGroup", ""))
        if group not in grouped:
            continue
        name = str(player.get("name", "Unknown Player"))
        name_counts_by_group[group][name.casefold()] += 1

    for player in sorted(players, key=_sort_key):
        group = str(player.get("positionGroup", ""))
        if group not in grouped:
            continue

        player_id = str(player.get("id", ""))
        if not player_id:
            continue

        player_name = str(player.get("name", "Unknown Player"))
        include_id = name_counts_by_group[group][player_name.casefold()] > 1

        option = PlayerOption(
            label=_format_player_label(player, include_id=include_id),
            player_id=player_id,
            name=player_name,
            position_group=group,
        )
        grouped[group].append(option)
        by_id[player_id] = option
        by_label[option.label] = option

    return grouped, by_id, by_label


class ScoreWorkbenchApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("NHL Score Workbench")
        self.root.geometry("1220x820")
        self.root.minsize(1080, 720)

        players = load_players()
        if not players:
            raise RuntimeError("No players were loaded. Build the backend player data first.")

        self.players = players
        self.options_by_group, self.option_by_id, self.option_by_label = _build_player_options(players)
        self.slot_vars: dict[str, StringVar] = {}
        self.weight_vars: dict[str, StringVar] = {}

        self._configure_style()
        self._build_layout()
        self._fill_default_lineup()
        self.score_current_lineup()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.root.configure(background="#f4f7fb")

        style.configure("App.TFrame", background="#f4f7fb")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("Header.TLabel", background="#f4f7fb", foreground="#132238", font=("Segoe UI", 18, "bold"))
        style.configure("Subtle.TLabel", background="#f4f7fb", foreground="#526173", font=("Segoe UI", 10))
        style.configure("Slot.TLabel", background="#ffffff", foreground="#132238", font=("Segoe UI", 10, "bold"))
        style.configure("Panel.TLabelframe", background="#ffffff", foreground="#132238")
        style.configure("Panel.TLabelframe.Label", background="#ffffff", foreground="#132238", font=("Segoe UI", 10, "bold"))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=18, style="App.TFrame")
        outer.pack(fill=BOTH, expand=True)

        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill="x", pady=(0, 14))

        ttk.Label(header, text="NHL Score Workbench", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Pick players for F1/F2/F3/D1/D2/G, then score the lineup with the current backend rules.",
            style="Subtle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        summary = ttk.Frame(outer, style="App.TFrame")
        summary.pack(fill="x", pady=(0, 12))
        ttk.Label(
            summary,
            text=(
                f"Loaded {len(self.players)} players | "
                f"Forwards: {len(self.options_by_group['Forward'])} | "
                f"Defense: {len(self.options_by_group['Defense'])} | "
                f"Goalies: {len(self.options_by_group['Goalie'])}"
            ),
            style="Subtle.TLabel",
        ).pack(anchor="w")

        body = ttk.Frame(outer, style="App.TFrame")
        body.pack(fill=BOTH, expand=True)

        left = ttk.Frame(body, style="Card.TFrame", padding=16)
        left.pack(side=LEFT, fill=BOTH, expand=False)

        right = ttk.Frame(body, style="Card.TFrame", padding=16)
        right.pack(side=RIGHT, fill=BOTH, expand=True, padx=(16, 0))

        ttk.Label(
            left,
            text="Lineup Builder",
            background="#ffffff",
            foreground="#132238",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(
            left,
            text="Type a player name or pick from the dropdown. Then score the lineup.",
            background="#ffffff",
            foreground="#526173",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 10))

        slots_frame = ttk.Frame(left, style="Card.TFrame")
        slots_frame.pack(fill=BOTH, expand=True)

        for slot in SLOTS:
            group = SLOT_GROUPS[slot]
            row = ttk.Frame(slots_frame, style="Card.TFrame")
            row.pack(fill="x", pady=6)

            ttk.Label(row, text=f"{slot} ({group})", style="Slot.TLabel").pack(anchor="w")

            options = [option.label for option in self.options_by_group[group]]
            var = StringVar(value="")
            self.slot_vars[slot] = var
            combo = AutocompleteCombobox(row, textvariable=var, values=options, width=54)
            combo.pack(fill="x", pady=(4, 0))
            combo.bind("<<ComboboxSelected>>", self._on_selection_change)
            combo.bind("<Return>", self._on_selection_change)
            combo.bind("<FocusOut>", self._on_selection_change)

        button_row = ttk.Frame(left, style="Card.TFrame")
        button_row.pack(fill="x", pady=(12, 0))
        ttk.Button(button_row, text="Score lineup", style="Action.TButton", command=self.score_current_lineup).pack(
            side=LEFT, padx=(0, 8)
        )
        ttk.Button(button_row, text="Random valid lineup", command=self._fill_random_lineup).pack(side=LEFT, padx=(0, 8))
        ttk.Button(button_row, text="Clear", command=self.clear_lineup).pack(side=LEFT)

        weights_box = ttk.LabelFrame(left, text="Scoring weights", style="Panel.TLabelframe", padding=10)
        weights_box.pack(fill="x", pady=(14, 0))

        weights_grid = ttk.Frame(weights_box, style="Card.TFrame")
        weights_grid.pack(fill="x")

        weight_items = [
            ("production", "Production"),
            ("trophies", "Awards"),
            ("cups", "Cups"),
            ("grit", "Grit"),
            ("positionFit", "Position fit"),
            ("hallOfFame", "Hall of Fame"),
            ("goalieQuality", "Goalie quality"),
        ]

        for row_index, (weight_key, label) in enumerate(weight_items):
            ttk.Label(weights_grid, text=label, style="Slot.TLabel").grid(row=row_index, column=0, sticky="w", pady=3)
            value_var = StringVar(value=f"{SCORE_WEIGHTS[weight_key]:.3f}".rstrip("0").rstrip("."))
            self.weight_vars[weight_key] = value_var
            ttk.Entry(weights_grid, textvariable=value_var, width=10).grid(row=row_index, column=1, sticky="e", padx=(12, 0), pady=3)

        weights_grid.columnconfigure(0, weight=1)

        weights_button_row = ttk.Frame(weights_box, style="Card.TFrame")
        weights_button_row.pack(fill="x", pady=(10, 0))
        ttk.Button(weights_button_row, text="Copy weights", command=self.copy_weights_to_clipboard).pack(side=LEFT)

        self.status_var = StringVar(value="Ready.")
        ttk.Label(
            left,
            textvariable=self.status_var,
            background="#ffffff",
            foreground="#526173",
            font=("Segoe UI", 9),
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

        ttk.Label(
            right,
            text="Score Output",
            background="#ffffff",
            foreground="#132238",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        output_frame = ttk.Frame(right, style="Card.TFrame")
        output_frame.pack(fill=BOTH, expand=True)

        self.output = Text(
            output_frame,
            wrap="word",
            height=30,
            borderwidth=0,
            background="#f8fafc",
            foreground="#132238",
            insertbackground="#132238",
            font=("Consolas", 10),
        )
        self.output.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(output_frame, orient=VERTICAL, command=self.output.yview)
        scrollbar.pack(side=RIGHT, fill="y")
        self.output.configure(yscrollcommand=scrollbar.set)

    def _on_selection_change(self, _event: object | None = None) -> None:
        self.score_current_lineup()

    def _resolve_selection(self, slot: str, raw_value: str) -> PlayerOption | None:
        value = raw_value.strip()
        if not value:
            return None

        option = self.option_by_label.get(value)
        if option:
            return option

        option = self.option_by_id.get(value)
        if option and option.position_group == SLOT_GROUPS[slot]:
            return option

        group = SLOT_GROUPS[slot]
        candidates = [
            player_option
            for player_option in self.options_by_group[group]
            if player_option.name.lower() == value.lower()
            or player_option.label.lower().startswith(value.lower())
            or player_option.player_id == value
        ]

        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise ValueError(f"{slot} is ambiguous. Pick a full dropdown value for {group} players.")
        return None

    def _current_lineup_payload(self) -> tuple[list[dict[str, str]], list[str]]:
        lineup: list[dict[str, str]] = []
        display_lines: list[str] = []

        for slot in SLOTS:
            option = self._resolve_selection(slot, self.slot_vars[slot].get())
            if not option:
                continue
            lineup.append({"slot": slot, "playerId": option.player_id})
            display_lines.append(f"{slot}: {option.name} [{option.position_group}] ({option.player_id})")

        return lineup, display_lines

    def clear_lineup(self) -> None:
        for var in self.slot_vars.values():
            var.set("")
        self.status_var.set("Lineup cleared.")
        self._render_output("Lineup cleared. Select players and score the lineup.")

    def _fill_random_lineup(self) -> None:
        try:
            selected = {
                "F1": random.choice(self.options_by_group["Forward"]),
                "F2": random.choice(self.options_by_group["Forward"]),
                "F3": random.choice(self.options_by_group["Forward"]),
                "D1": random.choice(self.options_by_group["Defense"]),
                "D2": random.choice(self.options_by_group["Defense"]),
                "G": random.choice(self.options_by_group["Goalie"]),
            }
        except IndexError:
            messagebox.showerror("Missing players", "Not enough players were loaded to build a valid lineup.")
            return

        for slot, option in selected.items():
            self.slot_vars[slot].set(option.label)

        self.score_current_lineup()

    def _fill_default_lineup(self) -> None:
        desired_players = {
            "F1": "Wayne Gretzky",
            "F2": "Jean Beliveau",
            "F3": "Jaromir Jagr",
            "D1": "Paul Coffey",
            "D2": "Scott Stevens",
            "G": "Martin Brodeur",
        }

        try:
            for slot, player_name in desired_players.items():
                option = next(
                    player_option
                    for player_option in self.options_by_group[SLOT_GROUPS[slot]]
                    if player_option.name.casefold() == player_name.casefold()
                )
                self.slot_vars[slot].set(option.label)
        except StopIteration:
            messagebox.showerror("Missing players", "Could not find one of the default skaters in the loaded player data.")
            return

    def _current_score_weights(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        for key, value_var in self.weight_vars.items():
            raw_value = value_var.get().strip()
            if not raw_value:
                raise ValueError(f"Weight '{key}' cannot be blank.")
            try:
                weights[key] = float(raw_value)
            except ValueError as exc:
                raise ValueError(f"Weight '{key}' must be a number.") from exc
        return weights

    def copy_weights_to_clipboard(self) -> None:
        try:
            weights = self._current_score_weights()
        except ValueError as exc:
            messagebox.showerror("Invalid weights", str(exc))
            return

        lines = ["SCORE_WEIGHTS = {"]
        for key in ["production", "trophies", "cups", "grit", "positionFit", "hallOfFame", "goalieQuality"]:
            lines.append(f'    "{key}": {weights[key]:g},')
        lines.append("}")
        clipboard_text = "\n".join(lines)

        self.root.clipboard_clear()
        self.root.clipboard_append(clipboard_text)
        self.root.update_idletasks()
        self.status_var.set("Weights copied to clipboard.")

    def score_current_lineup(self) -> None:
        try:
            lineup, display_lines = self._current_lineup_payload()
        except ValueError as exc:
            self.status_var.set(str(exc))
            self._render_output(str(exc))
            return

        if not lineup:
            self.status_var.set("No players selected yet.")
            self._render_output("No players selected yet. Pick players for one or more slots and score again.")
            return

        try:
            weights = self._current_score_weights()
            result = score_lineup(lineup, weights=weights)
        except Exception as exc:  # pragma: no cover - surfaced in UI
            message = f"Scoring failed: {exc}"
            self.status_var.set(message)
            self._render_output(message)
            return

        self.status_var.set(f"Scored {len(lineup)} player(s): {result['grade']} / {result['totalScore']}")
        self._render_output(self._format_score_output(result, display_lines))

    def _format_score_output(self, result: dict[str, Any], display_lines: list[str]) -> str:
        lines: list[str] = []
        lines.append(f"Total score: {result['totalScore']}")
        lines.append(f"Grade: {result['grade']}")
        lines.append(f"Equation: {result['finalScoreEquation']}")
        lines.append("")
        lines.append("Selected lineup:")
        if display_lines:
            lines.extend(f"  {line}" for line in display_lines)
        else:
            lines.append("  <empty>")

        lines.append("")
        lines.append("Component breakdown:")
        for key, value in result.get("breakdown", {}).items():
            lines.append(f"  {key}: {value}")

        lines.append("")
        lines.append("Weighted contribution:")
        for key, value in result.get("weightedContribution", {}).items():
            lines.append(f"  {key}: {value}")

        bonuses = result.get("bonuses", [])
        penalties_applied = result.get("penaltiesApplied", [])
        penalties = result.get("penalties", [])
        warnings = result.get("warnings", [])

        lines.append("")
        lines.append("Adjustments:")
        if bonuses:
            lines.append("  Bonuses:")
            for item in bonuses:
                lines.append(f"    + {item['label']}: {item['points']}")
        else:
            lines.append("  Bonuses: none")

        if penalties_applied:
            lines.append("  Penalties applied:")
            for item in penalties_applied:
                lines.append(f"    - {item['label']}: {item['points']}")
        else:
            lines.append("  Penalties applied: none")

        if penalties:
            lines.append("")
            lines.append("Penalty notes:")
            for penalty in penalties:
                lines.append(f"  - {penalty}")

        if warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in warnings:
                lines.append(f"  - {warning}")

        player_breakdown = result.get("playerBreakdown", [])
        if player_breakdown:
            lines.append("")
            lines.append("Per-player breakdown:")
            for entry in player_breakdown:
                breakdown = entry.get("breakdown", {})
                lines.append(f"  {entry['slot']}: {entry['playerName']} ({entry['playerId']})")
                lines.append(
                    "    "
                    f"production={breakdown.get('production', 0)} "
                    f"awards={breakdown.get('awards', 0)} "
                    f"cups={breakdown.get('cups', 0)} "
                    f"grit={breakdown.get('grit', 0)} "
                    f"hallOfFame={breakdown.get('hallOfFame', 0)} "
                    f"positionFit={breakdown.get('positionFit', 0)}"
                )

        lines.append("")
        lines.append("Raw response:")
        lines.append(json.dumps(result, indent=2))
        return "\n".join(lines)

    def _render_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", END)
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")


def main() -> None:
    root = Tk()
    try:
        ScoreWorkbenchApp(root)
    except Exception as exc:
        messagebox.showerror("NHL Score Workbench", str(exc))
        root.destroy()
        raise SystemExit(1) from exc

    root.mainloop()


if __name__ == "__main__":
    main()