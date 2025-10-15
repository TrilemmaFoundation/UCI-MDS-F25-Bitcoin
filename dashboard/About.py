import streamlit as st


md_string = """
# Welcome to Your Smart Bitcoin Accumulator! 📊

Hello and welcome! If you're new to Bitcoin, you've probably asked the biggest question everyone has: **"When is the right time to buy?"**

The price of Bitcoin can seem unpredictable, and jumping in can feel intimidating. This dashboard is designed to help you navigate that question by turning a complex decision into a simple, automated plan.

Our goal is simple: to help you accumulate Bitcoin for the long term in an intelligent way, removing the stress and guesswork from the process.

---

### How to Use This Dashboard

Getting your personalized investment plan is as easy as 1-2-3:

1.  **Enter Your Budget:** Tell us the total amount of money you'd like to invest.
2.  **Set Your Timeframe:** Choose the period over which you want to invest that budget.
3.  **Get Your Plan:** The dashboard will instantly generate a daily schedule, showing you exactly how much to invest each day to make the most of your budget.

---

### The "Secret Sauce": Smart Shopper Model 🧠

Credit to Youssef Ahmed, Georgia Institude of Technology for developing the model.

So, how does this all work? Instead of trying to "time the market" perfectly (which is nearly impossible!), the model follows a disciplined and proven strategy.

Imagine you're a **Smart Shopper** with a weekly grocery budget.

🛒 **Strategy 1: The Steady Approach**

You could spend the exact same amount of money every single day. This is a great, simple strategy called **Dollar Cost Averaging (DCA)**. It's consistent and avoids the risk of putting all your money in at a "bad" price.

💡 **Strategy 2: The *Smart Shopper* Approach (The Model)**

Now, what if your favorite item goes on a **huge sale** one day? A smart shopper would recognize the opportunity. On that day, you'd decide to spend a little *more* of your weekly budget to stock up while the price is low.

To stay on budget, you'd then spend a little *less* on the following days.

**The model does exactly this for Bitcoin.**

1.  **It Establishes a "Fair Price":** First, the model calculates the average price of Bitcoin over the long term (specifically, the last 200 days). Think of this as the regular, non-sale price.

2.  **It Looks for a "Sale":** Every day, it compares the current price to this long-term average. If the current price drops significantly below the average, the model sees this as a "sale"—a great opportunity to buy.

3.  **It Buys More on Sale Days:** When the model detects a "sale," it automatically assigns a larger portion of your budget to that day. The bigger the price drop, the more it invests.

4.  **It Stays on Budget:** To pay for these bigger purchases, the model slightly reduces the amount it plans to invest on many future days. This ensures you never go over your total budget.

### Why Does This Work?

This dynamic approach is powerful for a few key reasons:

*   ✅ **It Removes Emotion:** The strategy is 100% rules-based. It prevents "fear of missing out" (FOMO) when prices are high and "panic selling" when prices are low.
*   ✅ **It Aims for a Better Average Price:** By buying more when the price is low, the goal is to lower your average purchase price over time.
*   ✅ **More "Sats for Your Dollar":** Ultimately, this means you accumulate more Bitcoin (or "Sats," the smallest unit of Bitcoin) for the same amount of money.

---

### ⚠️ Important Disclaimer

This tool is for educational and informational purposes only. It is designed to demonstrate a quantitative investment strategy. It is **not financial advice**. The cryptocurrency market is highly volatile, and investing in Bitcoin involves significant risk.

Please do your own research and consider consulting with a qualified financial advisor before making any investment decisions. Past performance is not indicative of future results.

**Happy accumulating!**

"""

st.markdown(md_string)
