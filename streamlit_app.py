import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SEBI_FEED_URL = "https://www.sebi.gov.in/sebirss.xml"

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

def parse_pub_date(pub_date):
    # Try multiple date formats
    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b, %Y %z",
        "%d %b, %Y",
        "%Y-%m-%d"
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(pub_date, fmt)
        except Exception:
            continue
    try:
        # Remove timezone if present and try again
        return datetime.strptime(pub_date.split("+")[0].strip(), "%d %b, %Y")
    except Exception:
        pass
    return None

def filter_items(items, weeks=3):
    filtered = []
    now = datetime.utcnow()
    start_date = now - timedelta(weeks=weeks)
    for item in items:
        dt = parse_pub_date(item["pub_date"])
        if not dt:
            continue
        # Convert tz-aware to naive UTC if necessary
        if dt.tzinfo:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        if dt < start_date:
            continue
        if is_keyword_present(item["title"]) or is_keyword_present(item["description"]):
            item_cpy = item.copy()
            item_cpy["pub_date_obj"] = dt
            filtered.append(item_cpy)
    # Sort by date, latest first
    filtered.sort(key=lambda x: x["pub_date_obj"], reverse=True)
    return filtered

def extract_pdf_from_iframe(page_url):
    """
    Given a SEBI webpage URL, extract the first PDF URL from an <iframe> if present.
    Returns the PDF URL as a string, or None if not found.
    """
    try:
        response = requests.get(page_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        iframe = soup.find("iframe", src=True)
        if iframe:
            pdf_url = iframe["src"]
            pdf_url = urljoin(page_url, pdf_url)
            return pdf_url
    except Exception:
        pass
    return None

def main():
    st.set_page_config(page_title="SEBI Circulars/Regulations (Last 3 Weeks)", layout="wide")
    st.title("SEBI Circulars, Master Circulars, Regulations & Amendments")
    st.write("Latest updates from SEBI for circulars, master circulars, regulations and amendments, including PDF extraction if available (last 3 weeks).")
    with st.spinner("Fetching SEBI RSS feed..."):
        try:
            xml_content = fetch_sebi_feed(SEBI_FEED_URL)
            items = parse_sebi_feed(xml_content)
            filtered = filter_items(items, weeks=3)
        except Exception as e:
            st.error(f"Failed to fetch or parse SEBI feed: {e}")
            return

    if not filtered:
        st.info("No relevant SEBI circulars, master circulars, or regulation/amendment updates found in the last 3 weeks.")
        return

    for idx, item in enumerate(filtered, 1):
        st.markdown(f"### {idx}. [{item['title']}]({item['link']})")
        st.write(f"**Published:** {item['pub_date_obj'].strftime('%d %b %Y, %H:%M:%S')}")
        st.write(item['description'])
        # PDF extraction
        with st.spinner("Checking for PDF..."):
            pdf_url = extract_pdf_from_iframe(item["link"])
        if pdf_url and pdf_url.lower().endswith(".pdf"):
            st.markdown(f"[🔗 Download/View PDF]({pdf_url})")
            st.components.v1.iframe(pdf_url, height=600)
        else:
            st.info("No PDF found/linked.")
        st.markdown("---")

    # Option to view as table
    with st.expander("Show as table"):
        import pandas as pd
        df = pd.DataFrame([
            {
                "Title": item["title"],
                "Published": item["pub_date_obj"].strftime("%d-%m-%Y %H:%M"),
                "Link": item["link"],
                "PDF": extract_pdf_from_iframe(item["link"]) or "Not found"
            } for item in filtered
        ])
        st.dataframe(df)

if __name__ == "__main__":
    main()
