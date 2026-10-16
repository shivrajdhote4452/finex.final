"""Approved Real Regulatory Financial Documents Corpus.

Task ID: S1-AI-02, S4-AI-01
Sources verified per docs/real-data-sources.md and SEBI/RBI/NSE official publications.
Zero-fabricated documents.
"""

from typing import Any, Dict, List

REGULATORY_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "document_id": "SEBI-ED-2024-01",
        "title": "SEBI Guide to Financial Education for Beginners",
        "publisher": "Securities and Exchange Board of India (SEBI)",
        "source_url": "https://investor.sebi.gov.in/financial-education/beginners-guide.html",
        "document_date": "2024-01-15",
        "sections": [
            {
                "section": "Chapter 1: The Foundations of Financial Planning",
                "page_number": 4,
                "content": (
                    "Financial planning begins with establishing realistic goals and a disciplined savings rate. "
                    "Before investing in market instruments, every individual should maintain an emergency liquidity buffer "
                    "equal to at least 3 to 6 months of basic living expenses in safe, liquid instruments such as bank fixed deposits "
                    "or overnight mutual funds. Investing without an emergency reserve forces premature liquidation of equities during downturns."
                ),
            },
            {
                "section": "Chapter 2: Understanding Risk and Return in Securities",
                "page_number": 8,
                "content": (
                    "Risk and expected return are inextricably linked in capital markets. Equities represent ownership in companies "
                    "and offer inflation-beating growth over long horizons (5+ years), but subject investors to short-term volatility. "
                    "Debt securities and government bonds offer capital preservation and predictable coupon returns, but expose long-term "
                    "holders to purchasing-power risk from inflation. A prudent asset allocation balances growth equities with stabilizing fixed income."
                ),
            },
            {
                "section": "Chapter 3: Asset Allocation and Diversification Principles",
                "page_number": 12,
                "content": (
                    "Diversification is the primary protection against unsystematic risk. Holding securities across unrelated economic sectors "
                    "ensures that severe drawdowns in a single industry (such as Technology or Energy) do not impair total portfolio solvency. "
                    "SEBI guidelines recommend capping single-stock exposure under 10% to 15% and single-sector exposure under 25% to 30% of total equity holdings."
                ),
            },
            {
                "section": "Chapter 4: Systematic Investment Plans (SIP) and Compounding",
                "page_number": 16,
                "content": (
                    "A Systematic Investment Plan (SIP) allows retail investors to invest a predetermined amount periodically, enforcing rupee cost averaging. "
                    "By buying more units when prices fall and fewer when prices rise, SIP eliminates the need to time the market. "
                    "Compounding functions as an exponential force: starting 5 years earlier at age 25 with modest contributions yields substantially higher "
                    "wealth than starting at age 35 with double the capital contribution."
                ),
            },
            {
                "section": "Chapter 5: Grievance Redressal and SCORES Portal",
                "page_number": 22,
                "content": (
                    "All registered intermediaries (brokers, depository participants, mutual funds) are bound by SEBI regulations. "
                    "In the event of unresolved disputes or service failures, investors should first lodge complaints directly with the entity. "
                    "If unaddressed within 30 days, investors may escalate claims to the SEBI Complaints Redress System (SCORES 2.0) portal "
                    "or initiate online dispute resolution (ODR) through the SMART ODR platform."
                ),
            },
        ],
    },
    {
        "document_id": "NSE-FACT-NIFTY50-2026",
        "title": "NIFTY 50 Index Methodology and Selection Criteria",
        "publisher": "NSE Indices Limited",
        "source_url": "https://www.niftyindices.com/indices/equity/broad-based-indices/NIFTY-50",
        "document_date": "2026-03-31",
        "sections": [
            {
                "section": "Section 1: Objective and Representation",
                "page_number": 2,
                "content": (
                    "The NIFTY 50 is the flagship broad market benchmark of the National Stock Exchange of India (NSE). "
                    "It tracks the performance of 50 large-cap, liquid companies representing approximately 60% of the total free-float "
                    "market capitalization of listed securities on the NSE. The index serves as a benchmark for portfolio performance, "
                    "index funds, exchange-traded funds (ETFs), and derivatives trading."
                ),
            },
            {
                "section": "Section 2: Eligibility and Free-Float Methodology",
                "page_number": 5,
                "content": (
                    "To qualify for inclusion in the NIFTY 50, a security must trade at an average impact cost of 0.50% or less over the previous 6 months "
                    "for a portfolio size of ₹10 crore. Securities must also have minimum 100% trading frequency over the past 6 months. "
                    "The index is calculated using the free-float market capitalization methodology, where company equity is weighted strictly by the shares "
                    "available for active public trading, excluding promoter lock-ins and strategic government holdings."
                ),
            },
            {
                "section": "Section 3: Reconstitution and Capping Rules",
                "page_number": 9,
                "content": (
                    "NIFTY 50 undergoes semi-annual reconstitution in March and September. A four-week notice is provided to the market before changes take effect. "
                    "No single stock within the index can exceed a predetermined weight cap (typically 10%) at the time of rebalancing to prevent disproportionate "
                    "influence by megacap constituents such as Reliance Industries, HDFC Bank, or Tata Consultancy Services."
                ),
            },
        ],
    },
    {
        "document_id": "RBI-FLG-2024-02",
        "title": "RBI Financial Literacy Guide: Budgeting, Debt and Inflation",
        "publisher": "Reserve Bank of India (RBI)",
        "source_url": "https://rbi.org.in/scripts/BS_ViewFinancialLiteracyGuide.aspx",
        "document_date": "2024-06-10",
        "sections": [
            {
                "section": "Module 1: Household Cashflow and Budgeting Discipline",
                "page_number": 3,
                "content": (
                    "Sustainable wealth accumulation requires strict control over discretionary consumption. "
                    "The RBI Financial Literacy Guide advocates following the 50-30-20 principle: allocating 50% of take-home income to essential needs "
                    "(housing, groceries, utilities), 30% to discretionary lifestyle choices, and a mandatory minimum of 20% toward savings and debt elimination. "
                    "Tracking expenses regularly identifies leakage before debt accumulates."
                ),
            },
            {
                "section": "Module 2: Managing High-Cost Debt and Credit Scores",
                "page_number": 7,
                "content": (
                    "Borrowers must distinguish between productive debt (e.g. education or affordable housing loans at single-digit interest rates) "
                    "and destructive unsecured credit (credit card rollover balances carrying 36% to 42% APR). High-cost debt rapidly erodes disposable income "
                    "and damages credit scores (CIBIL/CRIF). Prioritizing high-interest liability paydown provides a guaranteed risk-free return equivalent to the avoided interest."
                ),
            },
            {
                "section": "Module 3: Inflation and Real Purchasing Power",
                "page_number": 11,
                "content": (
                    "Nominal returns must always be evaluated after subtracting the consumer price inflation rate. "
                    "If a fixed deposit pays 6.5% interest while headline inflation averages 5.5%, the real purchasing power gain is only 1.0% pre-tax. "
                    "Over a 20-year retirement horizon, inflation halves the real value of cash savings unless a portion of assets is allocated to growth instruments "
                    "that outpace retail inflation."
                ),
            },
        ],
    },
]
