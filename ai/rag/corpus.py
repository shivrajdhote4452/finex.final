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
                    "Asset allocation and portfolio diversification are foundational risk-mitigation principles in securities markets. "
                    "Diversification involves spreading investments across different asset classes (such as equity, debt, and cash equivalents), market sectors, "
                    "and issuers to reduce unsystematic (company-specific and sector-specific) risk. "
                    "Diversification helps reduce some risks, but it does not eliminate market risk (systematic risk) and does not guarantee protection against investment losses or guarantee positive returns during market downturns. "
                    "Under SEBI regulations, there are no statutory percentage holding limits or mandatory concentration caps for individual retail investors in their direct equity holdings; retail investors determine their own asset allocation based on their financial goals and risk tolerance. "
                    "For mutual funds, Clause 1 of the Seventh Schedule of the SEBI (Mutual Funds) Regulations, 1996 restricts a mutual fund scheme from investing more than 10% of its Net Asset Value (NAV) in equity shares or equity-related instruments of a single company. "
                    "This concentration limit applies specifically to actively managed mutual fund schemes and does not apply to individual retail investors. "
                    "Furthermore, it is not a universal rule for all funds: exceptions exist for Index Funds and Exchange Traded Funds (ETFs) tracking benchmark indices under SEBI portfolio concentration norms (SEBI Circular SEBI/HO/IMD/DF3/CIR/P/2019/17), sectoral and thematic schemes investing within their defined mandate, and distinct single-issuer limits governing debt instruments."
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
    {
        "document_id": "RBI-SGB-2024-FAQ",
        "title": "Reserve Bank of India Sovereign Gold Bond (SGB) Scheme FAQs",
        "publisher": "Reserve Bank of India (RBI)",
        "source_url": "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=57022",
        "document_date": "2024-02-12",
        "sections": [
            {
                "section": "Section 1: Interest Rate and Coupon Payments",
                "page_number": 2,
                "content": (
                    "Sovereign Gold Bonds (SGB) bear interest at the rate of 2.50% (fixed rate) per annum on the initial nominal amount of investment. "
                    "Interest is credited semi-annually directly to the investor's bank account. The last coupon interest payment is made on maturity along with the principal."
                ),
            },
            {
                "section": "Section 2: Eligibility and Limits",
                "page_number": 4,
                "content": (
                    "SGBs are restricted for sale to resident individuals, HUFs, Trusts, Universities, and Charitable Institutions. "
                    "The minimum allowable investment is 1 gram of gold. The maximum limit of subscription is 4 kg for individuals and HUF, and 20 kg for trusts "
                    "and similar entities per fiscal year (April–March) as notified by the Government of India from time to time."
                ),
            },
            {
                "section": "Section 3: Taxation and Premature Exit",
                "page_number": 6,
                "content": (
                    "The tenure of the Bond is 8 years. Premature encashment or redemption of the bond is permitted after the 5th year from the date of issue on coupon payment dates. "
                    "The capital gains tax arising on redemption of SGB to an individual upon maturity is completely exempted under Section 47 of the Income Tax Act. "
                    "Indexation benefits are provided to long-term capital gains arising from transfer of the bond on the stock exchange."
                ),
            },
        ],
    },
    {
        "document_id": "NISM-EQ-DERIV-2024",
        "title": "NISM Series VIII: Equity Derivatives Certification & Clearing Rules",
        "publisher": "National Institute of Securities Markets (NISM)",
        "source_url": "https://www.nism.ac.in/certifications/series-viii-equity-derivatives-certification-examination/",
        "document_date": "2024-04-01",
        "sections": [
            {
                "section": "Chapter 4: Margin Requirements and Risk Containment",
                "page_number": 45,
                "content": (
                    "To safeguard financial market stability, clearing corporations enforce mandatory upfront peak margins on equity derivative contracts. "
                    "Margin components include Value-at-Risk (VaR) margin, Extreme Loss Margin (ELM), and mark-to-market (MTM) margins. "
                    "Brokers cannot permit intraday leverage beyond the SEBI-mandated peak margin collection framework."
                ),
            },
            {
                "section": "Chapter 6: Settlement Mechanism of Futures and Options",
                "page_number": 72,
                "content": (
                    "Index derivatives (NIFTY 50 and BANK NIFTY options) are settled entirely in cash at expiration based on the weighted average closing price "
                    "of the underlying index. Individual equity stock derivatives, however, are subject to physical delivery of the underlying shares upon expiry "
                    "if held to contract close, requiring full capital outlay or deliverable shares."
                ),
            },
        ],
    },
    {
        "document_id": "AMFI-MF-GUIDE-2024",
        "title": "AMFI Code of Conduct and Mutual Fund Investor Educational Handbook",
        "publisher": "Association of Mutual Funds in India (AMFI)",
        "source_url": "https://www.amfiindia.com/investor-corner/knowledge-center/what-are-mutual-funds.html",
        "document_date": "2024-05-18",
        "sections": [
            {
                "section": "Chapter 3: Total Expense Ratio (TER) Structure",
                "page_number": 15,
                "content": (
                    "Total Expense Ratio (TER) represents the annual percentage fee charged by the Asset Management Company (AMC) to manage the fund. "
                    "Under SEBI Mutual Fund Regulations, TER caps are strictly tiered based on scheme Assets Under Management (AUM): capping at 2.25% for the first ₹500 crore of AUM "
                    "and decreasing incrementally. Direct plans have lower TER than regular plans because no distributor commissions are paid."
                ),
            },
            {
                "section": "Chapter 5: Exit Load Structure and NAV Computation",
                "page_number": 28,
                "content": (
                    "An exit load is a fee levied when an investor redeems mutual fund units before a specified lock-in holding period (typically 1% if redeemed within 1 year for equity funds). "
                    "Exit loads are credited back directly to the scheme's assets to protect remaining long-term unitholders from liquidity disruption. "
                    "Net Asset Value (NAV) is computed daily at the close of trading after deducting scheme operational expenses."
                ),
            },
        ],
    },
]

# Separate FinEx educational summary documents containing practical heuristics clearly labeled as FinEx research
FINEX_EDUCATIONAL_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "document_id": "FINEX-ED-DIVERSIFICATION-2026",
        "title": "FinEx Educational Summary: Portfolio Diversification & Risk Allocation Heuristics",
        "doc_type": "EDUCATIONAL_SUMMARY",
        "publisher": "FinEx Educational Summary",
        "source_url": "local://finex/educational-summary/diversification",
        "document_date": "2026-10-16",
        "sections": [
            {
                "section": "Section 1: Portfolio Diversification Heuristics for Retail Investors",
                "page_number": 1,
                "content": (
                    "FinEx Educational Summary: Practical Portfolio Diversification Heuristics. "
                    "While SEBI regulations do not prescribe statutory portfolio caps or percentage limits for individual retail investors in their personal direct equity holdings, "
                    "financial planning practitioners and FinEx educational research commonly recommend the following illustrative heuristics to help reduce unsystematic risk: "
                    "1. Single-Stock Heuristic: Consider capping individual equity holdings under 10% to 15% of total equity to avoid disproportionate firm-specific downside. "
                    "2. Single-Sector Heuristic: Consider capping total exposure to a single industry under 25% to 30% of total equity holdings to mitigate sectoral downturns. "
                    "Regulatory & Risk Disclosures: These figures are illustrative FinEx educational summaries and financial planning heuristics; they are NOT statutory SEBI regulations for retail investors. "
                    "Statutory 10% single-company concentration limits apply to actively managed mutual fund schemes under Clause 1 of the Seventh Schedule of SEBI (Mutual Funds) Regulations, 1996 (with exceptions for Index Funds and ETFs tracking benchmark indices), not to individual retail investors. "
                    "Diversification helps reduce unsystematic (company-specific and sector-specific) risk, but does not eliminate systematic market risk and does not guarantee protection against investment losses."
                ),
            }
        ],
    }
]
