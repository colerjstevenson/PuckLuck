import type { Category } from "../types";

type CategoryTileProps = {
  title: string;
  category: Category | null;
  disabled?: boolean;
  onRespin?: () => void;
  spinning?: boolean;
};

export function CategoryTile({ title, category, disabled, onRespin, spinning }: CategoryTileProps) {
  return (
    <div className="category-wrap">
      <div className="category-title">{title}</div>
      <div className={`category-tile${spinning ? " spinning" : ""}`}>
        <p className="category-status">{spinning ? "Shuffling" : "Locked In"}</p>
        <p className="category-group">{category?.group ?? "Waiting"}</p>
        <p className="category-label">{category?.label ?? "Waiting for round"}</p>
      </div>
      {onRespin ? (
        <button className="respin-side" type="button" onClick={onRespin} disabled={disabled}>
          Respin This
        </button>
      ) : null}
    </div>
  );
}
