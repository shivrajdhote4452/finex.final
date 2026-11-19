import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';
import {
  HORIZON_OPTIONS,
  RISK_QUESTIONS,
  evaluateDeterministicRisk,
  RiskEvaluationResult,
} from '../domain/riskEvaluation';

interface OnboardingScreenProps {
  onComplete: () => void;
}

const STORAGE_KEY = 'finex_onboarding_draft';

interface OnboardingDraft {
  step: 1 | 2 | 3 | 4;
  maxStepReached: number;
  q1Option: string;
  q3Option: string;
  selectedHorizon: string;
  q2Option: string;
  q4Option: string;
}

const OnboardingStepper: React.FC<{
  activeStepIndex: 1 | 2 | 3 | 4;
  maxStepReached: number;
  onSelectStep: (step: 1 | 2 | 3 | 4) => void;
}> = ({ activeStepIndex, maxStepReached, onSelectStep }) => {
  const steps: Array<{ num: string; label: string; index: 1 | 2 | 3 | 4 }> = [
    { num: '01', label: 'Basics', index: 1 },
    { num: '02', label: 'Time horizon', index: 2 },
    { num: '03', label: 'Capacity', index: 3 },
    { num: '04', label: 'Review', index: 4 },
  ];

  return (
    <div
      style={{
        display: 'flex',
        gap: '20px',
        marginBottom: '28px',
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '14px',
        overflowX: 'auto',
        whiteSpace: 'nowrap',
        scrollbarWidth: 'none',
      }}
      role="navigation"
      aria-label="Onboarding Progress"
    >
      {steps.map((s) => {
        const isActive = s.index === activeStepIndex;
        const isClickable = s.index <= maxStepReached;
        return (
          <button
            key={s.num}
            type="button"
            onClick={() => isClickable && onSelectStep(s.index)}
            disabled={!isClickable}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              cursor: isClickable ? 'pointer' : 'default',
              fontSize: '12px',
              color: isActive
                ? 'var(--color-action)'
                : isClickable
                ? 'var(--text-main)'
                : 'var(--text-faint)',
              fontWeight: isActive ? 700 : 500,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              flexShrink: 0,
              opacity: !isClickable && !isActive ? 0.6 : 1,
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                color: isActive ? 'var(--color-action)' : 'inherit',
              }}
            >
              {s.num}
            </span>
            <span>{s.label}</span>
          </button>
        );
      })}
    </div>
  );
};

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({ onComplete }) => {
  // Restore draft or use default baseline values
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [step, setStepState] = useState<1 | 2 | 3 | 4>(1);
  const [maxStepReached, setMaxStepReached] = useState<number>(1);

  // Questionnaire selections
  const [q1Option, setQ1Option] = useState<string>('Q1_C');
  const [q3Option, setQ3Option] = useState<string>('Q3_B');
  const [selectedHorizon, setSelectedHorizon] = useState<string>('3-5');
  const [q2Option, setQ2Option] = useState<string>('Q2_C');
  const [q4Option, setQ4Option] = useState<string>('Q4_C');

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [evaluatedProfile, setEvaluatedProfile] = useState<RiskEvaluationResult>(() =>
    evaluateDeterministicRisk('3-5', {
      Q1: 'Q1_C',
      Q2: 'Q2_C',
      Q3: 'Q3_B',
      Q4: 'Q4_C',
    })
  );

  // Recalculate deterministic profile whenever selections change
  useEffect(() => {
    const updated = evaluateDeterministicRisk(selectedHorizon, {
      Q1: q1Option,
      Q2: q2Option,
      Q3: q3Option,
      Q4: q4Option,
    });
    setEvaluatedProfile(updated);
  }, [selectedHorizon, q1Option, q2Option, q3Option, q4Option]);

  // Synchronize step and browser history
  const setStep = useCallback((newStep: 1 | 2 | 3 | 4, updateHistory = true) => {
    setStepState(newStep);
    setMaxStepReached((prev) => Math.max(prev, newStep));
    setSubmitError(null);
    if (updateHistory && typeof window !== 'undefined') {
      window.history.pushState({ onboardingStep: newStep }, '', `#step=${newStep}`);
    }
  }, []);

  // Restore draft from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed: Partial<OnboardingDraft> = JSON.parse(saved);
        if (parsed.q1Option) setQ1Option(parsed.q1Option);
        if (parsed.q3Option) setQ3Option(parsed.q3Option);
        if (parsed.selectedHorizon) setSelectedHorizon(parsed.selectedHorizon);
        if (parsed.q2Option) setQ2Option(parsed.q2Option);
        if (parsed.q4Option) setQ4Option(parsed.q4Option);
        if (parsed.maxStepReached) setMaxStepReached(parsed.maxStepReached);
        if (parsed.step && [1, 2, 3, 4].includes(parsed.step)) {
          setStepState(parsed.step as 1 | 2 | 3 | 4);
        }
      }
    } catch {
      // storage unavailable, use defaults
    } finally {
      setDraftLoaded(true);
    }
  }, []);

  // Sync draft to localStorage
  useEffect(() => {
    if (!draftLoaded) return;
    try {
      const draft: OnboardingDraft = {
        step,
        maxStepReached,
        q1Option,
        q3Option,
        selectedHorizon,
        q2Option,
        q4Option,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
    } catch {
      // storage unavailable
    }
  }, [draftLoaded, step, maxStepReached, q1Option, q3Option, selectedHorizon, q2Option, q4Option]);

  // Support browser Back/Forward navigation
  useEffect(() => {
    const handlePopState = (event: PopStateEvent) => {
      if (event.state && event.state.onboardingStep) {
        const stepNum = event.state.onboardingStep;
        if ([1, 2, 3, 4].includes(stepNum)) {
          setStepState(stepNum as 1 | 2 | 3 | 4);
        }
      } else if (window.location.hash.startsWith('#step=')) {
        const num = parseInt(window.location.hash.replace('#step=', ''), 10);
        if ([1, 2, 3, 4].includes(num)) {
          setStepState(num as 1 | 2 | 3 | 4);
        }
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Compute profile and advance to Step 4 review screen
  const handleCalculateProfile = () => {
    setLoading(true);
    setSubmitError(null);
    setStep(4);
    setLoading(false);
  };

  // Authoritative submission on Step 4
  const handleFinalConfirm = async () => {
    if (submitting) return;
    setSubmitting(true);
    setSubmitError(null);

    const submissionPayload = {
      questionnaire_version: 'v1.0',
      horizon_category: selectedHorizon,
      answers: [
        { question_id: 'Q1', option_id: q1Option },
        { question_id: 'Q2', option_id: q2Option },
        { question_id: 'Q3', option_id: q3Option },
        { question_id: 'Q4', option_id: q4Option },
      ],
    };

    // If user has active authentication session, persist server-authoritatively
    if (apiClient.isAuthenticated()) {
      try {
        const res = await apiClient.risk.submitAssessment(submissionPayload);
        if (!res || !res.risk_band) {
          throw new Error('Server returned an invalid or incomplete assessment response.');
        }
      } catch (err: any) {
        setSubmitting(false);
        const errorDetail =
          err?.message ||
          (typeof err === 'string'
            ? err
            : 'Unable to save risk assessment to server. Please check your connection and retry.');
        setSubmitError(errorDetail);
        // CRITICAL: Do NOT call onComplete() and do NOT remove draft to prevent false success
        return;
      }
    }

    // Success: cleanup draft and transition to authenticated workspace
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    setSubmitting(false);
    onComplete();
  };

  // -------------------------------------------------------------
  // STEP 4: RISK RESULT & EXPLANATION (REVIEW STAGE)
  // -------------------------------------------------------------
  if (step === 4) {
    const horizonItem = HORIZON_OPTIONS.find((o) => o.id === selectedHorizon) || HORIZON_OPTIONS[2];
    const q1Item = RISK_QUESTIONS.Q1.options.find((o) => o.id === q1Option);
    const q3Item = RISK_QUESTIONS.Q3.options.find((o) => o.id === q3Option);
    const q2Item = RISK_QUESTIONS.Q2.options.find((o) => o.id === q2Option);
    const q4Item = RISK_QUESTIONS.Q4.options.find((o) => o.id === q4Option);

    return (
      <div style={{ maxWidth: '960px', margin: '0 auto', padding: '16px 0' }}>
        <div
          style={{
            fontSize: '11px',
            color: 'var(--color-action)',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
        >
          RISK RESULT &amp; EXPLANATION • STEP 4 OF 4
        </div>
        <h1 style={{ fontSize: '32px', fontWeight: 700, color: 'var(--text-main)', margin: '6px 0 4px 0' }}>
          Your risk profile
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px', lineHeight: 1.5 }}>
          Deterministic score via FinEx Risk Engine:{' '}
          <span style={{ color: 'var(--text-main)', fontWeight: 600, whiteSpace: 'nowrap' }}>
            {evaluatedProfile.composite_score}/100.
          </span>
        </p>

        <OnboardingStepper activeStepIndex={4} maxStepReached={maxStepReached} onSelectStep={setStep} />

        <div className="onboarding-result-grid">
          {/* Profile Summary Panel */}
          <div
            className="glass-card"
            style={{ padding: '28px', border: '1px solid var(--border-medium)', backgroundColor: 'var(--bg-card)' }}
          >
            <div
              style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              Profile summary
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-action)', fontWeight: 600, marginTop: '2px' }}>
              Verified deterministic result
            </div>
            <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--text-main)', margin: '14px 0 8px 0' }}>
              {evaluatedProfile.risk_band}
            </div>
            <p style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--text-muted)', marginBottom: '16px' }}>
              {evaluatedProfile.explanation}
            </p>

            {/* Asset Allocation Breakdown */}
            <div
              style={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '12px 14px',
                marginBottom: '18px',
              }}
            >
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--text-main)',
                  textTransform: 'uppercase',
                  marginBottom: '8px',
                  letterSpacing: '0.03em',
                }}
              >
                Suggested Allocation
              </div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${evaluatedProfile.suggested_allocation.Equity}%`, backgroundColor: 'var(--color-action)' }} title="Equity" />
                <div style={{ width: `${evaluatedProfile.suggested_allocation.Debt}%`, backgroundColor: '#0284C7' }} title="Debt" />
                <div style={{ width: `${evaluatedProfile.suggested_allocation.Gold}%`, backgroundColor: '#F59E0B' }} title="Gold" />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                <span>Equity: <strong style={{ color: 'var(--text-main)' }}>{evaluatedProfile.suggested_allocation.Equity}%</strong></span>
                <span>Debt: <strong style={{ color: 'var(--text-main)' }}>{evaluatedProfile.suggested_allocation.Debt}%</strong></span>
                <span>Gold: <strong style={{ color: 'var(--text-main)' }}>{evaluatedProfile.suggested_allocation.Gold}%</strong></span>
              </div>
            </div>

            <div
              onClick={() => setStep(3)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setStep(3);
                }
              }}
              style={{
                fontSize: '12px',
                color: 'var(--color-action)',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                marginBottom: '16px',
              }}
            >
              ← Review or edit answers
            </div>

            <div
              style={{
                fontSize: '11px',
                color: 'var(--text-faint)',
                borderTop: '1px solid var(--border-subtle)',
                paddingTop: '12px',
                marginBottom: '20px',
                lineHeight: 1.4,
              }}
            >
              No return is guaranteed. All portfolio models on FinEx use simulated virtual capital for educational learning.
            </div>

            {submitError && (
              <div
                role="alert"
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid #EF4444',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 14px',
                  marginBottom: '14px',
                  color: '#EF4444',
                  fontSize: '12px',
                  lineHeight: 1.4,
                }}
              >
                <strong>Unable to save profile:</strong> {submitError}
              </div>
            )}

            {/* Primary Action Button */}
            <button
              type="button"
              onClick={handleFinalConfirm}
              disabled={submitting}
              className="btn btn-action"
              style={{
                width: '100%',
                padding: '12px 20px',
                fontSize: '14px',
                fontWeight: 700,
                cursor: submitting ? 'wait' : 'pointer',
                borderRadius: 'var(--radius-sm)',
                opacity: submitting ? 0.7 : 1,
              }}
            >
              {submitting ? 'Saving Profile...' : submitError ? 'Retry Confirm Profile →' : 'Confirm profile →'}
            </button>
          </div>

          {/* Influencing Answers Panel */}
          <div className="glass-card" style={{ padding: '28px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '20px' }}>
              What influenced the result
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              {/* 01 Time horizon */}
              <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-action)', fontWeight: 700 }}>
                      01
                    </span>
                    <strong style={{ color: 'var(--text-main)', fontSize: '13px' }}>Time horizon</strong>
                  </div>
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-action)',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: '2px 6px',
                    }}
                  >
                    Edit
                  </button>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', paddingLeft: '24px', margin: 0 }}>
                  Selected: <strong style={{ color: 'var(--text-main)' }}>{horizonItem.title}</strong> ({horizonItem.desc}).
                </p>
              </div>

              {/* 02 Willingness to take risk */}
              <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-action)', fontWeight: 700 }}>
                      02
                    </span>
                    <strong style={{ color: 'var(--text-main)', fontSize: '13px' }}>Willingness to take risk</strong>
                  </div>
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-action)',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: '2px 6px',
                    }}
                  >
                    Edit
                  </button>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', paddingLeft: '24px' }}>
                  <div>Correction response: <strong style={{ color: 'var(--text-main)' }}>{q1Item?.text}</strong></div>
                  <div style={{ marginTop: '2px' }}>Return objective: <strong style={{ color: 'var(--text-main)' }}>{q3Item?.text}</strong></div>
                </div>
              </div>

              {/* 03 Capacity to absorb loss */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-action)', fontWeight: 700 }}>
                      03
                    </span>
                    <strong style={{ color: 'var(--text-main)', fontSize: '13px' }}>Capacity to absorb loss</strong>
                  </div>
                  <button
                    type="button"
                    onClick={() => setStep(3)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-action)',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: '2px 6px',
                    }}
                  >
                    Edit
                  </button>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', paddingLeft: '24px' }}>
                  <div>Emergency buffer: <strong style={{ color: 'var(--text-main)' }}>{q2Item?.text}</strong></div>
                  <div style={{ marginTop: '2px' }}>Debt ratio (EMIs): <strong style={{ color: 'var(--text-main)' }}>{q4Item?.text}</strong></div>
                </div>
              </div>
            </div>

            {/* Citation & Regulatory Notice */}
            <div
              style={{
                marginTop: '22px',
                padding: '12px 14px',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-card)',
                fontSize: '11px',
                color: 'var(--text-muted)',
                lineHeight: 1.5,
              }}
            >
              <div style={{ fontWeight: 700, color: 'var(--color-action)', marginBottom: '4px' }}>
                SEBI EDUCATIONAL CITATION
              </div>
              {evaluatedProfile.citation}
            </div>

            {submitError && (
              <div
                role="alert"
                style={{
                  marginTop: '16px',
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid #EF4444',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 14px',
                  color: '#EF4444',
                  fontSize: '12px',
                  lineHeight: 1.4,
                }}
              >
                <strong>Submission Error:</strong> {submitError}
              </div>
            )}

            <div style={{ marginTop: '28px', display: 'flex', gap: '12px', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => setStep(3)}
                disabled={submitting}
                className="btn btn-secondary"
                style={{ flex: '1 1 auto' }}
              >
                Review answers
              </button>
              <button
                type="button"
                onClick={handleFinalConfirm}
                disabled={submitting}
                className="btn btn-action"
                style={{
                  flex: '1 1 auto',
                  cursor: submitting ? 'wait' : 'pointer',
                  opacity: submitting ? 0.7 : 1,
                }}
              >
                {submitting ? 'Saving...' : submitError ? 'Retry Confirm →' : 'Confirm profile →'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // STEP 1: BASICS (WILLINGNESS TO TAKE RISK)
  // -------------------------------------------------------------
  if (step === 1) {
    const q1 = RISK_QUESTIONS.Q1;
    const q3 = RISK_QUESTIONS.Q3;

    return (
      <div style={{ maxWidth: '960px', margin: '0 auto', padding: '16px 0' }}>
        <div
          style={{
            fontSize: '11px',
            color: 'var(--color-action)',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
        >
          RISK ONBOARDING • STEP 1 OF 4
        </div>
        <h1 style={{ fontSize: '32px', fontWeight: 700, color: 'var(--text-main)', margin: '6px 0 4px 0' }}>
          Understand your risk willingness
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
          Questionnaire step 1 of 3 (Basics). Evaluates your psychological comfort with market fluctuations.
        </p>

        <OnboardingStepper activeStepIndex={1} maxStepReached={maxStepReached} onSelectStep={setStep} />

        <div className="onboarding-risk-grid">
          {/* Questions Container */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Question 1: Market Correction */}
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>
                1. Market Correction Reaction
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                {q1.prompt}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {q1.options.map((opt) => {
                  const isSelected = q1Option === opt.id;
                  return (
                    <div
                      key={opt.id}
                      onClick={() => setQ1Option(opt.id)}
                      className="glass-card glass-card-interactive"
                      role="radio"
                      aria-checked={isSelected}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setQ1Option(opt.id);
                        }
                      }}
                      style={{
                        padding: '14px 18px',
                        border: isSelected ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                        backgroundColor: isSelected ? 'var(--color-action-bg)' : 'var(--bg-card)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      <div
                        style={{
                          width: '16px',
                          height: '16px',
                          borderRadius: '50%',
                          border: isSelected ? '5px solid var(--color-action)' : '2px solid var(--border-medium)',
                          backgroundColor: 'var(--bg-card)',
                          flexShrink: 0,
                        }}
                      />
                      <div style={{ fontWeight: 500, fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.4 }}>
                        {opt.text}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Question 2: Target Return Profile */}
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>
                2. Primary Return Objective
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                {q3.prompt}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {q3.options.map((opt) => {
                  const isSelected = q3Option === opt.id;
                  return (
                    <div
                      key={opt.id}
                      onClick={() => setQ3Option(opt.id)}
                      className="glass-card glass-card-interactive"
                      role="radio"
                      aria-checked={isSelected}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setQ3Option(opt.id);
                        }
                      }}
                      style={{
                        padding: '14px 18px',
                        border: isSelected ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                        backgroundColor: isSelected ? 'var(--color-action-bg)' : 'var(--bg-card)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      <div
                        style={{
                          width: '16px',
                          height: '16px',
                          borderRadius: '50%',
                          border: isSelected ? '5px solid var(--color-action)' : '2px solid var(--border-medium)',
                          backgroundColor: 'var(--bg-card)',
                          flexShrink: 0,
                        }}
                      />
                      <div style={{ fontWeight: 500, fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.4 }}>
                        {opt.text}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Navigation Buttons */}
            <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
              <button
                type="button"
                disabled
                className="btn btn-secondary"
                style={{ opacity: 0.5, cursor: 'not-allowed' }}
                title="First step of questionnaire"
              >
                Back
              </button>
              <button type="button" onClick={() => setStep(2)} className="btn btn-action">
                Continue →
              </button>
            </div>
          </div>

          {/* Right Explanatory Box: Why We Ask */}
          <div className="glass-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)' }}>
            <div
              style={{
                fontSize: '11px',
                color: 'var(--color-action)',
                fontWeight: 700,
                textTransform: 'uppercase',
                marginBottom: '8px',
                letterSpacing: '0.04em',
              }}
            >
              Why we ask
            </div>
            <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-main)', marginBottom: '16px' }}>
              Your psychological reaction to drawdown volatility and your target return expectations determine your risk willingness.
            </p>
            <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-muted)', marginBottom: '16px' }}>
              In real market cycles, panic selling during temporary pullbacks locks in permanent losses. Grounded in SEBI investor education principles, selecting an asset mix that matches your emotional tolerance helps avoid behavioral errors.
            </p>
            <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-muted)' }}>
              You can go back and revise your answers at any point before confirming your profile.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // STEP 2: TIME HORIZON
  // -------------------------------------------------------------
  if (step === 2) {
    return (
      <div style={{ maxWidth: '960px', margin: '0 auto', padding: '16px 0' }}>
        <div
          style={{
            fontSize: '11px',
            color: 'var(--color-action)',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
        >
          RISK ONBOARDING • STEP 2 OF 4
        </div>
        <h1 style={{ fontSize: '32px', fontWeight: 700, color: 'var(--text-main)', margin: '6px 0 4px 0' }}>
          Understand your investment horizon
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
          Questionnaire step 2 of 3 (Time horizon). Determines your compounding window and liquidity buffers.
        </p>

        <OnboardingStepper activeStepIndex={2} maxStepReached={maxStepReached} onSelectStep={setStep} />

        <div className="onboarding-risk-grid">
          {/* Question Options */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
              When might you need this money?
            </div>

            {HORIZON_OPTIONS.map((opt) => {
              const isSelected = selectedHorizon === opt.id;
              return (
                <div
                  key={opt.id}
                  onClick={() => setSelectedHorizon(opt.id)}
                  className="glass-card glass-card-interactive"
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedHorizon(opt.id);
                    }
                  }}
                  style={{
                    padding: '16px 20px',
                    border: isSelected ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                    backgroundColor: isSelected ? 'var(--color-action-bg)' : 'var(--bg-card)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '14px',
                    cursor: 'pointer',
                  }}
                >
                  <div
                    style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      border: isSelected ? '5px solid var(--color-action)' : '2px solid var(--border-medium)',
                      backgroundColor: 'var(--bg-card)',
                      flexShrink: 0,
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-main)' }}>{opt.title}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{opt.desc}</div>
                  </div>
                </div>
              );
            })}

            <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
              <button type="button" onClick={() => setStep(1)} className="btn btn-secondary">
                ← Back
              </button>
              <button type="button" onClick={() => setStep(3)} className="btn btn-action">
                Continue →
              </button>
            </div>
          </div>

          {/* Right Explanatory Box: Why We Ask */}
          <div className="glass-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)' }}>
            <div
              style={{
                fontSize: '11px',
                color: 'var(--color-action)',
                fontWeight: 700,
                textTransform: 'uppercase',
                marginBottom: '8px',
                letterSpacing: '0.04em',
              }}
            >
              Why we ask
            </div>
            <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-main)', marginBottom: '16px' }}>
              Your time horizon helps explain how investment risk relates to your plans. Longer timeframes allow investments to recover from cyclical market drawdowns.
            </p>
            <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-muted)', marginBottom: '16px' }}>
              Short horizons (&lt; 1 year) require strict capital preservation to protect liquid needs, while longer horizons (&gt; 5 years) unlock equity compounding potential.
            </p>
            <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-muted)' }}>
              You can go back and revise an answer before confirming your profile.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // STEP 3: CAPACITY (CAPACITY TO ABSORB LOSS)
  // -------------------------------------------------------------
  const q2 = RISK_QUESTIONS.Q2;
  const q4 = RISK_QUESTIONS.Q4;

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '16px 0' }}>
      <div
        style={{
          fontSize: '11px',
          color: 'var(--color-action)',
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}
      >
        RISK ONBOARDING • STEP 3 OF 4
      </div>
      <h1 style={{ fontSize: '32px', fontWeight: 700, color: 'var(--text-main)', margin: '6px 0 4px 0' }}>
        Assess your capacity to absorb loss
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
        Questionnaire step 3 of 3 (Capacity). Evaluates your emergency reserves and monthly debt commitments.
      </p>

      <OnboardingStepper activeStepIndex={3} maxStepReached={maxStepReached} onSelectStep={setStep} />

      <div className="onboarding-risk-grid">
        {/* Questions Container */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Question 4: Emergency Cash Reserves */}
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>
              4. Emergency Cash Reserves
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
              {q2.prompt}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {q2.options.map((opt) => {
                const isSelected = q2Option === opt.id;
                return (
                  <div
                    key={opt.id}
                    onClick={() => setQ2Option(opt.id)}
                    className="glass-card glass-card-interactive"
                    role="radio"
                    aria-checked={isSelected}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setQ2Option(opt.id);
                      }
                    }}
                    style={{
                      padding: '14px 18px',
                      border: isSelected ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                      backgroundColor: isSelected ? 'var(--color-action-bg)' : 'var(--bg-card)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '14px',
                      cursor: 'pointer',
                    }}
                  >
                    <div
                      style={{
                        width: '16px',
                        height: '16px',
                        borderRadius: '50%',
                        border: isSelected ? '5px solid var(--color-action)' : '2px solid var(--border-medium)',
                        backgroundColor: 'var(--bg-card)',
                        flexShrink: 0,
                      }}
                    />
                    <div style={{ fontWeight: 500, fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.4 }}>
                      {opt.text}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Question 5: Debt Obligations */}
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>
              5. Debt Obligations (EMIs)
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
              {q4.prompt}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {q4.options.map((opt) => {
                const isSelected = q4Option === opt.id;
                return (
                  <div
                    key={opt.id}
                    onClick={() => setQ4Option(opt.id)}
                    className="glass-card glass-card-interactive"
                    role="radio"
                    aria-checked={isSelected}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setQ4Option(opt.id);
                      }
                    }}
                    style={{
                      padding: '14px 18px',
                      border: isSelected ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                      backgroundColor: isSelected ? 'var(--color-action-bg)' : 'var(--bg-card)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '14px',
                      cursor: 'pointer',
                    }}
                  >
                    <div
                      style={{
                        width: '16px',
                        height: '16px',
                        borderRadius: '50%',
                        border: isSelected ? '5px solid var(--color-action)' : '2px solid var(--border-medium)',
                        backgroundColor: 'var(--bg-card)',
                        flexShrink: 0,
                      }}
                    />
                    <div style={{ fontWeight: 500, fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.4 }}>
                      {opt.text}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Navigation Buttons */}
          <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
            <button type="button" onClick={() => setStep(2)} className="btn btn-secondary">
              ← Back
            </button>
            <button
              type="button"
              onClick={handleCalculateProfile}
              disabled={loading}
              className="btn btn-action"
            >
              {loading ? 'Evaluating Profile...' : 'Calculate Profile →'}
            </button>
          </div>
        </div>

        {/* Right Explanatory Box: Why We Ask */}
        <div className="glass-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)' }}>
          <div
            style={{
              fontSize: '11px',
              color: 'var(--color-action)',
              fontWeight: 700,
              textTransform: 'uppercase',
              marginBottom: '8px',
              letterSpacing: '0.04em',
            }}
          >
            Why we ask
          </div>
          <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-main)', marginBottom: '16px' }}>
            Capacity represents your balance-sheet ability to sustain portfolio drawdowns without forcing premature asset liquidation.
          </p>
          <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-muted)', marginBottom: '16px' }}>
            Even if an investor has high risk tolerance, having less than 3 months of emergency reserves or more than 50% monthly income committed to EMIs constrains overall risk capacity.
          </p>
          <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-muted)' }}>
            Once you calculate your profile, you will see a transparent breakdown and can edit any answer before confirming.
          </p>
        </div>
      </div>
    </div>
  );
};
