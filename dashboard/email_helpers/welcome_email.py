from datetime import datetime


def welcome_email(name: str) -> str:
    """
    Return a mobile-friendly HTML welcome email for a new user subscribing to
    daily Bitcoin purchasing updates.

    Args:
        name: Recipient's name (string). Will be HTML-escaped for safety.

    Returns:
        A string containing the HTML email.
    """
    import html

    n = html.escape(name) if name else "Friend"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Welcome — Daily BTC Purchases</title>
  <style>
    /* Basic reset */
    body,table,td,a{{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}}
    table,td{{mso-table-lspace:0pt;mso-table-rspace:0pt;}}
    img{{-ms-interpolation-mode:bicubic;}}
    img{{border:0;height:auto;line-height:100%;outline:none;text-decoration:none;}}
    a[x-apple-data-detectors]{{color:inherit;text-decoration:none;font-size:inherit;font-family:inherit;font-weight:inherit;line-height:inherit;}}

    /* Container and typography */
    body{{margin:0;padding:0;width:100% !important;background-color:#f4f6f8;font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;}}
    .email-wrapper{{width:100%;background-color:#f4f6f8;padding:20px 0;}}
    .email-content{{max-width:600px;margin:0 auto;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 4px 14px rgba(20,20,30,0.06);}}

    .header{{padding:20px;text-align:center;background:linear-gradient(90deg,#0f172a,#0b1220);color:#ffffff;}}
    .logo{{font-weight:700;font-size:20px;letter-spacing:0.4px;}}
    .preheader{{display:none !important;visibility:hidden;opacity:0;height:0;width:0;mso-hide:all;overflow:hidden;}} /* hidden preview text */

    .content{{padding:28px 24px 20px 24px;color:#0f172a;}}
    .greeting{{font-size:18px;margin:0 0 10px 0;font-weight:600;}}
    .lead{{font-size:15px;line-height:1.45;margin:0 0 18px 0;color:#334155;}}

    .card{{background-color:#f8fafc;border-radius:8px;padding:14px;margin:18px 0;color:#0b1220;font-size:14px;line-height:1.4;}}
    .cta-wrap{{text-align:center;margin:20px 0 10px 0;}}
    .button{{display:inline-block;padding:12px 20px;border-radius:8px;background-color:#f7931a;color:white;text-decoration:none;font-weight:600;font-size:15px;}}
    .muted{{color:#64748b;font-size:13px;margin-top:12px;}}

    .footer{{padding:18px 24px;background-color:#ffffff;border-top:1px solid #eef2f7;color:#94a3b8;font-size:12px;text-align:center;}}
    .small{{font-size:12px;color:#94a3b8;line-height:1.4;}}

    /* Responsive tweaks */
    @media only screen and (max-width:480px){{ 
      .content{{padding:20px 16px;}}
      .header{{padding:16px;}}
      .logo{{font-size:18px;}}
      .greeting{{font-size:16px;}}
      .button{{width:100%;display:block;padding:12px 14px;}}
    }}
  </style>
</head>
<body>
  <!-- Preheader (hidden preview text) -->
  <div class="preheader">Welcome to daily Bitcoin purchases — a simple, automated way to dollar-cost-average into BTC.</div>

  <table class="email-wrapper" role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td align="center">
        <table class="email-content" role="presentation" cellpadding="0" cellspacing="0" width="100%">

          <!-- Header -->
          <tr>
            <td class="header">
              <div class="logo">Daily BTC Purchases</div>
              <div style="font-size:13px;margin-top:6px;opacity:0.9;">Simple daily updates for your Bitcoin buying plan</div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td class="content">
              <p class="greeting">Hi {n},</p>
              <p class="lead">
                Welcome — thanks for subscribing to daily Bitcoin purchasing updates. Every afternoon you'll receive a clear note with that day's suggested buy amount,
                the current BTC price, and a short market snapshot so you can stay informed.
              </p>

              <div class="card" role="note" aria-label="What to expect">
                <strong>What to expect:</strong>
                <ul style="margin:10px 0 0 18px;padding:0;color:#0b1220;">
                  <li>Daily short email with the suggested purchase action.</li>
                </ul>
              </div>

              <div class="cta-wrap">
                <!-- Example CTA; replace href with your real link when sending -->
                <a href="https://bitcoin-accumulation-dashboard.streamlit.app/" class="button" target="_blank" rel="noopener">View today's plan</a>
                <div class="muted">or manage your preferences from your account</div>
              </div>

              <p style="margin:18px 0 0 0;color:#334155;font-size:14px;">
                Welcome aboard — here's to steady, disciplined investing.
              </p>

              <p style="margin:12px 0 0 0;color:#334155;font-size:14px;font-weight:600;">Best,<br/>The Daily BTC Purchases Team</p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td class="footer">
              <div class="small">
                You received this email because you subscribed to Daily BTC Purchases. If this wasn't you, please ignore this message or <a href="#" style="color:#0f172a;text-decoration:underline;">contact support</a>.
                <br/><br/>
                <div style="margin-top:8px;color:#cbd5e1;font-size:11px;">
                  <a href="#" style="color:#94a3b8;text-decoration:none;">Unsubscribe</a> • <a href="#" style="color:#94a3b8;text-decoration:none;">Privacy policy</a>
                </div>
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# print(welcome_email("Sam"))
