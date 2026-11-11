"""
matching.py — Part 2: which of their items are ours?

Lakeshore calls it a "Caffe Mocha", Hilltop a "Mocha Cappuccino", Canal Street a
"Mochaccino", and we call it a "Mocha Latte". Before anyone can compare prices,
every rival item needs one name — ours when it is something we sell, its own
when it is not.

No score can do that alone. Fuzzy matching scores how alike two *strings* are, not
whether two *drinks* are the same: "Matcha Latte" scores 87 against "Mocha Latte"
and is a different drink; "PSL" scores 0 against "Pumpkin Spice Latte" and is the
same one. So the code proposes and the owner decides:

- a score of settings.AUTO_MATCH or more is matched automatically;
- anything lower waits for the owner, who sees the top suggestions on the Review
  page and picks one, or says it is a new item;
- the owner's decisions are saved (data/item_matches.csv) and win every time,
  so next month's scrape does not ask the same questions again.

The steps are described in words. You write the code.
"""

import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz, process

from .settings import (
    AUTO_MATCH,
    DECISION_COLUMNS,
    FILLER_WORDS,
    NEW_ITEM,
    OUR_CAFE,
    REVIEW,
)


def normalize_name(name: str) -> str:
    """A menu name reduced to the words that tell items apart.

        normalize_name("Caffè Americano")    ->  "americano"
        normalize_name("Cold-Brew Coffee")   ->  "cold brew"
        normalize_name("Bagel w/ Cream Cheese") -> "bagel cream cheese"

    How to build it:

    - Strip accents: `unicodedata.normalize("NFKD", name).encode("ascii",
      "ignore").decode()` turns "è" into "e".
    - Lowercase, then replace everything that is not a letter, digit or space with
      a space: `re.sub(r"[^a-z0-9 ]+", " ", text)`.
    - Split into words, drop the ones in settings.FILLER_WORDS, and join the rest
      with single spaces.
    """
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9 ]+", " ", stripped.lower())
    words = [w for w in text.split() if w not in FILLER_WORDS]
    return " ".join(words)


def top_candidates(name: str, choices: list[str], limit: int = 3) -> list[tuple]:
    """The `limit` choices most like `name`, best first, as (choice, score) pairs.

        top_candidates("Americano, Iced", ["Americano", "Iced Americano", "Latte"])
        -> [("Iced Americano", 100), ("Americano", 78), ("Latte", 24)]

    Scores are whole numbers 0–100 from rapidfuzz's `fuzz.token_sort_ratio`, which
    ignores word order ("Croissant, Almond" = "Almond Croissant"). Both sides are
    compared *normalized*, but the pairs hold the original choice names. No
    choices gives an empty list.

    How to build it:

    - Normalize `name` and every choice.
    - `process.extract(normalized_name, normalized_choices,
      scorer=fuzz.token_sort_ratio, limit=limit)` returns (match, score, index)
      tuples, best first. The index says which original choice it was.
    - Return `(choices[index], round(score))` for each.
    """
    if not choices:
        return []
    normalized_name = normalize_name(name)
    normalized_choices = [normalize_name(c) for c in choices]
    matches = process.extract(
        normalized_name,
        normalized_choices,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
    )
    return [(choices[index], round(score)) for _, score, index in matches]


def match_band(score: float) -> str:
    """How sure a score is: "auto" at settings.AUTO_MATCH or more, "review" at
    settings.REVIEW or more, otherwise "unlikely".

    The Review page preselects the top suggestion for "review" and NEW_ITEM for
    "unlikely"; "auto" never reaches the owner.

    How to build it:

    - Two `if`s and a `return`: compare `score` to `AUTO_MATCH` first, then
      `REVIEW` (both imported from settings — don't type 90 and 70).
    """
    if score >= AUTO_MATCH:
        return "auto"
    if score >= REVIEW:
        return "review"
    return "unlikely"


def match_items(menus: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame:
    """One row per rival item: what it is called on our list, and who decided.

    `menus` is the dataset from build_dataset; `decisions` is data/item_matches.csv
    (columns `cafe`, `item`, `matched_to`). Returns, one row per distinct
    (`cafe`, `item`) that is not ours, in the order they first appear in `menus`:

        cafe  item  kind  status  matched_to  score  suggestions

    - `suggestions`: top_candidates(item, the names on the list so far of the same
      `kind`) — a list of (name, score) pairs. `score` is the first pair's score
      (0 when there are no suggestions).
    - `status` and `matched_to`:
        - "owner" when the owner has decided this (cafe, item): `matched_to` is
          their answer — or the item's own name when they answered NEW_ITEM.
        - otherwise "auto" when `score` is AUTO_MATCH or more: the top suggestion.
        - otherwise "unreviewed", and `matched_to` is None.

    "The list" starts as our own item names (with their kinds) and grows: an item
    that ends up matched to a name not yet on the list adds it. That is how
    Lakeshore's "Avocado Toast" — not ours — becomes the name Hilltop's
    "Avocado Toast" matches. Unreviewed items add nothing.

    How to build it (nearly line by line):

    - The list so far: `ours` <- the rows of `menus` whose cafe is OUR_CAFE.
      `pool = dict(zip(ours["item"], ours["kind"]))` — {name: kind}.
    - The owner's answers: `answers` — a dict {(cafe, item): matched_to}, one
      entry per row of `decisions` (loop over `decisions.to_dict("records")`).
    - The rival items, once each, in order: `theirs` <- the rows of `menus` whose
      cafe is *not* OUR_CAFE; `rivals = theirs[["cafe", "item", "kind"]]
      .drop_duplicates()`.
    - `rows = []`, then `for cafe, item, kind in rivals.itertuples(index=False):`
        - `choices` <- the names in `pool` whose kind equals `kind`
          (a list comprehension over `pool.items()`).
        - `suggestions = top_candidates(item, choices)`;
          `score` <- `suggestions[0][1]` if there are any suggestions, else 0.
        - Decide, in this order:
            - `(cafe, item)` is in `answers`: status "owner"; `matched_to` is the
              answer — or `item` itself when the answer is NEW_ITEM.
            - else `score >= AUTO_MATCH`: status "auto"; `matched_to` is the top
              suggestion's name, `suggestions[0][0]`.
            - else: status "unreviewed"; `matched_to = None`.
        - Grow the list: if `matched_to` is not None and not already in `pool`,
          `pool[matched_to] = kind`.
        - `rows.append({...})` with the seven keys.
    - `return pd.DataFrame(rows, columns=[...the seven columns...])` — naming the
      columns keeps them in order.
    """
    ours = menus[menus["cafe"] == OUR_CAFE]
    pool = dict(zip(ours["item"], ours["kind"]))
    answers = {
        (row["cafe"], row["item"]): row["matched_to"]
        for row in decisions.to_dict("records")
    }
    theirs = menus[menus["cafe"] != OUR_CAFE]
    rivals = theirs[["cafe", "item", "kind"]].drop_duplicates()
    rows = []
    for cafe, item, kind in rivals.itertuples(index=False):
        choices = [name for name, k in pool.items() if k == kind]
        suggestions = top_candidates(item, choices)
        score = suggestions[0][1] if suggestions else 0
        if (cafe, item) in answers:
            status = "owner"
            ans = answers[(cafe, item)]
            matched_to = item if ans == NEW_ITEM else ans
        elif score >= AUTO_MATCH:
            status = "auto"
            matched_to = suggestions[0][0]
        else:
            status = "unreviewed"
            matched_to = None
        if matched_to is not None and matched_to not in pool:
            pool[matched_to] = kind
        rows.append({
            "cafe": cafe,
            "item": item,
            "kind": kind,
            "status": status,
            "matched_to": matched_to,
            "score": score,
            "suggestions": suggestions,
        })
    columns = [
        "cafe",
        "item",
        "kind",
        "status",
        "matched_to",
        "score",
        "suggestions",
    ]
    return pd.DataFrame(rows, columns=columns)


def record_decision(
    decisions: pd.DataFrame, cafe: str, item: str, matched_to: str
) -> pd.DataFrame:
    """`decisions` with the owner's answer for (cafe, item) — replacing any earlier
    answer for the same item, never duplicating it.

    Returns a new DataFrame with columns settings.DECISION_COLUMNS (`cafe`, `item`,
    `matched_to`), the new answer last, plain index. `decisions` is not changed.

    How to build it:

    - Keep the rows of `decisions` that are *not* this (cafe, item) (a boolean filter).
    - `pd.concat` them with a one-row DataFrame of the new answer; reset the index.
      (When nothing is kept, the one-row DataFrame is the answer.)
    """
    new_row = pd.DataFrame(
        [{"cafe": cafe, "item": item, "matched_to": matched_to}],
        columns=DECISION_COLUMNS,
    )
    if not decisions.empty:
        kept = decisions[~((decisions["cafe"] == cafe) & (decisions["item"] == item))]
    else:
        kept = pd.DataFrame(columns=DECISION_COLUMNS)
    return pd.concat([kept, new_row], ignore_index=True)
