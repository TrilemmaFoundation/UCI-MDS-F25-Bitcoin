import streamlit as st
import requests
from datetime import datetime, timedelta
import re
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dashboard.data_loader import load_bitcoin_data
from bs4 import BeautifulSoup


# MicroStrategy (MSTR) configuration - CIK number for SEC EDGAR filings
COMPANY = {
    "name": "MicroStrategy (MSTR)",
    "cik": "1050446",
    "ticker": "MSTR",
    "description": "Largest corporate Bitcoin holder",
    "color": "#F7931A"
}


@st.cache_data(ttl=3600)
def fetch_sec_filings(cik, form_type="8-K", days_back=180):
    """
    Fetch SEC filings from EDGAR API (free, no authentication required)
    
    Args:
        cik: Company CIK number (as string with leading zeros)
        form_type: Type of form to search for (default: 8-K for material events)
        days_back: Number of days to look back
    
    Returns:
        List of filing dictionaries
    """
    try:
        # Format CIK with leading zeros (10 digits)
        cik_formatted = cik.zfill(10)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # SEC EDGAR submissions API endpoint
        # Note: SEC requires a User-Agent header
        headers = {
            "User-Agent": "BTC-Dashboard/1.0 (Educational Dashboard; contact@example.com)",
            "Accept": "application/json"
        }
        
        # Get company submissions
        url = f"https://data.sec.gov/submissions/CIK{cik_formatted}.json"
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        filings = []
        recent_filings = data.get("filings", {}).get("recent", {})
        
        if not recent_filings:
            return filings
        
        # Get form types and filing dates
        form_types = recent_filings.get("form", [])
        filing_dates = recent_filings.get("filingDate", [])
        accession_numbers = recent_filings.get("accessionNumber", [])
        primary_documents = recent_filings.get("primaryDocument", [])
        
        # Filter for specified form type and date range
        for i, (form, date_str, acc_num, doc) in enumerate(
            zip(form_types, filing_dates, accession_numbers, primary_documents)
        ):
            if form == form_type:
                try:
                    filing_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if filing_date >= start_date:
                        # Format accession number (remove dashes)
                        acc_num_clean = acc_num.replace("-", "")
                        
                        filings.append({
                            "form": form,
                            "filingDate": date_str,
                            "filingDateObj": filing_date,
                            "accessionNumber": acc_num,
                            "accessionNumberClean": acc_num_clean,
                            "primaryDocument": doc,
                            "url": f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik_formatted}&accession_number={acc_num}&xbrl_type=v",
                            "documentUrl": f"https://www.sec.gov/Archives/edgar/data/{cik_formatted}/{acc_num_clean}/{doc}"
                        })
                except ValueError:
                    continue
        
        # Sort by date (newest first)
        filings.sort(key=lambda x: x["filingDate"], reverse=True)
        
        return filings
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return []  # Company not found or no filings
        return []
    except Exception as e:
        return []


def extract_k8_post_202503(text: str):
    """
    - 8-K format changed starting Mar 2025 → requires new extraction logic.
    - Handles special cases:
        - Missing entries shown as "—" or "0" → treated as None.
        - Aggregated historical values may appear even if current period is missing.
        - Known special cases: 2025-10-06 and 2025-07-28 8-k reports
    -  Detects "(in millions/billions)" and converts to absolute numeric values
    """
    # Convert text to lowercase for easier matching
    t = text.lower()

    # 1) Locate "btc update" (also matches btcupdate / btc updateon)
    m = re.search(r'btc\s*update(?:\s*on)?', t)
    block = t[m.start():] if m else t

    # 2) Find six headings in order (spacing-flexible; does not rely on "in millions/billions")
    patterns = [
        r'btc\s*acquired',               # 0
        r'aggregate\s*purchase\s*price', # 1
        r'average\s*purchase\s*price',   # 2
        r'aggregate\s*btc\s*holdings',   # 3
        r'aggregate\s*purchase\s*price', # 4
        r'average\s*purchase\s*price',   # 5
    ]

    pos = 0
    ends = []  # end index of each heading within 'block'
    units = {1: 1.0, 4: 1.0}  # used to scale to million or billion later

    for idx, p in enumerate(patterns):
        m = re.search(p, block[pos:], re.I)
        if not m:
            # If heading not found, use end of text as fallback
            ends.append(len(block))
            continue

        end = pos + m.end()
        ends.append(end)

        # Check if this heading has "(in millions/billions)" nearby
        if idx in (1, 4):
            lookahead = block[end:end+80]
            if re.search(r'\(\s*in\s*millions?\s*\)', lookahead, re.I):
                units[idx] = 1e6
            elif re.search(r'\(\s*in\s*billions?\s*\)', lookahead, re.I):
                units[idx] = 1e9

        pos = end

     # 3) Numbers appear after the 6th heading
    tail = block[ends[-1]:]

    # Token rules:
    #   - "$" → ignore
    #   - "—" / "-" → None
    #   - number → float (supports 0, decimals, thousand separators)
    token = re.compile(
        r'\$'
        r'|[—\-–]+'
        r'|(\d{1,3}(?:,\d{3})+|\d+\.\d+|\d+)'
    )

    vals = []
    for m in token.finditer(tail):
        tok = m.group(0).strip()

        # Ignore "$"
        if tok == '$':
            continue

        # Series of dashes → None
        if all(ch in '—-– ' for ch in tok):
            vals.append(None)

        # Numeric token
        elif m.group(1):
            num_str = m.group(1)

            # --- skip common noise: (1) (2)
            if num_str in {"1", "2"}:
                L = tail[max(0, m.start()-2):m.start()]
                R = tail[m.end():m.end()+2]
                # footnote like "(1)" or "(2)" → skip
                if num_str in {"1","2"} and (("(" in L) or (")" in R)):
                    continue

            v = float(num_str.replace(',', ''))

            # For (index 1 and 4), detect million/billion near the number
            idx = len(vals)
            if idx in (1, 4):
                right = tail[m.end(): m.end()+20]
                mu = re.search(r'(million|billion)\b', right, re.I)
                if mu:
                    u = mu.group(1).lower()
                    if u.startswith('million'):
                        v *= 1e6
                    elif u.startswith('billion'):
                        v *= 1e9
                else:
                    # If no inline unit, fallback to heading-based scale
                    v *= units[idx]

            vals.append(v)

        # Stop once six numbers are collected
        if len(vals) == 6:
            break

    # Pad to 6 values
    while len(vals) < 6:
        vals.append(None)

    # Convert 0 → None (after scaling so 0 million stays 0 before turning into None)
    vals = [None if (isinstance(v, (int,float)) and v == 0) else v for v in vals]

    # 4) Return mapped results
    return {
        "btc_acquired": vals[0],
        "purchase_usd": vals[1],
        "average_purchase_usd": vals[2],
        "aggregate_btc_acquired": vals[3],
        "aggregate_purchase_usd": vals[4],
        "aggregate_average_purchase_usd": vals[5]
    }


def extract_k8_pre_202503(text: str):
    pattern = re.compile(
        r'(?:acquired|purchased)\s+'                  # verb
        r'(?:approximately\s+)?'                      # optional "approximately"
        r'([\d,]+(?:\.\d+)?)\s+bitcoin(?:s)?\s+'      # X1 = BTC amount
        r'for\s+(?:approximately\s+)?\$\s*'           # "for $" (allow optional "approximately")
        r'([\d,]+(?:\.\d+)?)'                         # X2 = purchase amount
        r'(?:\s*(million|billion))?'                  # optional unit
        r'(?:\s+in\s+cash)?',                         # optional "in cash"
        re.IGNORECASE
    )

    m = pattern.search(text)
    if not m:
        return {"btc_acquired": None, "purchase_usd": None}

    # ---- BTC amount ----
    x1 = float(m.group(1).replace(",", ""))
    btc_acquired = int(x1) if x1.is_integer() else x1

    # ---- USD amount ----
    x2 = float(m.group(2).replace(",", ""))
    unit = (m.group(3) or "").lower()

    if unit.startswith("million"):
        x2 *= 1e6
    elif unit.startswith("billion"):
        x2 *= 1e9

    return {
        "btc_acquired": btc_acquired,
        "purchase_usd": x2
    }


def parse_filing_for_bitcoin_purchase(filing_url, filing_date):
    """
    Returns:
        dict | None like:
        {
            "purchase_date": "YYYY-MM-DD",
            "btc_amount": <float|int|None>,
            "usd_amount": <float|None>,
            "mentions_bitcoin": True
        }
        - For post-2025-03-31 (inclusive): result comes from "extract_k8_post_202503"
        - For pre-2025-03-31: result comes from "extract_k8_pre_202503"
    """
    try:
        headers = {
            "User-Agent": "BTC-Dashboard/1.0 (Educational Dashboard; contact@example.com)",
            "Accept": "text/html,application/xhtml+xml"
        }
        
        response = requests.get(filing_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text().lower()

        # Check if filing mentions Bitcoin
        if "bitcoin" not in text:
            return None
        
        cutoff = datetime(2025, 3, 31)
        fdate = datetime.strptime(filing_date, "%Y-%m-%d")

        if fdate >= cutoff:
            parsed = extract_k8_post_202503(text)
        else:
            parsed = extract_k8_pre_202503(text)

        if not parsed:
            return None

        btc_amount = parsed.get("btc_acquired")
        usd_amount = parsed.get("purchase_usd")

        # skip non useful rows
        # if btc_amount is None and usd_amount is None:
        #     return None
        
        return {
                "purchase_date": filing_date,
                "btc_amount": btc_amount,
                "usd_amount": usd_amount,
                "mentions_bitcoin": True
            }

    except Exception as e:
        return None


def format_date(date_str):
    """Format date string to readable format"""
    try:
        if isinstance(date_str, datetime):
            return date_str.strftime("%B %d, %Y")
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except:
        return str(date_str)


def create_price_chart_with_purchases(btc_df, purchases, company_name, company_color):
    """
    Create a professional BTC price chart with purchase markers
    Focused on recent data (last 2 years or purchase period)
    """
    if btc_df is None or btc_df.empty:
        return None
    
    # Prepare BTC price data
    btc_df.index = pd.to_datetime(btc_df.index)
    btc_df = btc_df.sort_index()
    
    # Determine date range - focus on purchase period with nice zoom
    today = datetime.now()
    
    # If we have purchases, zoom to show purchase period nicely
    if purchases:
        purchase_dates = []
        for purchase in purchases:
            purchase_date = purchase["purchase_date"]
            if isinstance(purchase_date, str):
                purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d")
            purchase_dates.append(purchase_date)
        
        earliest_purchase = min(purchase_dates)
        latest_purchase = max(purchase_dates)
        
        # Start 1.5 months before earliest purchase, end at today
        chart_start = earliest_purchase - timedelta(days=45)
        chart_end = today
        
        # Ensure we don't go too far back (max 1 year)
        one_year_ago = today - timedelta(days=365)
        chart_start = max(chart_start, one_year_ago)
    else:
        # No purchases - show last 3 months
        chart_start = today - timedelta(days=90)
        chart_end = today
    
    # Filter data to chart range
    btc_df_filtered = btc_df[(btc_df.index >= chart_start) & (btc_df.index <= chart_end)].copy()
    
    if btc_df_filtered.empty:
        # Fallback to last 90 days
        btc_df_filtered = btc_df[btc_df.index >= (today - timedelta(days=90))].copy()
    
    # Calculate 200-period moving average
    # Need to get enough historical data for MA200
    ma200_start = chart_start - timedelta(days=250)  # Extra buffer for MA calculation
    btc_df_for_ma = btc_df[btc_df.index >= ma200_start].copy()
    btc_df_for_ma = btc_df_for_ma.sort_index()
    btc_df_for_ma['MA200'] = btc_df_for_ma['PriceUSD'].rolling(window=200, min_periods=1).mean()
    
    # Filter MA200 to chart range
    ma200_filtered = btc_df_for_ma[btc_df_for_ma.index >= chart_start]['MA200'].copy()
    
    # Create figure
    fig = go.Figure()
    
    # Add MA200 line (blue dashed line) - add first so it appears behind
    fig.add_trace(
        go.Scatter(
            x=ma200_filtered.index,
            y=ma200_filtered.values,
            mode="lines",
            name="MA200",
            line=dict(color="#1f77b4", width=2, dash="dash"),  # Standard blue for MA200
            hovertemplate="<b>%{x|%B %d, %Y}</b><br>MA200: $%{y:,.2f}<extra></extra>",
        )
    )
    
    # Add Historical Price line (orange solid line)
    fig.add_trace(
        go.Scatter(
            x=btc_df_filtered.index,
            y=btc_df_filtered["PriceUSD"],
            mode="lines",
            name="Historical Price",
            line=dict(color="#ff7f0e", width=2.5),  # Standard orange
            hovertemplate="<b>%{x|%B %d, %Y}</b><br>Price: $%{y:,.2f}<extra></extra>",
        )
    )
    
    # Add purchase markers (red solid circles for MSTR purchases)
    if purchases:
        purchase_dates = []
        purchase_prices = []
        purchase_labels = []
        
        for purchase in purchases:
            purchase_date = purchase["purchase_date"]
            if isinstance(purchase_date, str):
                purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d")
            
            # Only show purchases in chart range
            if purchase_date < chart_start:
                continue
                
            if purchase_date in btc_df_filtered.index:
                price = btc_df_filtered.loc[purchase_date, "PriceUSD"]
            else:
                closest_idx = btc_df_filtered.index.get_indexer([purchase_date], method="nearest")[0]
                price = btc_df_filtered.iloc[closest_idx]["PriceUSD"]
                purchase_date = btc_df_filtered.index[closest_idx]
            
            purchase_dates.append(purchase_date)
            purchase_prices.append(price)
            
            # Create label
            label_parts = []
            if purchase.get("btc_amount"):
                label_parts.append(f"{purchase['btc_amount']:,.0f} BTC")
            if purchase.get("usd_amount"):
                label_parts.append(f"${purchase['usd_amount']/1_000_000:.1f}M")
            if not label_parts:
                label_parts.append("Purchase")
            
            purchase_labels.append("<br>".join(label_parts))
        
        if purchase_dates:
            fig.add_trace(
                go.Scatter(
                    x=purchase_dates,
                    y=purchase_prices,
                    mode="markers",
                    name="MSTR Purchases",
                    marker=dict(
                        size=10,
                        color="#d62728",  # Standard red for markers
                        symbol="circle",
                        line=dict(width=0.5, color="#ffffff"),
                        opacity=1.0
                    ),
                    hovertemplate="<b>%{x|%B %d, %Y}</b><br>Price: $%{y:,.2f}<br>%{text}<extra></extra>",
                    text=[label.replace("<br>", " - ") for label in purchase_labels],
                )
            )
    
    # Update layout to match reference image styling
    fig.update_layout(
        height=450,
        title={
            "text": "Price & MA200",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "#f0f6fc", "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"},
            "y": 0.97
        },
        xaxis_title="",
        yaxis_title="Price (USD)",
        yaxis_title_font=dict(size=12, color="#c9d1d9", family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"),
        hovermode="x unified",
        template="plotly_dark",
        plot_bgcolor="#1e1e1e",  # Dark gray background like the image
        paper_bgcolor="#161b22",
        font=dict(color="#c9d1d9", family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif", size=11),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(color="#c9d1d9", size=11),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=0,
            itemsizing="constant"
        ),
        margin=dict(l=60, r=25, t=50, b=45),
    )
    
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.1)",
        showgrid=True,
        zeroline=False,
        showline=False,
        tickfont=dict(color="#8b949e", size=10),
        title_font=dict(color="#8b949e", size=11),
        tickformat="%b %d",
        showspikes=False
    )
    
    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.1)",
        showgrid=True,
        zeroline=False,
        showline=False,
        tickfont=dict(color="#8b949e", size=10),
        title_font=dict(color="#c9d1d9", size=12),
        tickformat="$,.0f",
        showspikes=False
    )
    
    return fig


def main():
    """Main function for BTC Purchase Indicators page"""
    st.set_page_config(
        page_title="BTC Purchase Indicators - BTC Dashboard",
        layout="wide",
        page_icon="₿",
    )
    
    # Professional CSS styling
    st.markdown("""
    <style>
    /* Main app background - professional dark theme */
    .stApp {
        background: #0d1117 !important;
        background-image: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
    }
    
    /* Main container */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
        max-width: 1400px;
    }
    
    /* Typography - professional and clean */
    h1 {
        color: #f0f6fc !important;
        font-size: 2.25rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        margin-bottom: 0.25rem !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    h2 {
        color: #f0f6fc !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    h3 {
        color: #f0f6fc !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        margin-top: 1.25rem !important;
        margin-bottom: 0.5rem !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    /* Company selector - professional styling */
    .stSelectbox > div > div {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        color: #f0f6fc !important;
    }
    
    .stSelectbox label {
        color: #8b949e !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
    }
    
    /* Metric cards - professional financial dashboard style */
    [data-testid="stMetricContainer"] {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.625rem !important;
        font-weight: 600 !important;
        color: #f0f6fc !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        color: #8b949e !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    /* Purchase cards - professional card design */
    .purchase-card {
        background: #161b22 !important;
        padding: 1.25rem !important;
        border-radius: 8px !important;
        border: 1px solid #30363d !important;
        margin: 0.75rem 0 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
    }
    
    .purchase-card:hover {
        border-color: #484f58 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Filing cards - table-like professional design */
    .filing-card {
        background: #161b22 !important;
        padding: 0.875rem 1rem !important;
        border-radius: 6px !important;
        border: 1px solid #30363d !important;
        margin: 0.375rem 0 !important;
        transition: all 0.2s ease !important;
    }
    
    .filing-card:hover {
        border-color: #484f58 !important;
        background: #1c2128 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* Links - professional styling */
    a {
        text-decoration: none !important;
        color: #58a6ff !important;
        transition: color 0.2s ease !important;
    }
    
    a:hover {
        color: #79c0ff !important;
        text-decoration: underline !important;
    }
    
    /* Buttons - professional action buttons */
    .stButton > button {
        background: #238636 !important;
        color: white !important;
        border: 1px solid #2ea043 !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s ease !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    .stButton > button:hover {
        background: #2ea043 !important;
        border-color: #3fb950 !important;
        box-shadow: 0 2px 8px rgba(46, 160, 67, 0.3) !important;
    }
    
    /* Info boxes */
    .stInfo {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-left: 4px solid #58a6ff !important;
        border-radius: 6px !important;
        color: #c9d1d9 !important;
    }
    
    /* Success boxes */
    .stSuccess {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-left: 4px solid #238636 !important;
        border-radius: 6px !important;
        color: #c9d1d9 !important;
    }
    
    /* Warning boxes */
    .stWarning {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-left: 4px solid #d29922 !important;
        border-radius: 6px !important;
        color: #c9d1d9 !important;
    }
    
    /* Remove Streamlit default styling */
    .stMarkdown {
        color: #c9d1d9 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    /* Captions */
    .stCaption {
        color: #8b949e !important;
        font-size: 0.8125rem !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
    }
    
    /* Expander styling - compact and professional */
    .streamlit-expanderHeader {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        color: #c9d1d9 !important;
        font-weight: 500 !important;
        padding: 0.625rem 0.875rem !important;
        font-size: 0.875rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: #1c2128 !important;
        border-color: #484f58 !important;
    }
    
    .streamlit-expanderContent {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
        color: #c9d1d9 !important;
        padding: 0.875rem 1rem !important;
        margin-top: -6px !important;
        margin-bottom: 0.75rem !important;
    }
    
    .streamlit-expanderContent p {
        margin: 0.375rem 0 !important;
        font-size: 0.8125rem !important;
        line-height: 1.6 !important;
        color: #c9d1d9 !important;
    }
    
    .streamlit-expanderContent p:first-child {
        margin-top: 0 !important;
    }
    
    .streamlit-expanderContent p:last-child {
        margin-bottom: 0 !important;
    }
    
    .streamlit-expanderContent strong {
        color: #f0f6fc !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderContent ul {
        margin: 0.25rem 0 0.375rem 0 !important;
        padding-left: 1.5rem !important;
    }
    
    .streamlit-expanderContent li {
        margin: 0.125rem 0 !important;
        font-size: 0.8125rem !important;
        line-height: 1.5 !important;
        color: #c9d1d9 !important;
    }
    
    /* Spinner styling */
    .stSpinner > div {
        border-top-color: #58a6ff !important;
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background: #238636 !important;
    }
    
    /* Hide Streamlit menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Section dividers */
    .section-divider {
        border-top: 1px solid #30363d;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Professional Header - more compact
    st.markdown("""
    <div style="margin-bottom: 0.75rem;">
        <h1 style="margin-bottom: 0.25rem; color: #f0f6fc;">Bitcoin Purchase Indicators</h1>
        <p style="color: #8b949e; font-size: 0.9375rem; margin-top: 0;">Track corporate Bitcoin purchases through SEC filings</p>
    </div>
    """, unsafe_allow_html=True)
    
    # About section - positioned under title, styled better
    with st.expander("ℹ️ About", expanded=False):
        st.markdown("""
        **Data Source:** SEC EDGAR API
        
        **What We Track:**
        - 8-K forms (Material Events)
        - Bitcoin purchase disclosures
        - Purchase dates and amounts
        
        **Note:** Filings may be delayed by several days after transactions.
        """)
    
    # Load BTC data
    try:
        btc_df = load_bitcoin_data()
        if btc_df is None or btc_df.empty:
            st.warning("⚠️ Unable to load BTC price data. Charts will not be available.")
            btc_df = None
    except Exception as e:
        st.warning(f"⚠️ Error loading BTC data: {e}")
        btc_df = None
    
    # MicroStrategy company header card - more compact
    st.markdown(f"""
    <div style="background: #161b22; 
                padding: 1rem 1.25rem; 
                border-radius: 8px; 
                border: 1px solid #30363d;
                border-left: 4px solid {COMPANY['color']}; 
                margin: 1rem 0 1.25rem 0;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin: 0; color: #f0f6fc; font-size: 1.125rem; font-weight: 600;">{COMPANY['name']}</h3>
                <p style="margin: 0.25rem 0 0 0; color: #8b949e; font-size: 0.8125rem;">{COMPANY['description']}</p>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="color: #8b949e; font-size: 0.8125rem; font-weight: 500;">Ticker:</span>
                <span style="color: #f0f6fc; font-size: 0.8125rem; font-weight: 600; padding: 0.25rem 0.5rem; background: #21262d; border-radius: 4px; border: 1px solid #30363d;">{COMPANY['ticker']}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch SEC filings
    with st.spinner("Fetching SEC filings..."):
        filings = fetch_sec_filings(COMPANY['cik'], form_type="8-K", days_back=180)
    
    if not filings:
        st.info(f"No recent 8-K filings found for {COMPANY['name']} in the last 180 days.")
        return
    
    # Parse filings
    purchases = []
    status_container = st.empty()
    
    with status_container.container():
        st.markdown("**Analyzing filings for Bitcoin purchases...**")
        progress_bar = st.progress(0)
        
        for i, filing in enumerate(filings[:10]):
            progress_bar.progress((i + 1) / min(10, len(filings)))
            
            purchase_info = parse_filing_for_bitcoin_purchase(
                filing['documentUrl'],
                filing['filingDate']
            )
            
            if purchase_info:
                purchase_info.update({
                    "filing": filing,
                    "accession_number": filing['accessionNumber']
                })
                purchases.append(purchase_info)
    
    status_container.empty()
    
    # Display results
    if purchases:
        # Metrics - professional summary section - more compact
        st.markdown("### Summary")
        col1, col2, col3 = st.columns(3)
        
        total_btc = sum([p.get("btc_amount", 0) or 0 for p in purchases])
        total_usd = sum([p.get("usd_amount", 0) or 0 for p in purchases])
        
        with col1:
            st.metric("Purchases Found", len(purchases))
        with col2:
            if total_btc > 0:
                st.metric("Total BTC", f"{total_btc:,.0f}")
            else:
                st.metric("Total BTC", "N/A")
        with col3:
            if total_usd > 0:
                st.metric("Total Value", f"${total_usd/1_000_000:.1f}M")
            else:
                st.metric("Total Value", "N/A")
        
        # Chart - professional container
        st.markdown("### Price Chart")
        chart = create_price_chart_with_purchases(
            btc_df,
            purchases,
            COMPANY['name'],
            COMPANY['color']
        )
        if chart:
            st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})
        else:
            st.info("Price chart unavailable.")
        
        # Purchase details - professional section
        st.markdown("### Purchase Details")
        
        for i, purchase in enumerate(purchases, 1):
            filing = purchase['filing']
            
            # Format values nicely
            btc_display = f"{purchase['btc_amount']:,.0f} BTC" if purchase.get("btc_amount") else "Not specified"
            usd_display = f"${purchase['usd_amount']:,.0f}" if purchase.get("usd_amount") else "Not specified"
            
            # Format USD nicely (millions/billions)
            if purchase.get("usd_amount"):
                if purchase['usd_amount'] >= 1_000_000_000:
                    usd_display = f"${purchase['usd_amount']/1_000_000_000:.2f}B"
                elif purchase['usd_amount'] >= 1_000_000:
                    usd_display = f"${purchase['usd_amount']/1_000_000:.2f}M"
                else:
                    usd_display = f"${purchase['usd_amount']:,.0f}"
            
            st.markdown(f"""
            <div class="purchase-card" style="border-left: 3px solid {COMPANY['color']};">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.375rem;">
                            <div style="width: 1.75rem; height: 1.75rem; border-radius: 6px; background: {COMPANY['color']}20; 
                                        display: flex; align-items: center; justify-content: center; 
                                        font-size: 0.8125rem; font-weight: 600; color: {COMPANY['color']}; 
                                        border: 1px solid {COMPANY['color']}40;">
                                #{i}
                            </div>
                            <div>
                                <h4 style="margin: 0; color: #f0f6fc; font-size: 1rem; font-weight: 600;">Purchase #{i}</h4>
                                <p style="margin: 0.125rem 0 0 0; color: #8b949e; font-size: 0.8125rem;">
                                    📅 {format_date(purchase['purchase_date'])}
                                </p>
                            </div>
                        </div>
                    </div>
                    <a href="{filing['url']}" target="_blank" 
                       style="background: #238636; color: white; padding: 0.5rem 0.875rem; border-radius: 6px; 
                              font-weight: 500; font-size: 0.8125rem; text-decoration: none;
                              border: 1px solid #2ea043;
                              transition: all 0.2s ease;
                              white-space: nowrap;
                              display: inline-block;">
                        View Filing →
                    </a>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #30363d;">
                    <div style="background: #0d1117; padding: 0.875rem; border-radius: 6px; border: 1px solid #30363d;">
                        <p style="margin: 0 0 0.375rem 0; color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500;">BTC Amount</p>
                        <p style="margin: 0; color: #f0f6fc; font-size: 1.375rem; font-weight: 600; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;">
                            {btc_display}
                        </p>
                    </div>
                    <div style="background: #0d1117; padding: 0.875rem; border-radius: 6px; border: 1px solid #30363d;">
                        <p style="margin: 0 0 0.375rem 0; color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500;">USD Value</p>
                        <p style="margin: 0; color: #f0f6fc; font-size: 1.375rem; font-weight: 600; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;">
                            {usd_display}
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"No Bitcoin purchase disclosures found in recent 8-K filings for {COMPANY['name']}.")
        st.markdown("""
        <div style="background: #161b22; padding: 1rem; border-radius: 8px; border: 1px solid #30363d; margin-top: 1rem;">
            <p style="color: #8b949e; margin: 0; line-height: 1.5; font-size: 0.8125rem;">
                Companies may not file 8-K forms for all purchases, or purchases may be disclosed 
                in other filing types (10-Q, 10-K, etc.). Check the filings below for more details.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # All filings - professional table-like display
    st.markdown("### Recent 8-K Filings")
    st.caption(f"Showing {min(10, len(filings))} most recent filings")
    
    for filing in filings[:10]:
        st.markdown(f"""
        <div class="filing-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <div style="padding: 0.5rem 0.75rem; background: #21262d; border-radius: 4px; border: 1px solid #30363d;">
                            <span style="color: #f0f6fc; font-weight: 600; font-size: 0.875rem;">8-K</span>
                        </div>
                        <div>
                            <p style="margin: 0; color: #f0f6fc; font-weight: 500; font-size: 0.9375rem;">8-K Filing</p>
                            <p style="margin: 0.25rem 0 0 0; color: #8b949e; font-size: 0.8125rem;">Filed: {format_date(filing['filingDate'])}</p>
                        </div>
                    </div>
                </div>
                <a href="{filing['url']}" target="_blank" 
                   style="background: #21262d; color: #58a6ff; padding: 0.5rem 1rem; 
                          border-radius: 6px; border: 1px solid #30363d; 
                          font-weight: 500; font-size: 0.875rem; text-decoration: none;
                          transition: all 0.2s ease;">
                    View →
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
