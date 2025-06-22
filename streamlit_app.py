import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="SEBI Circulars & Regulation Updates", layout="wide")

SEBI_FEED_URL = "https://www.sebi.gov.in/sebirss.xml"

# Keywords to filter for
KEYWORDS = [
    "circular",
    "master circular",
    "regulation",
    "regulations",
    "amendment",
    "amendments",
]

def fetch_sebi_feed(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.content

def parse_sebi_feed(xml_content):
    root = ET.fromstring(xml_content)
    items = []
    for item in root.findall("./channel/item"):
        title = item.findtext("title", default="")
        link = item.findtext("link", default="")
        pub_date = item.findtext("pubDate", default="")
        description = item.findtext("description", default="")
        items.append({
            "title": title,
            "link": link,
            "pub_date": pub_date,
            "description": description,
        })
    return items

def is_keyword_present(text):
    text_lower = text.lower()
    return any(re.search(r"\b{}\b".format(re.escape(word)), text_lower) for word in KEYWORDS)

def filter_items(items, weeks=3):
    filtered = []
    now = datetime.utcnow()
    start_date = now - timedelta(weeks=weeks)
    for item in items:
        # Try several date formats
        pub_date = item["pub_date"]
        dt = None
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(pub_date, fmt)
                break
            except Exception:
                continue
        # fallback: skip if can't parse date
        if not dt:
            continue
        # Convert tz-aware to naive UTC if necessary
        if dt.tzinfo:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        if dt < start_date:
            continue
        # Check keyword in title or description
        if is_keyword_present(item["title"]) or is_keyword_present(item["description"]):
            item_cpy = item.copy()
            item_cpy["pub_date_obj"] = dt
            filtered.append(item_cpy)
    # Sort by date, latest first
    filtered.sort(key=lambda x: x["pub_date_obj"], reverse=True)
    return filtered

def main():
    st.title("SEBI Circulars, Master Circulars, and Regulation Updates (Last 3 Weeks)")
    st.write("This application fetches and displays SEBI's circulars, master circulars, new regulations, and amendments from the past 3 weeks. Data is sourced from [SEBI RSS Feed](https://www.sebi.gov.in/sebirss.xml).")

    with st.spinner("Fetching SEBI feed..."):
        try:
            xml_content = fetch_sebi_feed(SEBI_FEED_URL)
            items = parse_sebi_feed(xml_content)
            filtered = filter_items(items, weeks=3)
        except Exception as e:
            st.error(f"Failed to fetch or parse SEBI feed: {e}")
            return

    if not filtered:
        st.info("No recent circulars, master circulars, or regulation/amendment updates found in the last 3 weeks.")
        return

    # Display results
    for idx, item in enumerate(filtered, 1):
        st.markdown(f"### {idx}. [{item['title']}]({item['link']})")
        st.write(f"**Published:** {item['pub_date_obj'].strftime('%d %b %Y, %H:%M:%S')}")
        st.write(item['description'])
        st.markdown("---")

    # Optionally, show as a table
    with st.expander("Show as table"):
        import pandas as pd
        df = pd.DataFrame([
            {
                "Title": item["title"],
                "Published": item["pub_date_obj"].strftime("%d-%m-%Y %H:%M"),
                "Link": item["link"],
            } for item in filtered
        ])
        st.dataframe(df)

if __name__ == "__main__":
    main()
