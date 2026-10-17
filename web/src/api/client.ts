/**
 * Centralized Typed API Client for FinEx Frontend.
 * 
 * Task: CH-06 (Connect React to FastAPI Backend)
 * Conforms to the FinEx OpenAPI contract and response envelope specification.
 */

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '/api/v1';

export interface ApiResponseEnvelope<T> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  correlation_id?: string;
  timestamp?: string;
}

class ApiError extends Error {
  code: string;
  status: number;
  details?: any;

  constructor(message: string, status: number, code: string = 'API_ERROR', details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('finex_access_token');
  }

  public setToken(token: string | null): void {
    this.token = token;
    if (token) {
      localStorage.setItem('finex_access_token', token);
    } else {
      localStorage.removeItem('finex_access_token');
    }
  }

  public getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('finex_access_token');
    }
    return this.token;
  }

  public isAuthenticated(): boolean {
    return Boolean(this.getToken());
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Correlation-ID': `web-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized globally
    if (response.status === 401) {
      this.setToken(null);
      throw new ApiError('Authentication required or session expired', 401, 'UNAUTHORIZED');
    }

    let payload: any;
    try {
      payload = await response.json();
    } catch {
      if (!response.ok) {
        throw new ApiError(`HTTP ${response.status}: ${response.statusText}`, response.status);
      }
      return {} as T;
    }

    if (!response.ok || (payload && payload.success === false)) {
      const errMsg = payload?.error?.message || `Request failed with status ${response.status}`;
      const errCode = payload?.error?.code || `HTTP_${response.status}`;
      throw new ApiError(errMsg, response.status, errCode, payload?.error?.details);
    }

    return (payload && 'data' in payload ? payload.data : payload) as T;
  }

  // --- Auth & User Profile ---
  public auth = {
    googleLogin: async (idToken: string) => {
      const res = await this.request<{
        access_token: string;
        token_type: string;
        expires_in: number;
        user_id: string;
        email: string;
        name: string;
      }>('/auth/google', {
        method: 'POST',
        body: JSON.stringify({ id_token: idToken }),
      });
      this.setToken(res.access_token);
      return res;
    },

    devLogin: async (email: string = 'shivraj.dhote@finex.internal', name: string = 'Shivraj Dhote') => {
      const res = await this.request<{
        access_token: string;
        token_type: string;
        expires_in: number;
        user_id: string;
        email: string;
        name: string;
      }>('/auth/dev-login', {
        method: 'POST',
        body: JSON.stringify({ email, name, user_id: 'usr-shivraj-001' }),
      });
      this.setToken(res.access_token);
      return res;
    },

    getMe: async () => {
      return this.request<{
        user_id: string;
        email: string;
        full_name: string;
        display_name: string;
        experience_level: string;
        country: string;
        onboarding_completed: boolean;
        risk_band: string;
        composite_score: number;
        verified_identity: boolean;
      }>('/users/me');
    },

    recordConsent: async (consentVersion: string = 'v1.0') => {
      return this.request<{
        user_id: string;
        consent_version: string;
        terms_accepted: boolean;
        privacy_accepted: boolean;
        educational_disclaimer_accepted: boolean;
        status: string;
      }>('/users/consent', {
        method: 'POST',
        body: JSON.stringify({
          consent_version: consentVersion,
          terms_accepted: true,
          privacy_accepted: true,
          educational_disclaimer_accepted: true,
        }),
      });
    },

    logout: async () => {
      try {
        const token = this.getToken();
        if (token) {
          await this.request('/auth/revoke', {
            method: 'POST',
            body: JSON.stringify({ token }),
          });
        }
      } catch {
        // ignore logout errors
      } finally {
        this.setToken(null);
      }
    },
  };

  // --- Risk Profile Questionnaire ---
  public risk = {
    getQuestions: async () => {
      return this.request<any>('/risk/questions');
    },

    submitAssessment: async (submission: {
      investor_horizon: string;
      risk_tolerance: string;
      liquidity_need: string;
      financial_literacy?: string;
    }) => {
      return this.request<{
        score: number;
        risk_band: string;
        summary: string;
        suggested_allocation: Record<string, number>;
      }>('/risk/assessments', {
        method: 'POST',
        body: JSON.stringify(submission),
      });
    },

    getMyAssessment: async () => {
      return this.request<any>('/risk/assessments/me');
    },
  };

  // --- Market Data ---
  public market = {
    getInstruments: async () => {
      return this.request<{
        instruments: Array<{
          symbol: string;
          provider_symbol: string;
          canonical_id: string;
          name: string;
          sector: string;
          exchange: string;
          currency: string;
        }>;
        total: number;
      }>('/market/instruments');
    },

    getQuote: async (symbol: string) => {
      return this.request<{
        canonical_id: string;
        symbol: string;
        price: string | number;
        currency: string;
        observed_at: string;
        ingested_at: string;
        source: string;
        served_from_cache: boolean;
        is_delayed: boolean;
        is_stale: boolean;
        data_status: string;
      }>(`/market/quotes/${symbol}`);
    },

    getHistory: async (symbol: string, startDate?: string, endDate?: string) => {
      const q = new URLSearchParams();
      if (startDate) q.set('start_date', startDate);
      if (endDate) q.set('end_date', endDate);
      const queryStr = q.toString() ? `?${q.toString()}` : '';
      return this.request<{
        symbol: string;
        bars: Array<{
          date: string;
          open: string | number;
          high: string | number;
          low: string | number;
          close: string | number;
          volume: number;
          currency: string;
        }>;
      }>(`/market/history/${symbol}${queryStr}`);
    },

    search: async (query: string) => {
      return this.request<{
        query: string;
        results: any[];
        count: number;
      }>(`/market/search?query=${encodeURIComponent(query)}`);
    },
  };

  // --- Paper Trading Engine ---
  public paperTrading = {
    getAccount: async () => {
      return this.request<{
        account_id: string;
        currency: string;
        cash_balance: number;
        current_cash: number;
        positions_market_value: number;
        total_cost_basis: number;
        total_equity: number;
        total_portfolio_value: number;
        unrealized_pnl: number;
        reset_count: number;
        disclaimer: string;
        positions: Array<{
          symbol: string;
          quantity: number;
          average_buy_price: number;
          avg_cost: number;
          current_price: number;
          market_value: number;
          cost_basis: number;
          unrealized_pnl: number;
          unrealized_pnl_pct: number;
        }>;
      }>('/paper-trading/account');
    },

    getOrders: async (limit: number = 50) => {
      return this.request<{
        orders: Array<{
          id: string;
          symbol: string;
          order_type: string;
          side: string;
          status: string;
          quantity: number;
          fill_price: number;
          gross_value: number;
          cash_balance_after?: number;
          created_at: string;
        }>;
        total: number;
      }>(`/paper-trading/orders?limit=${limit}`);
    },

    submitOrder: async (
      payload: {
        symbol: string;
        side: 'BUY' | 'SELL';
        order_type: 'MARKET' | 'LIMIT' | 'STOP_LOSS' | 'SIP';
        quantity: number;
        limit_price?: number;
        stop_price?: number;
      },
      idempotencyKey?: string
    ) => {
      const key = idempotencyKey || `ord-key-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      return this.request<{
        order_id: string;
        account_id: string;
        symbol: string;
        side: string;
        status: string;
        quantity: number;
        fill_price: number;
        gross_value: number;
        cash_balance_after: number;
        replayed: boolean;
      }>('/paper-trading/orders', {
        method: 'POST',
        headers: {
          'X-Idempotency-Key': key,
        },
        body: JSON.stringify(payload),
      });
    },

    deposit: async (amount: number) => {
      return this.request<{
        account_id: string;
        deposited: number;
        cash_balance: number;
        current_cash: number;
        entry: any;
      }>('/paper-trading/deposit', {
        method: 'POST',
        body: JSON.stringify({ amount }),
      });
    },

    resetAccount: async () => {
      return this.request('/paper-trading/reset', {
        method: 'POST',
        body: JSON.stringify({ confirm_reset: true }),
      });
    },
  };

  // --- Spending & CSV Ingestion ---
  public spending = {
    getTransactions: async (params?: { category?: string; yearMonth?: string }) => {
      const q = new URLSearchParams();
      if (params?.category) q.set('category', params.category);
      if (params?.yearMonth) q.set('year_month', params.yearMonth);
      const queryStr = q.toString() ? `?${q.toString()}` : '';
      return this.request<{
        total: number;
        transactions: Array<{
          id: string;
          transaction_date: string;
          amount: number;
          transaction_type: string;
          masked_description: string;
          category_id: string;
          categorization_method: string;
          confidence_score: number;
          is_reviewed: boolean;
        }>;
      }>(`/spending/transactions${queryStr}`);
    },

    getSummary: async (yearMonth?: string) => {
      const q = yearMonth ? `?year_month=${yearMonth}` : '';
      return this.request<{
        user_id: string;
        year_month: string;
        total_debit: number;
        total_credit: number;
        net_savings: number;
        savings_rate_pct: number;
        transaction_count: number;
        category_breakdown: Record<string, number>;
      }>(`/spending/summary${q}`);
    },

    previewCsv: async (fileName: string, csvContent: string) => {
      return this.request<{
        preview_id: string;
        file_name: string;
        total_rows: number;
        valid_count: number;
        duplicate_count: number;
        invalid_count: number;
        valid_rows: any[];
        invalid_rows: any[];
        status: string;
      }>('/spending/upload/preview', {
        method: 'POST',
        body: JSON.stringify({ file_name: fileName, csv_content: csvContent }),
      });
    },

    commitCsv: async (previewId: string, acceptedIndices?: number[]) => {
      return this.request<{
        upload_id: string;
        accepted_count: number;
        quarantined_count: number;
        status: string;
        replayed: boolean;
      }>('/spending/upload/commit', {
        method: 'POST',
        body: JSON.stringify({ preview_id: previewId, accepted_indices: acceptedIndices }),
      });
    },

    addManual: async (item: {
      transaction_date: string;
      amount: number;
      description: string;
      transaction_type?: string;
      category_id?: string;
    }) => {
      return this.request<any>('/spending/manual', {
        method: 'POST',
        body: JSON.stringify(item),
      });
    },
  };

  // --- Goals ---
  public goals = {
    listGoals: async () => {
      return this.request<{
        goals: Array<{
          id: string;
          name: string;
          category: string;
          target_amount: number;
          current_amount: number;
          target_date: string;
          monthly_sip_amount: number;
          progress_pct: number;
          status: string;
        }>;
      }>('/goals');
    },

    createGoal: async (goal: {
      name: string;
      category: string;
      target_amount: number;
      initial_amount: number;
      target_date: string;
      monthly_contribution: number;
    }) => {
      return this.request<any>('/goals', {
        method: 'POST',
        body: JSON.stringify(goal),
      });
    },

    addContribution: async (goalId: string, amount: number) => {
      return this.request<any>(`/goals/${goalId}/contributions`, {
        method: 'POST',
        body: JSON.stringify({ amount }),
      });
    },
  };

  // --- Alerts & Notifications ---
  public alerts = {
    getRules: async () => {
      return this.request<any[]>('/alerts/rules');
    },

    getNotifications: async (unreadOnly: boolean = false) => {
      return this.request<{
        notifications: Array<{
          id: string;
          user_id: string;
          category: string;
          title: string;
          body: string;
          is_read: boolean;
          created_at: string;
        }>;
        count: number;
      }>(`/alerts/notifications?unread_only=${unreadOnly}`);
    },

    markRead: async (notifId: string) => {
      return this.request<any>(`/alerts/notifications/${notifId}/read`, {
        method: 'POST',
      });
    },

    markAllRead: async () => {
      return this.request<any>('/alerts/notifications/read-all', {
        method: 'POST',
      });
    },
  };

  // --- AI RAG Assistant ---
  public ai = {
    getConversations: async () => {
      return this.request<{
        conversations: Array<{
          id: string;
          title: string;
          created_at: string;
          updated_at: string;
        }>;
      }>('/ai/conversations');
    },

    getMessages: async (conversationId: string) => {
      return this.request<{
        conversation_id: string;
        messages: Array<{
          id: string;
          role: 'user' | 'assistant';
          headline?: string;
          content: string;
          citations?: Array<{
            chunk_id: string;
            document_id: string;
            title: string;
            publisher: string;
            section?: string;
            page_number?: number;
            source_url?: string;
            published_date: string;
            excerpt: string;
          }>;
          legal_disclaimer?: string;
          created_at: string;
        }>;
      }>(`/ai/conversations/${conversationId}/messages`);
    },

    sendMessage: async (conversationId: string, content: string) => {
      return this.request<{
        user_message: any;
        assistant_message: {
          id: string;
          role: 'assistant';
          headline: string;
          content: string;
          citations: Array<{
            chunk_id: string;
            document_id: string;
            title: string;
            publisher: string;
            section?: string;
            page_number?: number;
            source_url?: string;
            published_date: string;
            excerpt: string;
          }>;
          legal_disclaimer?: string;
          created_at: string;
        };
      }>(`/ai/conversations/${conversationId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content }),
      });
    },
  };
}

export const apiClient = new ApiClient();
