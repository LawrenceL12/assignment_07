"""
menus.py — Part 1, Step 3: three scrapes and our own menu, as one dataset.

The scrapers return lists of dicts in each café's own words. This step makes them
one table everyone downstream can trust — the same columns for every café, and
every category labelled a drink or a food:

    cafe  category  kind  item  size  price

(Every café uses the same sizes — S, M, L for drinks, "Each" for food — so there
is nothing to translate.)

Our own menu (data/salt_city_menu.csv) goes in the same table, under
"Salt City Coffee", so comparing prices later is one table, not two.

No walkthrough here: the docstrings say what each function returns, and
tests/test_pipeline.py says how it is checked.
"""

import pandas as pd

from .settings import (
    CATEGORIES_FILE,
    MENU_COLUMNS,
    OUR_CAFE,
    OUR_MENU_FILE,
)


def load_our_menu() -> pd.DataFrame:
    """Salt City Coffee's menu with the scrapers' five columns.  *(Provided.)*"""
    ours = pd.read_csv(OUR_MENU_FILE)
    return pd.DataFrame({
        "cafe": OUR_CAFE,
        "category": ours["category"],
        "item": ours["item"],
        "size": ours["size"],
        "price": ours["price"],
    })


def menus_table(rows: list[dict]) -> pd.DataFrame:
    """Scraped rows as a DataFrame with exactly these columns, in this order:
    `cafe`, `category`, `item`, `size`, `price`.

    Extra keys a scraper might add are left out. An empty list gives an empty
    table that still has the five columns.
    """
    cols = ["cafe", "category", "item", "size", "price"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows)
    return df[cols]


def add_kinds(menus: pd.DataFrame, categories: pd.DataFrame) -> pd.DataFrame:
    """`menus` plus a `kind` column ("drink" or "food"): each row's (`cafe`,
    `category`) looked up in `categories` (data/categories.csv).

    Every row is kept, in order (a one-sided merge). A category that is not in
    `categories` gets a missing kind. `menus` itself is not changed.
    """
    return menus.merge(categories, on=["cafe", "category"], how="left")


def build_dataset(rival_rows: list[dict]) -> pd.DataFrame:
    """The whole dataset: our menu first, then the rivals' rows, as one table.

    `pd.concat` our menu (`load_our_menu()`) with `menus_table(rival_rows)`, then
    `add_kinds` with data/categories.csv. The columns are settings.MENU_COLUMNS,
    in that order; plain index.
    """
    ours = load_our_menu()
    theirs = menus_table(rival_rows)
    combined = pd.concat([ours, theirs], ignore_index=True)
    categories = pd.read_csv(CATEGORIES_FILE)
    with_kinds = add_kinds(combined, categories)
    return with_kinds[MENU_COLUMNS].reset_index(drop=True)
