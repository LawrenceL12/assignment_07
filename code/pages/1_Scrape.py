"""
1_Scrape.py — Part 1: scrape the rivals' menus into one dataset.

The owner picks the cafés, clicks Scrape, and sees what came back: how much was
scraped, every row in one table, and a download of the dataset.

The scraping itself runs in a separate program (code/scrape_menus.py) that
runner.py starts for you — Streamlit and Playwright do not share a process well.
This page only asks for it and shows the result.

Test it: pytest tests/test_pipeline.py -k scrape_page
"""

import os

import pandas as pd
import streamlit as st

from rivals import CAFES, MENUS_FILE, OUR_CAFE, run_scraper

st.title("Salt City: Scrape the Rivals")
st.markdown("Pick the cafés to scrape. Each run replaces the saved dataset.")

cafes = st.multiselect("Cafés", list(CAFES), default=list(CAFES), key="cafes")

if st.button("Scrape", key="scrape"):
    if cafes:
        with st.spinner("Scraping menus..."):
            result = run_scraper(cafes)
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            last_line = lines[-1] if lines else ""
            st.success(last_line)
        else:
            st.error("Scraper failed.")
            st.code(result.stderr[-1500:] if result.stderr else "")

if not os.path.exists(MENUS_FILE):
    st.info("No menus yet — scrape them first.")
    st.stop()

menus = pd.read_csv(MENUS_FILE)
theirs = menus[menus["cafe"] != OUR_CAFE]

c1, c2, c3 = st.columns(3)
c1.metric("Cafés", theirs["cafe"].nunique())
c2.metric("Items", len(theirs[["cafe", "item"]].drop_duplicates()))
c3.metric("Rows", len(theirs))

st.dataframe(menus, hide_index=True)
st.download_button(
    "Download the dataset",
    data=menus.to_csv(index=False),
    file_name="menus.csv",
    mime="text/csv",
    key="download",
)
