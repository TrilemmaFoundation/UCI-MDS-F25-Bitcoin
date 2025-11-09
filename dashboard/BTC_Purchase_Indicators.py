import streamlit as st
import requests
from datetime import datetime, timedelta
import re
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dashboard.data_loader import load_bitcoin_data
from bs4 import BeautifulSoup


# Company configurations: CIK numbers for SEC EDGAR filings
COMPANIES = {
    "MicroStrategy (MSTR)": {
        "cik": "1050446",
        "ticker": "MSTR",
        "description": "Largest corporate Bitcoin holder",
        "color": "#F7931A"
    },
    "Tesla": {
        "cik": "1318605",
        "ticker": "TSLA",
        "description": "Major Bitcoin purchaser",
        "color": "#E31937"
    },
    "Block (Square)": {
        "cik": "1512673",
        "ticker": "SQ",
        "description": "Bitcoin-focused company",
        "color": "#00A86B"
    },
    "Marathon Digital": {
        "cik": "1536387",
        "ticker": "MARA",
        "description": "Bitcoin mining and holding company",
        "color": "#FF6B35"
    },
    "Coinbase": {
        "cik": "1679788",
        "ticker": "COIN",
        "description": "Cryptocurrency exchange",
        "color": "#0052FF"
    },
    "Riot Platforms": {
        "cik": "1167419",
        "ticker": "RIOT",
        "description": "Bitcoin mining company",
        "color": "#00D9FF"
    },
    "Hut 8 Mining": {
        "cik": "1716959",
        "ticker": "HUT",
        "description": "Bitcoin mining company",
        "color": "#8B5CF6"
    }
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
        - Missing entries shown as “—” or “0” → treated as None.
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
        if "bitcoin" not in text.lower():
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
    
    # Create figure
    fig = go.Figure()
    
    # Add BTC price line with gradient fill
    fig.add_trace(
        go.Scatter(
            x=btc_df_filtered.index,
            y=btc_df_filtered["PriceUSD"],
            mode="lines",
            name="Bitcoin Price",
            line=dict(color="#F7931A", width=3),
            fill='tozeroy',
            fillcolor='rgba(247, 147, 26, 0.1)',
            hovertemplate="<b>%{x|%B %d, %Y}</b><br>$%{y:,.2f}<extra></extra>",
        )
    )
    
    # Add purchase markers
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
                    name="Purchase",
                    marker=dict(
                        size=18,
                        color=company_color,
                        symbol="diamond",
                        line=dict(width=2.5, color="white"),
                        opacity=0.9
                    ),
                    hovertemplate="<b>%{x|%B %d, %Y}</b><br>Price: $%{y:,.2f}<br>%{text}<extra></extra>",
                    text=[label.replace("<br>", " - ") for label in purchase_labels],
                )
            )
    
    # Update layout with modern styling
    fig.update_layout(
        height=650,
        title={
            "text": f"{company_name} Bitcoin Purchases",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 22, "color": "#ffffff", "family": "Inter, sans-serif"},
            "y": 0.98
        },
        xaxis_title="",
        yaxis_title="",
        hovermode="x unified",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff", family="Inter, sans-serif", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(color="#999", size=11),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1
        ),
        margin=dict(l=50, r=20, t=60, b=50),
    )
    
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.06)",
        showgrid=True,
        zeroline=False,
        showline=False,
        tickfont=dict(color="#999", size=10),
        tickformat="%b %d",
        showspikes=True,
        spikecolor="rgba(255,255,255,0.2)",
        spikethickness=1
    )
    
    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.06)",
        showgrid=True,
        zeroline=False,
        showline=False,
        tickfont=dict(color="#999", size=10),
        tickformat="$,.0f",
        showspikes=True,
        spikecolor="rgba(255,255,255,0.2)",
        spikethickness=1
    )
    
    return fig


def main():
    """Main function for BTC Purchase Indicators page"""
    st.set_page_config(
        page_title="BTC Purchase Indicators - BTC Dashboard",
        layout="wide",
        page_icon="₿",
    )
    
    # Modern CSS styling
    st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background: linear-gradient(180deg, #0a0a0a 0%, #0f0f0f 100%);
    }
    
    /* Typography */
    h1 {
        color: #ffffff !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        margin-bottom: 0.5rem !important;
    }
    
    h2 {
        color: #ffffff !important;
        font-size: 1.75rem !important;
        font-weight: 600 !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
    }
    
    h3 {
        color: #ffffff !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
    }
    
    /* Company selector styling */
    .stSelectbox > div > div {
        background-color: #1a1a1a !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 8px !important;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #999 !important;
        font-weight: 500 !important;
    }
    
    /* Purchase cards */
    .purchase-card {
        background: linear-gradient(135deg, #1a1a1a 0%, #1f1f1f 100%);
        padding: 28px;
        border-radius: 16px;
        border: 1px solid #2a2a2a;
        margin: 20px 0;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    
    .purchase-card:hover {
        border-color: #3a3a3a;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
        transform: translateY(-4px);
    }
    
    /* Filing cards */
    .filing-card {
        background: linear-gradient(135deg, #1a1a1a 0%, #1f1f1f 100%);
        padding: 20px 24px;
        border-radius: 12px;
        border: 1px solid #2a2a2a;
        margin: 12px 0;
        transition: all 0.3s ease;
    }
    
    .filing-card:hover {
        border-color: #3a3a3a;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    /* Links */
    a {
        text-decoration: none !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #F7931A 0%, #FFA64D 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(247, 147, 26, 0.4);
    }
    
    /* Info boxes */
    .stInfo {
        background-color: #1a1a1a !important;
        border-left: 4px solid #F7931A !important;
        border-radius: 8px !important;
    }
    
    /* Success boxes */
    .stSuccess {
        background-color: #1a2a1a !important;
        border-left: 4px solid #00ff00 !important;
        border-radius: 8px !important;
    }
    
    /* Remove Streamlit default styling */
    .stMarkdown {
        color: #e0e0e0;
    }
    
    /* Captions */
    .stCaption {
        color: #999 !important;
        font-size: 0.85rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("## Bitcoin Purchase Indicators")
        st.markdown(
            '<p style="color: #999; font-size: 1rem; margin-top: -0.5rem;">Track corporate Bitcoin purchases through SEC filings</p>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("ℹ️ Info", expanded=False):
            st.markdown("""
            **Data Source:** SEC EDGAR API (free, no authentication)
            
            **What we track:**
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
    
    # Company selection
    st.markdown("### Select Company")
    
    selected_company = st.selectbox(
        "Choose a company to analyze:",
        options=list(COMPANIES.keys()),
        index=0,
        help="Select which company you want to analyze for Bitcoin purchases",
        label_visibility="collapsed"
    )
    
    company = COMPANIES[selected_company]
    
    # Company header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1a1a1a 0%, #1f1f1f 100%); 
                padding: 24px; border-radius: 12px; border-left: 4px solid {company['color']}; 
                margin: 20px 0;">
        <h3 style="margin: 0; color: #ffffff;">{selected_company}</h3>
        <p style="margin: 8px 0 0 0; color: #999; font-size: 0.95rem;">{company['description']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch SEC filings
    with st.spinner("Fetching SEC filings..."):
        filings = fetch_sec_filings(company['cik'], form_type="8-K", days_back=180)
    
    if not filings:
        st.info(f"No recent 8-K filings found for {selected_company} in the last 180 days.")
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
        # Metrics
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
        
        # Chart
        st.markdown("### Price Chart")
        chart = create_price_chart_with_purchases(
            btc_df,
            purchases,
            selected_company,
            company['color']
        )
        if chart:
            st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})
        else:
            st.info("Price chart unavailable.")
        
        # Purchase details
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
            <div class="purchase-card" style="border-left: 3px solid {company['color']};">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                            <div style="width: 40px; height: 40px; border-radius: 10px; background: linear-gradient(135deg, {company['color']}22, {company['color']}44); 
                                        display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 700; color: {company['color']};">
                                #{i}
                            </div>
                            <div>
                                <h4 style="margin: 0; color: #ffffff; font-size: 1.3rem; font-weight: 600;">Purchase #{i}</h4>
                                <p style="margin: 4px 0 0 0; color: #999; font-size: 0.9rem; display: flex; align-items: center; gap: 6px;">
                                    <span>📅</span> {format_date(purchase['purchase_date'])}
                                </p>
                            </div>
                        </div>
                    </div>
                    <a href="{filing['url']}" target="_blank" 
                       style="background: linear-gradient(135deg, {company['color']} 0%, {company['color']}dd 100%);
                              color: white; padding: 10px 20px; border-radius: 8px; 
                              font-weight: 600; font-size: 0.9rem; text-decoration: none;
                              box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                              transition: all 0.2s ease;
                              white-space: nowrap;">
                        View Filing →
                    </a>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <div style="background: rgba(255,255,255,0.03); padding: 16px; border-radius: 8px;">
                        <p style="margin: 0 0 8px 0; color: #999; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500;">BTC Amount</p>
                        <p style="margin: 0; color: #ffffff; font-size: 1.4rem; font-weight: 700; font-family: 'Monaco', 'Courier New', monospace;">
                            {btc_display}
                        </p>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 16px; border-radius: 8px;">
                        <p style="margin: 0 0 8px 0; color: #999; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500;">USD Value</p>
                        <p style="margin: 0; color: #ffffff; font-size: 1.4rem; font-weight: 700; font-family: 'Monaco', 'Courier New', monospace;">
                            {usd_display}
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"No Bitcoin purchase disclosures found in recent 8-K filings for {selected_company}.")
        st.markdown("""
        <div style="background: #1a1a1a; padding: 20px; border-radius: 12px; border: 1px solid #2a2a2a; margin-top: 20px;">
            <p style="color: #999; margin: 0; line-height: 1.6;">
                Companies may not file 8-K forms for all purchases, or purchases may be disclosed 
                in other filing types (10-Q, 10-K, etc.). Check the filings below for more details.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # All filings
    st.markdown("### Recent 8-K Filings")
    st.caption(f"Showing {min(10, len(filings))} most recent filings")
    
    for filing in filings[:10]:
        st.markdown(f"""
        <div class="filing-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="margin: 0; color: #ffffff; font-weight: 600;">8-K Filing</p>
                    <p style="margin: 4px 0 0 0; color: #999; font-size: 0.9rem;">{format_date(filing['filingDate'])}</p>
                </div>
                <a href="{filing['url']}" target="_blank" 
                   style="background: #2a2a2a; color: #F7931A; padding: 8px 16px; 
                          border-radius: 6px; border: 1px solid #3a3a3a; 
                          font-weight: 600; font-size: 0.9rem; text-decoration: none;">
                    View →
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
