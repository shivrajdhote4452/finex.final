# FinEx — Cross-Platform UI Contract v1.0 (S1-PRD-03)

**Platforms:** React Web & Flutter Mobile  
**Contract Version:** 1.0  
**Ownership:** Visual styling is owned and guided by Shivraj Dhote. This contract freezes the logical states, field names, error messages, and accessibility definitions across both clients.

---

## 1. Standard UI States per Route

| State | Definition | Visual / Screen Behavior |
|---|---|---|
| `LOADING` | Network or asynchronous calculation in progress | Shows accessible spinner/skeleton; disables action buttons |
| `EMPTY` | Valid state where no records exist yet (e.g. 0 holdings) | Shows informative guidance (e.g., "No holdings yet. Add your first investment."); never presents as an error |
| `SUCCESS` | Data retrieved or mutation committed | Shows full data view with source attribution and observation timestamp |
| `VALIDATION_ERROR` | Client or server rejected input | Highlights offending field with specific error message; preserves user's valid input |
| `UNAUTHORIZED` | Session expired or missing authentication | Retains attempted URL and redirects cleanly to `/login` |
| `PROVIDER_FAILURE` | Upstream provider outage (e.g., market quotes) | Shows cached real data with "Last updated" banner or explicit "Temporarily Unavailable" badge; never displays `0` |

---

## 2. Route Map & Required States

### `/login`
- **Fields:** `google_auth_button`
- **States:** Default, Loading (OAuth popup/redirect), Error (OAuth failure/cancelled).

### `/onboarding`
- **Fields:** `full_name`, `country`, `experience_level`, `terms_accepted`, `privacy_accepted`
- **Wording:**
  - Terms checkbox: *"I consent to FinEx educational terms of use and data handling policies."*
  - Validation error: *"You must accept the terms to continue."*

### `/dashboard`
- **Components:** Portfolio Summary Card, Market Highlights, Recent Activity, Risk Profile Banner.
- **Rules:** If no holdings exist, display: *"You have not added any holdings yet. Track your first asset to view performance analytics."*

### `/portfolio`
- **Fields:** `symbol`, `quantity`, `cost_per_share`, `currency`, `purchase_date`
- **Validation Messages:**
  - `quantity`: *"Quantity must be a positive number greater than 0."*
  - `cost_per_share`: *"Cost per share must be greater than or equal to 0."*

### `/chat`
- **Components:** Message History, Input Composer, Citation Cards, Feedback Thumbs (Up/Down), Disclaimer.
- **Mandatory Disclaimer:** *"FinEx is an educational research assistant. Information provided does not constitute financial, investment, or legal advice."*

### `/paper-trading`
- **Components:** Virtual Cash Balance, Order Ticket (Buy/Sell), Open Positions, Execution Ledger.
- **Mandatory Simulation Badge:** *"Simulated Paper Trading — Virtual Currency Only. No real funds involved."*

### `/alerts`
- **Components:** Rule List, Add Rule Modal/Form, Notification History.
- **States:** Active, Cooldown, Disabled.

### `/goals`
- **Fields:** `goal_name`, `target_amount`, `current_savings`, `target_date`, `expected_annual_return`
- **Validation:** Target date must be in the future; target amount must be positive.

### `/spending`
- **Components:** CSV Upload Dropzone/File Picker, Preview Table with Column Mapping, Masked Category Review, Monthly Trend Charts.
