from datetime import datetime


def daily_btc_purchase_email(amount: str, current_price: str) -> str:
    """
    Return a mobile-friendly HTML email showing the suggested Bitcoin accumulation amount.

    Args:
        amount: A string representing the dollar amount (e.g., "45.23").

    Returns:
        A string containing the HTML email.
    """
    import html

    amt = html.escape(amount.strip())

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Today's Bitcoin Accumulation </title>
  <style>
    body,table,td,a{{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}}
    table,td{{mso-table-lspace:0pt;mso-table-rspace:0pt;}}
    img{{-ms-interpolation-mode:bicubic;}}
    img{{border:0;height:auto;line-height:100%;outline:none;text-decoration:none;}}
    a[x-apple-data-detectors]{{color:inherit;text-decoration:none;font-size:inherit;font-family:inherit;font-weight:inherit;line-height:inherit;}}
    body{{margin:0;padding:0;width:100% !important;background-color:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}}
    .email-wrapper{{width:100%;background-color:#f4f6f8;padding:20px 0;}}
    .email-content{{max-width:600px;margin:0 auto;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 4px 14px rgba(20,20,30,0.06);}}
    .header{{padding:20px;text-align:center;background:linear-gradient(90deg,#0f172a,#0b1220);color:#ffffff;}}
    .logo{{font-weight:700;font-size:20px;letter-spacing:0.4px;}}
    .content{{padding:28px 24px 20px 24px;color:#0f172a;text-align:center;}}
    .title{{font-size:20px;margin:0 0 10px 0;font-weight:600;}}
    .amount-box{{display:inline-block;margin-top:14px;padding:22px 28px;background:#f7931a;color:#ffffff;border-radius:12px;font-size:36px;font-weight:700;letter-spacing:0.5px;box-shadow:0 4px 12px rgba(247,147,26,0.3);}}
    .note{{font-size:15px;line-height:1.5;margin:18px 0 0 0;color:#334155;}}
    .footer{{padding:18px 24px;background-color:#ffffff;border-top:1px solid #eef2f7;color:#94a3b8;font-size:12px;text-align:center;}}
    .button{{display:inline-block;padding:12px 20px;border-radius:8px;background-color:#f7931a;color:white;text-decoration:none;font-weight:600;font-size:15px;}}

    @media only screen and (max-width:480px) {{
      .content{{padding:22px 16px;}}
      .amount-box{{font-size:30px;padding:18px 24px;}}
      .title{{font-size:18px;}}
    }}
  </style>
</head>
<body>
  <table class="email-wrapper" role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td align="center">
        <table class="email-content" role="presentation" cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td class="header">
              <div class="logo">Daily BTC Accumulation</div>
              <div style="font-size:13px;margin-top:6px;opacity:0.9;">Your daily Bitcoin amount</div>
            </td>
          </tr>
          <tr>
            <td class="content">
              <p class="title">Today's Accumulation</p>
              <div class="amount-box">${amt}</div>
              <p class="note">
                This is a Bitcoin accumulation amount for today. The current bitcoin price is ${current_price}.
                Prices are monitored daily to help you stay consistent with your strategy.
              </p>
              <br>
            <a href="https://bitcoin-accumulation-dashboard.streamlit.app/" class="button" target="_blank" rel="noopener">Go to your dashboard</a>
                <br>
              <p class="note" style="margin-top:16px;">
                You can review your history or adjust your plan anytime in your account settings.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# print(daily_btc_purchase_email(amount="67"))
