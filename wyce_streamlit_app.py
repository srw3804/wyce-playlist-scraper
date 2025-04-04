import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from io import StringIO

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
            csv = df.to_csv(index=False).encode("utf-8")
            st.success(f"✅ Scraped {len(all_songs)} songs!")
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"{dj_name}_playlists.csv",
                mime="text/csv",
            )
        else:
            st.warning("⚠️ No songs found.")

    except Exception as e:
        st.error(f"❌ Failed to scrape profile: {e}")
