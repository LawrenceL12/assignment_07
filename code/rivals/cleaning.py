"""
cleaning.py — Part 1, Step 1: turn scraped text into clean values.

A scraper hands you whatever the page shows a person, and pages are written for
people. Lakeshore Lattes' menu cards are a good example — `inner_text()` on one
card gives you:

    NEW!
    Matcha Latte
    V
    S $5.05 · L $6.25
    Ceremonial-grade matcha whisked with steamed milk.

A badge, a dietary tag, two sizes and two prices crammed onto one line. These
functions turn that into rows a DataFrame can hold. They are plain Python — no
browser — so they are quick to test and quick to fix.

Every café names its drink sizes S, M and L (Lakeshore pours only S and L); food
has one price, which we call "Each".

This step is walked through line by line. The scrapers give you less help.
"""

import re

# Lines on a menu card that are decoration, not data.
NOISE = {"NEW!", "NEW", "V", "GF"}


def clean_price(text: str) -> float:
    """A price as a number: "$4.75" -> 4.75, " $1,029.00 " -> 1029.0.

    How to build it:

    - Remove the dollar sign and any commas with `.replace()`.
    - `.strip()` the spaces, then convert with `float()`.
    """
    cleaned = text.replace("$", "").replace(",", "").strip()
    return float(cleaned)


def clean_card_lines(text: str) -> list[str]:
    """The useful lines of a menu card, in order, with the decoration removed.

        clean_card_lines("NEW!\\n\\nAvocado Toast\\nV GF\\n$8.50\\nToast.")
        -> ["Avocado Toast", "$8.50", "Toast."]

    Remove: blank lines, and lines made only of NOISE words (badges like "NEW!"
    and dietary tags like "V" or "V GF").

    How to build it:

    - `text.split("\\n")` gives a list of lines. Loop over it.
    - `.strip()` each line. Skip it if it is empty.
    - Skip it if every word in it is in NOISE: `all(w in NOISE for w in line.split())`.
    - Otherwise append it to a list, and return the list.
    """
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if all(w in NOISE for w in stripped.split()):
            continue
        lines.append(stripped)
    return lines


def parse_price_line(line: str) -> list[tuple[str, float]]:
    """Every (size, price) pair on a price line.

        parse_price_line("S $5.05 · L $6.25")
        -> [("S", 5.05), ("L", 6.25)]
        parse_price_line("S $2.15 · M $2.60 · L $3.05")
        -> [("S", 2.15), ("M", 2.60), ("L", 3.05)]
        parse_price_line("$8.50")
        -> [("Each", 8.50)]

    A price with no size in front of it is "Each".

    How to build it:

    - `re.findall(r"([SML])?\\s*(\\$[\\d.,]+)", line)` finds every price, and the
      size letter in front of it if there is one. Each match is a tuple
      (size, price), with size "" when there is none.
    - Loop over the matches. Use "Each" when size is "", and `clean_price()` on the
      price. Return the list of pairs.
    """
    matches = re.findall(r"([SML])?\s*(\$[\d.,]+)", line)
    results = []
    for size, price_str in matches:
        s = size if size else "Each"
        results.append((s, clean_price(price_str)))
    return results


def card_rows(cafe: str, category: str, card_text: str) -> list[dict]:
    """One row per size for one menu card.

        card_rows("Lakeshore Lattes", "Tea & More", "NEW!\\nMatcha Latte\\nV\\n"
                  "S $5.05 · L $6.25\\nMatcha.")
        -> [{"cafe": "Lakeshore Lattes", "category": "Tea & More",
             "item": "Matcha Latte", "size": "S", "price": 5.05},
            {... "size": "L", "price": 6.25}]

    How to build it:

    - `clean_card_lines()` the text. The first line is the item's name. The price
      line is the first line with a "$" in it — usually the second, but don't
      count on it.
    - `parse_price_line()` the price line, and build one dict per (size, price)
      pair with the five keys above. Return the list.
    """
    lines = clean_card_lines(card_text)
    item = lines[0]
    price_line = next(line for line in lines if "$" in line)
    pairs = parse_price_line(price_line)
    return [
        {
            "cafe": cafe,
            "category": category,
            "item": item,
            "size": size,
            "price": price,
        }
        for size, price in pairs
    ]
