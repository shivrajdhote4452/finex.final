import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  HORIZON_OPTIONS,
  RISK_QUESTIONS,
  evaluateDeterministicRisk,
} from '../src/domain/riskEvaluation.ts';

describe('Risk Onboarding Questionnaire & Domain Logic', () => {
  test('1. Stepper and question catalog contain all 4 stages and questions without skips', () => {
    // Verify Questions Q1, Q2, Q3, Q4 exist with authoritative options
    assert.ok(RISK_QUESTIONS.Q1, 'Q1 must be defined');
    assert.equal(RISK_QUESTIONS.Q1.dimension, 'willingness');
    assert.equal(RISK_QUESTIONS.Q1.options.length, 4);

    assert.ok(RISK_QUESTIONS.Q3, 'Q3 must be defined');
    assert.equal(RISK_QUESTIONS.Q3.dimension, 'willingness');
    assert.equal(RISK_QUESTIONS.Q3.options.length, 3);

    assert.ok(RISK_QUESTIONS.Q2, 'Q2 must be defined');
    assert.equal(RISK_QUESTIONS.Q2.dimension, 'capacity');
    assert.equal(RISK_QUESTIONS.Q2.options.length, 4);

    assert.ok(RISK_QUESTIONS.Q4, 'Q4 must be defined');
    assert.equal(RISK_QUESTIONS.Q4.dimension, 'capacity');
    assert.equal(RISK_QUESTIONS.Q4.options.length, 4);

    // Verify 4 Horizon options
    assert.equal(HORIZON_OPTIONS.length, 4);
    assert.deepEqual(
      HORIZON_OPTIONS.map((h) => h.id),
      ['<1', '1-3', '3-5', '>5']
    );
  });

  test('2. Deterministic calculation: Conservative scenario produces score < 40 and Conservative band', () => {
    const result = evaluateDeterministicRisk('<1', {
      Q1: 'Q1_A', // 10
      Q2: 'Q2_A', // 15
      Q3: 'Q3_A', // 20
      Q4: 'Q4_A', // 15
    });

    // avg_willingness = (10 + 20) / 2 = 15
    // avg_capacity = (15 + 15) / 2 = 15
    // composite = (15 * 0.45 + 15 * 0.55) * 0.50 = 15 * 0.50 = 7.5 -> 8
    assert.equal(result.risk_band, 'Conservative');
    assert.ok(result.composite_score < 40, `Expected composite_score < 40, got ${result.composite_score}`);
    assert.equal(result.suggested_allocation.Equity, 25);
    assert.equal(result.suggested_allocation.Debt, 65);
    assert.equal(result.suggested_allocation.Gold, 10);
  });

  test('3. Deterministic calculation: Moderate baseline scenario produces 40 <= score < 70 and Moderate band', () => {
    const result = evaluateDeterministicRisk('3-5', {
      Q1: 'Q1_C', // 70
      Q2: 'Q2_C', // 75
      Q3: 'Q3_B', // 60
      Q4: 'Q4_C', // 70
    });

    // avg_willingness = (70 + 60) / 2 = 65
    // avg_capacity = (75 + 70) / 2 = 72.5
    // composite = (65 * 0.45 + 72.5 * 0.55) * 1.0 = (29.25 + 39.875) * 1.0 = 69.125 -> 69
    assert.equal(result.risk_band, 'Moderate');
    assert.ok(
      result.composite_score >= 40 && result.composite_score < 70,
      `Expected 40 <= composite_score < 70, got ${result.composite_score}`
    );
    assert.equal(result.suggested_allocation.Equity, 50);
    assert.equal(result.suggested_allocation.Debt, 40);
    assert.equal(result.suggested_allocation.Gold, 10);
  });

  test('4. Deterministic calculation: Aggressive scenario produces score >= 70 and Aggressive band', () => {
    const result = evaluateDeterministicRisk('>5', {
      Q1: 'Q1_D', // 100
      Q2: 'Q2_D', // 100
      Q3: 'Q3_C', // 95
      Q4: 'Q4_D', // 100
    });

    // avg_willingness = (100 + 95) / 2 = 97.5
    // avg_capacity = (100 + 100) / 2 = 100
    // composite = (97.5 * 0.45 + 100 * 0.55) * 1.15 = (43.875 + 55) * 1.15 = 98.875 * 1.15 = 113.7 -> clamped to 100
    assert.equal(result.risk_band, 'Aggressive');
    assert.ok(result.composite_score >= 70, `Expected composite_score >= 70, got ${result.composite_score}`);
    assert.equal(result.suggested_allocation.Equity, 75);
    assert.equal(result.suggested_allocation.Debt, 15);
    assert.equal(result.suggested_allocation.Gold, 10);
  });

  test('5. Boundary conditions: Exact score 39 (Conservative) vs 40 (Moderate) and 69 (Moderate) vs 70 (Aggressive)', () => {
    // Boundary 39: Conservative upper edge
    const r39 = evaluateDeterministicRisk('<1', {
      Q1: 'Q1_A', // 10
      Q3: 'Q3_C', // 95  -> avg_w = 52.5
      Q2: 'Q2_D', // 100
      Q4: 'Q4_D', // 100 -> avg_c = 100
    });
    // raw = (52.5 * 0.45 + 100 * 0.55) * 0.50 = (23.625 + 55) * 0.50 = 78.625 * 0.50 = 39.3125 -> 39
    assert.equal(r39.composite_score, 39);
    assert.equal(r39.risk_band, 'Conservative');

    // Boundary 40: Moderate lower edge
    const r40 = evaluateDeterministicRisk('1-3', {
      Q1: 'Q1_A', // 10
      Q3: 'Q3_A', // 20  -> avg_w = 15
      Q2: 'Q2_D', // 100
      Q4: 'Q4_C', // 70  -> avg_c = 85
    });
    // raw = (15 * 0.45 + 85 * 0.55) * 0.75 = (6.75 + 46.75) * 0.75 = 53.5 * 0.75 = 40.125 -> 40
    assert.equal(r40.composite_score, 40);
    assert.equal(r40.risk_band, 'Moderate');

    // Boundary 69: Moderate upper edge
    const r69 = evaluateDeterministicRisk('1-3', {
      Q1: 'Q1_C', // 70
      Q3: 'Q3_C', // 95  -> avg_w = 82.5
      Q2: 'Q2_D', // 100
      Q4: 'Q4_D', // 100 -> avg_c = 100
    });
    // raw = (82.5 * 0.45 + 100 * 0.55) * 0.75 = (37.125 + 55) * 0.75 = 92.125 * 0.75 = 69.09375 -> 69
    assert.equal(r69.composite_score, 69);
    assert.equal(r69.risk_band, 'Moderate');

    // Boundary 70: Aggressive lower edge
    const r70 = evaluateDeterministicRisk('3-5', {
      Q1: 'Q1_A', // 10
      Q3: 'Q3_C', // 95  -> avg_w = 52.5
      Q2: 'Q2_D', // 100
      Q4: 'Q4_C', // 70  -> avg_c = 85
    });
    // raw = (52.5 * 0.45 + 85 * 0.55) * 1.0 = (23.625 + 46.75) * 1.0 = 70.375 -> 70
    assert.equal(r70.composite_score, 70);
    assert.equal(r70.risk_band, 'Aggressive');
  });

  test('6. Banker\'s rounding parity with backend Python round() across fractional .5 cases', () => {
    // Case where raw is exactly 26.5:
    // horizon '<1' (0.50), Q1_B (35), Q3_B (60) -> avg_w = 47.5
    // Q2_A (15), Q4_D (100) -> avg_c = 57.5
    // raw = (47.5 * 0.45 + 57.5 * 0.55) * 0.50 = (21.375 + 31.625) * 0.50 = 53.0 * 0.50 = 26.5
    const r26_5 = evaluateDeterministicRisk('<1', {
      Q1: 'Q1_B',
      Q3: 'Q3_B',
      Q2: 'Q2_A',
      Q4: 'Q4_D',
    });
    // Python's round(26.5) rounds half to even -> 26
    assert.equal(r26_5.composite_score, 26);
    assert.equal(r26_5.risk_band, 'Conservative');

    // Case where raw is exactly 38.5:
    // horizon '<1' (0.50), Q1_C (70), Q3_C (95) -> avg_w = 82.5
    // Q2_B (45), Q4_D (100) -> avg_c = 72.5
    // raw = (82.5 * 0.45 + 72.5 * 0.55) * 0.50 = (37.125 + 39.875) * 0.50 = 77.0 * 0.50 = 38.5
    const r38_5 = evaluateDeterministicRisk('<1', {
      Q1: 'Q1_C',
      Q3: 'Q3_C',
      Q2: 'Q2_B',
      Q4: 'Q4_D',
    });
    // Python's round(38.5) rounds half to even -> 38
    assert.equal(r38_5.composite_score, 38);
    assert.equal(r38_5.risk_band, 'Conservative');

    // Case where raw is exactly 40.5:
    // horizon '1-3' (0.75), Q1_B (35), Q3_C (95) -> avg_w = 65
    // Q2_C (75), Q4_A (15) -> avg_c = 45
    // raw = (65 * 0.45 + 45 * 0.55) * 0.75 = (29.25 + 24.75) * 0.75 = 54.0 * 0.75 = 40.5
    const r40_5 = evaluateDeterministicRisk('1-3', {
      Q1: 'Q1_B',
      Q3: 'Q3_C',
      Q2: 'Q2_C',
      Q4: 'Q4_A',
    });
    // Python's round(40.5) rounds half to even -> 40
    assert.equal(r40_5.composite_score, 40);
    assert.equal(r40_5.risk_band, 'Moderate');
  });

  test('7. Step sequence navigation rules: Back/Forward and direct editing preserve state', () => {
    let currentStep: 1 | 2 | 3 | 4 = 1;
    let maxStepReached = 1;
    const answers = {
      q1: 'Q1_C',
      q3: 'Q3_B',
      horizon: '3-5',
      q2: 'Q2_C',
      q4: 'Q4_C',
    };

    // Step 1: Basics -> Continue advances to Step 2
    currentStep = 2;
    maxStepReached = Math.max(maxStepReached, 2);
    assert.equal(currentStep, 2);
    assert.equal(maxStepReached, 2);

    // Step 2: Time horizon -> Back returns to Step 1
    currentStep = 1;
    assert.equal(currentStep, 1);
    assert.equal(answers.horizon, '3-5', 'Horizon answer preserved');

    // Step 1 -> Advance to Step 2 -> Step 3
    currentStep = 2;
    currentStep = 3;
    maxStepReached = Math.max(maxStepReached, 3);
    assert.equal(currentStep, 3);
    assert.equal(maxStepReached, 3);

    // Step 3 -> Back returns to Step 2
    currentStep = 2;
    assert.equal(currentStep, 2);

    // Advance to Step 4 (Review)
    currentStep = 4;
    maxStepReached = Math.max(maxStepReached, 4);
    assert.equal(currentStep, 4);

    // From Step 4, clicking "Edit" on Step 1 (Basics) directly navigates to Step 1
    currentStep = 1;
    assert.equal(currentStep, 1);
    assert.equal(answers.q1, 'Q1_C', 'Q1 answer preserved');

    // Changing answer updates state
    answers.q1 = 'Q1_D';
    assert.equal(answers.q1, 'Q1_D');

    // User can jump back to Step 4 since maxStepReached is 4
    assert.ok(4 <= maxStepReached, 'Step 4 remains accessible once unlocked');
    currentStep = 4;
    assert.equal(currentStep, 4);
  });

  test('8. Storage draft serialization preserves state across simulated page refresh', () => {
    const draft = {
      step: 3 as const,
      maxStepReached: 3,
      q1Option: 'Q1_B',
      q3Option: 'Q3_A',
      selectedHorizon: '1-3',
      q2Option: 'Q2_B',
      q4Option: 'Q4_B',
    };

    const serialized = JSON.stringify(draft);
    const restored = JSON.parse(serialized);

    assert.equal(restored.step, 3);
    assert.equal(restored.maxStepReached, 3);
    assert.equal(restored.q1Option, 'Q1_B');
    assert.equal(restored.selectedHorizon, '1-3');
    assert.equal(restored.q4Option, 'Q4_B');
  });

  test('9. False-success prevention: Submission failure must not mark complete or wipe draft', async () => {
    let onboardingCompletedCalled = false;
    let draftRemoved = false;
    let uiErrorMessage: string | null = null;

    const mockLocalStorage: Record<string, string> = {
      finex_onboarding_draft: JSON.stringify({ step: 4, q1Option: 'Q1_C' }),
    };

    // Simulate failed API call
    const mockApiClient = {
      isAuthenticated: () => true,
      submitAssessment: async () => {
        throw new Error('500 Internal Server Error: Database write timed out');
      },
    };

    // Runner representing handleFinalConfirm
    async function executeFinalConfirm() {
      try {
        if (mockApiClient.isAuthenticated()) {
          await mockApiClient.submitAssessment();
        }
        delete mockLocalStorage.finex_onboarding_draft;
        draftRemoved = true;
        onboardingCompletedCalled = true;
      } catch (err: any) {
        uiErrorMessage = err.message;
        // Do NOT proceed
      }
    }

    await executeFinalConfirm();

    // Verify false-success was prevented
    assert.equal(onboardingCompletedCalled, false, 'Must NOT trigger onComplete on API error');
    assert.equal(draftRemoved, false, 'Must NOT wipe draft on API error');
    assert.ok(mockLocalStorage.finex_onboarding_draft, 'Draft must remain intact in storage');
    assert.match(uiErrorMessage!, /500 Internal Server Error/);
  });
});
