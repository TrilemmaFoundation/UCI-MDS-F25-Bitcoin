from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def make_btc_purchase_failed_email(amount):
    """
    Build an HTML email notifying the user that their BTC purchase attempt failed due to insufficient funds.
    Parameter:
      - amount: numeric (int/float/Decimal) representing the attempted USD purchase amount
    Returns:
      - str : an f-string with HTML email content
    """
    # normalize amount
    try:
        amt = Decimal(amount)
    except (InvalidOperation, TypeError):
        amt = Decimal(0)

    formatted_amount = f"${amt:,.2f}"
    timestamp = (
        datetime.now(timezone.utc).astimezone().strftime("%B %d, %Y %I:%M %p %Z")
    )

    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width,initial-scale=1" />
      <title>BTC Purchase Attempt Failed</title>
      <style>
        body {{
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
          background-color: #f6f8fa;
          margin: 0;
          padding: 24px;
          color: #0f172a;
        }}
        .container {{
          max-width: 600px;
          margin: 0 auto;
          background: #ffffff;
          border-radius: 12px;
          box-shadow: 0 4px 20px rgba(16,24,40,0.08);
          overflow: hidden;
        }}
        .header {{
          padding: 24px;
          background: linear-gradient(90deg, #7c3aed, #0ea5a4);
          color: white;
        }}
        .logo {{
          font-weight: 700;
          font-size: 18px;
        }}
        .content {{
          padding: 24px;
          line-height: 1.5;
        }}
        .amount-card {{
          margin: 18px 0;
          padding: 18px;
          border-radius: 8px;
          background: #f8fafc;
          border: 1px solid #e6edf3;
          display: inline-block;
        }}
        .footer {{
          padding: 18px 24px;
          font-size: 13px;
          color: #6b7280;
          border-top: 1px solid #eef2f7;
          background: #fbfdff;
        }}
        a.button {{
          display: inline-block;
          padding: 10px 16px;
          margin-top: 12px;
          border-radius: 8px;
          text-decoration: none;
          background: #7c3aed;
          color: white;
          font-weight: 600;
        }}
        .muted {{ color: #6b7280; font-size: 13px; }}
      </style>
    </head>
    <body>
      <div class="container" role="article" aria-labelledby="title">
        <div class="header">
          <div class="logo">Bitcoin Accumulation</div>
        </div>

        <div class="content">
          <h2 id="title" style="margin:0 0 6px 0; color:#b91c1c;">Purchase Attempt Failed</h2>
          <p class="muted" style="margin:0 0 18px 0;">We attempted to complete your scheduled Bitcoin purchase through Bitcoin Accumulation (Coinbase integration), but the transaction could not be processed.</p>

          <div>
            <strong>Attempted purchase amount:</strong>
            <div class="amount-card">
              <div style="font-size:20px; font-weight:700;">{formatted_amount} USD</div>
              <div class="muted" style="margin-top:6px;">This transaction was not completed due to insufficient funds in your linked payment method.</div>
            </div>
          </div>

          <p style="margin-top:10px;">
            <strong>Attempt time:</strong><br />
            <span class="muted">{timestamp}</span>
          </p>

          <p style="margin-top:18px;">
            Please ensure your payment method has enough balance and try again.
          </p>

        </div>

        <div class="footer">
          <div>Bitcoin Accumulation • Secure purchases powered by Coinbase integration</div>
          <div style="margin-top:6px;">No funds were withdrawn from your account.</div>
        </div>
      </div>
    </body>
    </html>
    """

    return html


print(make_btc_purchase_failed_email(200.1))
