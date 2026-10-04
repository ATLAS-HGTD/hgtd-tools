"""
Plot HGTD modules (front + back quadrants) as rectangles,
coloured by SU_type.

Geometry rules
--------------
* The (x, y) stored in the plot-reference CSVs is the position of the
  **center of the long edge** (inner edge) of each module.
* Bare module dimensions: 39.9 mm  ×  21.8 mm
* Orientation per quadrant:
      - Rows  1 .. 14 :  module long axis is HORIZONTAL
      - Rows 15 .. 21 :  module long axis is VERTICAL ("twisted")
* Global coordinates (for separate plotting):
      - Front: x > 0, y > 0 (Quadrant 1)
      - Back:  x < 0, y > 0 (Quadrant 4)
* View transformations:
      - Combined: Uses global coordinates (Back swapped to overlap in Q1).
* Zoomed view: Applies tighter limits (-50, 700) for detailed inspection
  of the inner module layers.
"""

import os

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

# ------------------------------------------------------------------
# Module dimensions (mm)
# ------------------------------------------------------------------
BARE_LENGTH = 39.9  # Long edge
BARE_WIDTH = 21.8  # Short edge

BACK_PLOT = "Back-Back_to_plot_module_reference.csv"
FRONT_PLOT = "Front-Front_to_plot_module_reference.csv"
BACK_QUAD = "fullBackQuadrant.csv"
FRONT_QUAD = "fullFrontQuadrant.csv"
SLOT_TABLE_DIR = "/Users/annikastein/Documents/PostDoc/HGTD/DB/SlotTable/"
MODULE_REF_DIR = "/Users/annikastein/Documents/PostDoc/HGTD/DB/SlotTable/To_plot_module_reference/"


def load_data():
    """Load and merge the four CSVs into one DataFrame."""
    # Load plot references (delimited by ;)
    back_plot = pd.read_csv(os.path.join(MODULE_REF_DIR, BACK_PLOT), sep=";")
    front_plot = pd.read_csv(os.path.join(MODULE_REF_DIR, FRONT_PLOT), sep=";")

    # Load slot tables (delimited by ,)
    back_quad = pd.read_csv(os.path.join(SLOT_TABLE_DIR, BACK_QUAD), sep=",")
    front_quad = pd.read_csv(os.path.join(SLOT_TABLE_DIR, FRONT_QUAD), sep=",")

    # Standardize column names
    back_plot.columns = ["x", "y", "row", "mod"]
    front_plot.columns = ["x", "y", "row", "mod"]

    # Merge to get SU_type.
    keep_cols = [c for c in back_quad.columns if "FT_Length" not in c]
    back = back_plot.merge(back_quad[keep_cols], left_on=["row", "mod"], right_on=["Row", "Module"])

    front = front_plot.merge(
        front_quad[keep_cols], left_on=["row", "mod"], right_on=["Row", "Module"]
    )

    # Tag each side
    back["side"] = "Back"
    front["side"] = "Front"

    return pd.concat([back, front], ignore_index=True)


def orientation(row: int) -> str:
    """Rows 1-14 horizontal, rows 15-21 vertical."""
    return "horizontal" if row <= 14 else "vertical"


def plot_modules(
    combined: pd.DataFrame,
    outfile: str = "ft_modules.png",
    title: str = "Modules",
    invert_x: bool = False,
    zoom: bool = False,
):
    """Draw each module as a rectangle coloured by SU_type."""
    if combined.empty:
        print(f"No modules to plot for {title}")
        return

    su_types = sorted(combined["SU_type"].unique())
    n_types = len(su_types)
    cmap = plt.get_cmap("hsv")
    colours = [cmap(i / n_types) for i in range(n_types)]
    color_map = dict(zip(su_types, colours))

    fig, ax = plt.subplots(figsize=(18, 10))

    for _, r in combined.iterrows():
        x_ref, y_ref = r["x"], r["y"]
        ori = orientation(r["row"])
        side = r["side"]

        # View from backside: move around the disk to the backside.
        # "What was left is now right" -> mirror x.
        # "Up stays up" -> y remains negative (or positive if viewed from back).
        # We transform x -> -x for the standalone back view.
        if invert_x:
            x_ref = -x_ref

        # Reference point is the center of the long edge (inner edge).
        # Horizontal: Long edge at y_ref.
        x0, y0 = x_ref, y_ref

        if ori == "horizontal":
            w, h = BARE_LENGTH, BARE_WIDTH
            # Adjust x to be left of center, y is bottom
            x0 = x_ref - BARE_LENGTH / 2
            y0 = y_ref
        else:  # vertical
            w, h = BARE_WIDTH, BARE_LENGTH
            # Reference coordinate represents the right edge center for back modules.
            # This means the module extends to the left of the reference point.
            # This preserves the "inner edge" connection to the origin for the back view.
            if invert_x and side == "Back":
                x0 = x_ref - BARE_WIDTH
            else:
                x0 = x_ref

            y0 = y_ref - BARE_LENGTH / 2

        rect = patches.Rectangle(
            (x0, y0),
            w,
            h,
            linewidth=0.3,
            edgecolor="black",
            facecolor=color_map[r["SU_type"]],
            alpha=0.85,
        )
        ax.add_patch(rect)

    # Adjust limits to fit the data nicely
    if zoom:
        ax.set_xlim(-50, 700)
        ax.set_ylim(-50, 700)
    else:
        ax.set_xlim(-700, 700)
        ax.set_ylim(-700, 700)

    ax.set_aspect("equal")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_title(f"Modules — {title}")

    handles = [Patch(facecolor=color_map[st], edgecolor="black", label=st) for st in su_types]
    ax.legend(
        handles=handles,
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        title="SU_type",
        fontsize=7,
        ncol=2,
        frameon=True,
    )

    plt.tight_layout()
    plt.savefig(outfile, dpi=120, bbox_inches="tight")
    plt.close(fig)  # Close figure to allow script to continue generating others
    print(f"Saved: {outfile}")


def main():
    combined = load_data()
    print(f"Loaded {len(combined)} modules ({combined['side'].value_counts().to_dict()})")
    print(f"Distinct SU_types: {combined['SU_type'].nunique()}")

    # Filter subsets for additional views
    front = combined[combined["side"] == "Front"]
    back = combined[combined["side"] == "Back"]
    front_rows_1_3 = front[front["row"] <= 3]
    front_peb_3f = front[front["PEB_type"] == "3F"]

    # 1. Combined (Front in Q1, Back in Q3 - original coordinates) -> Uses zoomed view
    plot_modules(combined, "ft_modules_combined.png", "Front & Back Combined", zoom=True)

    # 2. Front Only
    plot_modules(front, "ft_modules_front.png", "Front Quadrant Only")

    # 3. Back Only (Transformed x to negative, vertical modules use right edge center)
    plot_modules(back, "ft_modules_back.png", "Back Quadrant Only (x < 0, y > 0)", invert_x=True)

    # 4. First Three Rows of Front
    plot_modules(front_rows_1_3, "ft_modules_front_rows_1_3.png", "Front - Rows 1-3")

    # 5. PEB Type 3F on Front
    plot_modules(front_peb_3f, "ft_modules_front_peb_3f.png", "Front - PEB Type 3F")


if __name__ == "__main__":
    main()
