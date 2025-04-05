
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

BASE_URL = "https://vintage.grcmc.org"

st.set_page_config(page_title="WYCE Playlist Scraper", layout="centered")
st.title("📻 WYCE DJ Playlist Scraper")

dj_input = st.text_input("Enter DJ profile URL (just the number, e.g. `9` for Lee):", value="9")
dj_name = st.text_input("Optional: DJ Name (for filename)", value="lee")

if st.button("Scrape Playlists"):
    profile_url = f"{BASE_URL}/wyce/programmer-profile/{dj_input}/placeholder"
    st.write(f"🔍 Fetching playlists from: {profile_url}")
    all_songs = []

    try:
        resp = requests.get(profile_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = soup.select("a[href*='/wyce/playlists/shiftId/']")
        shift_urls = set()

        for a in anchors:
            href = a.get("href", "")
            if "/wyce/playlists/shiftId/" in href and href.count("/") >= 5:
                full_url = BASE_URL + href
                shift_urls.add(full_url)

        shift_urls = sorted(shift_urls, reverse=True)
        progress = st.progress(0)
        status = st.empty()

        for i, url in enumerate(shift_urls):
            try:
                res = requests.get(url, timeout=30)
                time.sleep(1)
                soup = BeautifulSoup(res.text, "html.parser")
                articles = soup.select("article.content-item-wrapper")
                for idx, article in enumerate(articles, start=1):
                    artist = article.find("h1")
                    title = article.find("strong")
                    album = article.find("em")

                    raw_text = article.get_text(separator=" ", strip=True)
                    match = re.search(r"\b(19|20)\d{2}\b", raw_text)
                    year = match.group(0) if match else ""

                    label = ""
                    if "via" in raw_text:
                        parts = raw_text.split("via")
                        if len(parts) > 1:
                            label = parts[-1].strip()
                            label = label.replace("rate it!", "").replace("share it!", "").strip()

                    playlist_base = url.split("/")[-1]
                    playlist_date = f"{playlist_base}-{idx:02d}"

                    all_songs.append({
                        "Artist": artist.text.strip() if artist else "",
                        "Song Title": title.text.strip() if title else "",
                        "Album": album.text.strip() if album else "",
                        "Year": year,
                        "Record Label": label,
                        "Playlist Date": playlist_date
                    })
            except Exception as e:
                st.write(f"⚠️ Error scraping {url}: {e}")

            progress.progress((i + 1) / len(shift_urls))
            status.text(f"Scraped {i + 1} of {len(shift_urls)} playlists")

        if all_songs:
            df = pd.DataFrame(all_songs)
            df["Track"] = df["Artist"].str.strip() + " - " + df["Song Title"].str.strip()
            top_songs = df["Track"].value_counts().head(25).reset_index()
            top_songs.columns = ["Song", "Times Played"]

            top_artists = df["Artist"].str.strip().value_counts().head(25).reset_index()
            top_artists.columns = ["Artist", "Times Played"]

            # Store in session state
            st.session_state["df"] = df
            st.session_state["top_songs"] = top_songs
            st.session_state["top_artists"] = top_artists
            st.session_state["dj_name"] = dj_name

    except Exception as e:
        st.error(f"❌ Failed to scrape profile: {e}")

# ------------------- Always Show Downloads if Available -----------------------
if "df" in st.session_state:
    st.success(f"✅ Scraped {len(st.session_state['df'])} songs!")

    csv = st.session_state["df"].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Full Playlist CSV",
        data=csv,
        file_name=f"{st.session_state['dj_name']}_playlists.csv",
        mime="text/csv",
    )

    st.subheader("🎶 Top 25 Songs Played")
    st.dataframe(st.session_state["top_songs"])
    st.download_button(
        "⬇️ Download Top 25 Songs CSV",
        data=st.session_state["top_songs"].to_csv(index=False).encode("utf-8"),
        file_name=f"{st.session_state['dj_name']}_top25_songs.csv",
        mime="text/csv"
    )

    st.subheader("🎤 Top 25 Artists Played")
    st.dataframe(st.session_state["top_artists"])
    st.download_button(
        "⬇️ Download Top 25 Artists CSV",
        data=st.session_state["top_artists"].to_csv(index=False).encode("utf-8"),
        file_name=f"{st.session_state['dj_name']}_top25_artists.csv",
        mime="text/csv"
    )
