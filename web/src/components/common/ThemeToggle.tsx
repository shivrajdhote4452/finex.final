import React, { useState, useRef, useEffect } from 'react';
import { useTheme, ThemeMode } from '../../context/ThemeContext';

interface ThemeToggleProps {
  variant?: 'segmented' | 'dropdown' | 'cards' | 'icon-button';
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ variant = 'segmented', className = '' }) => {
  const { themeMode, resolvedTheme, setThemeMode } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isOpen]);

  const options: { id: ThemeMode; label: string; icon: string; description: string }[] = [
    {
      id: 'system',
      label: 'System',
      icon: '💻',
      description: `Follow computer theme (Current: ${resolvedTheme === 'dark' ? 'Dark' : 'Light'})`,
    },
    {
      id: 'light',
      label: 'Light',
      icon: '☀️',
      description: 'Crisp daylight palette with soft paper contrast',
    },
    {
      id: 'dark',
      label: 'Dark',
      icon: '🌙',
      description: 'Pure black graphite terminal with warm amber glow',
    },
  ];

  // 1. Segmented 3-button pill (great for top header)
  if (variant === 'segmented') {
    return (
      <div
        className={`theme-toggle-segmented ${className}`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          backgroundColor: 'var(--bg-input)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: '2px',
          gap: '2px',
        }}
        role="group"
        aria-label="Theme selection"
      >
        {options.map((opt) => {
          const isSelected = themeMode === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => setThemeMode(opt.id)}
              title={opt.description}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: isSelected ? 700 : 500,
                color: isSelected ? 'var(--color-action)' : 'var(--text-muted)',
                backgroundColor: isSelected ? 'var(--color-action-bg)' : 'transparent',
                border: isSelected ? '1px solid var(--color-action-border)' : '1px solid transparent',
                borderRadius: 'var(--radius-xs)',
                cursor: 'pointer',
                transition: 'all var(--transition-fast)',
                fontFamily: 'var(--font-sans)',
                outline: 'none',
              }}
            >
              <span style={{ fontSize: '12px', lineHeight: 1 }}>{opt.icon}</span>
              <span className="theme-toggle-label">{opt.label}</span>
            </button>
          );
        })}
      </div>
    );
  }

  // 2. Dropdown popup variant
  if (variant === 'dropdown') {
    const currentOpt = options.find((o) => o.id === themeMode) || options[0];
    return (
      <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block' }} className={className}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            backgroundColor: 'var(--bg-input)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-xs)',
            color: 'var(--text-primary)',
            fontSize: '12px',
            cursor: 'pointer',
            transition: 'border-color var(--transition-fast)',
          }}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        >
          <span>{currentOpt.icon}</span>
          <span style={{ fontWeight: 600 }}>{currentOpt.label}</span>
          <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>{isOpen ? '▲' : '▼'}</span>
        </button>

        {isOpen && (
          <div
            style={{
              position: 'absolute',
              top: 'calc(100% + 6px)',
              right: 0,
              width: '210px',
              backgroundColor: 'var(--bg-dropdown, var(--bg-card))',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--dropdown-shadow, 0 8px 24px rgba(0,0,0,0.5))',
              padding: '6px',
              zIndex: 100,
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
            role="listbox"
          >
            {options.map((opt) => {
              const isSelected = themeMode === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    setThemeMode(opt.id);
                    setIsOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 10px',
                    backgroundColor: isSelected ? 'var(--color-action-bg)' : 'transparent',
                    border: 'none',
                    borderRadius: 'var(--radius-xs)',
                    color: isSelected ? 'var(--color-action)' : 'var(--text-primary)',
                    textAlign: 'left',
                    cursor: 'pointer',
                    fontSize: '12px',
                    transition: 'background-color var(--transition-fast)',
                  }}
                  role="option"
                  aria-selected={isSelected}
                >
                  <span style={{ fontSize: '15px' }}>{opt.icon}</span>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: isSelected ? 700 : 500 }}>{opt.label}</span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {opt.id === 'system' ? `Auto (${resolvedTheme})` : opt.id === 'light' ? 'Daylight' : 'OLED Dark'}
                    </span>
                  </div>
                  {isSelected && (
                    <span style={{ marginLeft: 'auto', color: 'var(--color-action)', fontWeight: 700 }}>✓</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // 3. Settings Cards variant (Detailed options with preview)
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }} className={className}>
      {options.map((opt) => {
        const isSelected = themeMode === opt.id;
        return (
          <div
            key={opt.id}
            onClick={() => setThemeMode(opt.id)}
            className="glass-card"
            style={{
              padding: '16px',
              cursor: 'pointer',
              border: isSelected ? '2px solid var(--color-action)' : '1px solid var(--border-subtle)',
              backgroundColor: isSelected ? 'var(--color-action-bg)' : 'var(--bg-card)',
              boxShadow: isSelected ? 'var(--border-glow)' : 'none',
              transition: 'all var(--transition-fast)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '20px' }}>{opt.icon}</span>
                <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>{opt.label}</span>
              </div>
              <div
                style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  border: isSelected ? '5px solid var(--color-action)' : '2px solid var(--border-medium)',
                  backgroundColor: isSelected ? '#FFFFFF' : 'transparent',
                  transition: 'all var(--transition-fast)',
                }}
              />
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>
              {opt.description}
            </p>

            {/* Mini Color Palette Bar Preview */}
            <div
              style={{
                display: 'flex',
                height: '8px',
                borderRadius: 'var(--radius-xs)',
                overflow: 'hidden',
                border: '1px solid var(--border-subtle)',
                marginTop: '4px',
              }}
            >
              {opt.id === 'light' ? (
                <>
                  <div style={{ flex: 2, backgroundColor: '#F8F9FA' }} />
                  <div style={{ flex: 1, backgroundColor: '#D96B27' }} />
                  <div style={{ flex: 1, backgroundColor: '#059669' }} />
                  <div style={{ flex: 1, backgroundColor: '#111827' }} />
                </>
              ) : opt.id === 'dark' ? (
                <>
                  <div style={{ flex: 2, backgroundColor: '#000000' }} />
                  <div style={{ flex: 1, backgroundColor: '#F29A60' }} />
                  <div style={{ flex: 1, backgroundColor: '#4DD5AD' }} />
                  <div style={{ flex: 1, backgroundColor: '#FFFFFF' }} />
                </>
              ) : (
                <>
                  <div style={{ flex: 2, background: 'linear-gradient(90deg, #F8F9FA 50%, #000000 50%)' }} />
                  <div style={{ flex: 1, backgroundColor: 'var(--color-action)' }} />
                  <div style={{ flex: 1, backgroundColor: 'var(--color-positive)' }} />
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
