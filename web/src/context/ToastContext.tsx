import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

export type ToastType = 'success' | 'error' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  title?: string;
  duration?: number;
}

interface ToastContextType {
  toasts: ToastItem[];
  showToast: (message: string, type?: ToastType, title?: string, duration?: number) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = 'info', title?: string, duration: number = 4000) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev, { id, type, message, title, duration }]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, showToast, removeToast }}>
      {children}
      <div className="finex-toast-container" aria-live="polite">
        {toasts.map((t) => {
          const typeClass =
            t.type === 'success'
              ? 'finex-toast-success'
              : t.type === 'error'
              ? 'finex-toast-error'
              : 'finex-toast-info';

          const iconColor =
            t.type === 'success'
              ? 'var(--color-profit)'
              : t.type === 'error'
              ? 'var(--color-loss)'
              : 'var(--color-action)';

          return (
            <div key={t.id} className={`finex-toast ${typeClass}`} role="alert">
              <div
                style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: iconColor,
                  fontWeight: 700,
                  fontSize: '12px',
                  flexShrink: 0,
                  marginTop: '1px',
                }}
              >
                {t.type === 'success' ? '✓' : t.type === 'error' ? '!' : 'ℹ'}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                {t.title && (
                  <div
                    style={{
                      fontWeight: 600,
                      color: '#FFFFFF',
                      marginBottom: '2px',
                      fontSize: '13px',
                    }}
                  >
                    {t.title}
                  </div>
                )}
                <div style={{ color: 'var(--text-primary)', lineHeight: 1.4, wordBreak: 'break-word' }}>
                  {t.message}
                </div>
              </div>
              <button
                type="button"
                onClick={() => removeToast(t.id)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '16px',
                  lineHeight: 1,
                  padding: '2px 4px',
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-xs)',
                  marginLeft: '4px',
                }}
                aria-label="Dismiss notification"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

export default ToastProvider;
