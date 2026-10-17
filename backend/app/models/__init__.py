"""FinEx Operational Database ORM Models Catalog.

Exports Base declarative base and all entity models across Core, Market,
Paper Trading, Goals, Spending, Alerts, and RAG domains.
"""

from backend.app.models.alerts import (
    AlertEvent,
    AlertRule,
    Notification,
    NotificationDeliveryAttempt,
)
from backend.app.models.core import (
    ApplicationEvent,
    Base,
    Portfolio,
    PortfolioHolding,
    RevokedToken,
    User,
    UserConsent,
    UserProfile,
)
from backend.app.models.goals import (
    FinancialGoal,
    GoalContribution,
    GoalProjection,
)
from backend.app.models.market import (
    MarketPriceHistory,
    MarketQuote,
    Security,
    Watchlist,
    WatchlistItem,
)
from backend.app.models.paper_trading import (
    PaperAccount,
    PaperCashLedger,
    PaperOrder,
    PaperPosition,
    PaperTrade,
)
from backend.app.models.rag import (
    AIConversation,
    AIFeedback,
    AIMessage,
    DocumentChunk,
    DocumentRegistry,
    RetrievalEvent,
)
from backend.app.models.spending import (
    Transaction,
    TransactionCategory,
    TransactionUpload,
)

__all__ = [
    "Base",
    "User",
    "UserProfile",
    "UserConsent",
    "Portfolio",
    "PortfolioHolding",
    "RevokedToken",
    "ApplicationEvent",
    "Security",
    "MarketQuote",
    "MarketPriceHistory",
    "Watchlist",
    "WatchlistItem",
    "PaperAccount",
    "PaperOrder",
    "PaperTrade",
    "PaperPosition",
    "PaperCashLedger",
    "FinancialGoal",
    "GoalContribution",
    "GoalProjection",
    "TransactionUpload",
    "TransactionCategory",
    "Transaction",
    "AlertRule",
    "AlertEvent",
    "Notification",
    "NotificationDeliveryAttempt",
    "DocumentRegistry",
    "DocumentChunk",
    "AIConversation",
    "AIMessage",
    "AIFeedback",
    "RetrievalEvent",
]
