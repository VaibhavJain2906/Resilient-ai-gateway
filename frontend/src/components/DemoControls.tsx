import React from 'react';
import { SimulationMode } from '../types';

interface DemoControlsProps {
  mode: SimulationMode;
  onChange: (mode: SimulationMode) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const DemoControls: React.FC<DemoControlsProps> = ({ mode, onChange, isOpen, onToggle }) => {
  const isKey1 = mode === 'key_1_429';
  const isWildcard = mode === 'wildcard_429';
  const isSimulating = isKey1 || isWildcard;

  const modeBadgeText = isKey1 ? 'key_1 → 429' : isWildcard ? 'All → 429' : 'Normal';

  return (
    <div className="composer-popover-anchor">
      <button
        type="button"
        className={`composer-pill-btn ${isOpen ? 'active' : ''} ${isSimulating ? (isWildcard ? 'danger' : 'warning') : ''}`}
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className="pill-icon">🧪</span>
        <span className="pill-label">Demo Failure Simulation</span>
        <span className={`sim-state-chip ${isSimulating ? (isWildcard ? 'chip-danger' : 'chip-warning') : 'chip-normal'}`}>
          Demo: {modeBadgeText}
        </span>
      </button>

      {isOpen && (
        <div className="composer-popover-panel demo-popover-panel">
          <div className="popover-panel-header">
            <span className="popover-title">Failure Simulation Header</span>
          </div>
          <p className="popover-desc">
            Simulate HTTP 429 errors via <code>X-Simulate-Failure</code> to demonstrate automatic failover and resilience.
          </p>

          <div className="sim-radio-stack">
            <label className={`sim-option-card ${mode === 'normal' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="simMode"
                value="normal"
                checked={mode === 'normal'}
                onChange={() => onChange('normal')}
              />
              <div className="sim-option-body">
                <span className="sim-option-title">Normal</span>
                <span className="sim-option-desc">Standard live inference &amp; cache flow</span>
              </div>
            </label>

            <label className={`sim-option-card warning-card ${mode === 'key_1_429' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="simMode"
                value="key_1_429"
                checked={mode === 'key_1_429'}
                onChange={() => onChange('key_1_429')}
              />
              <div className="sim-option-body">
                <span className="sim-option-title">Simulate key_1 (429)</span>
                <span className="sim-option-desc">Triggers seamless auto-failover to key_2</span>
              </div>
            </label>

            <label className={`sim-option-card danger-card ${mode === 'wildcard_429' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="simMode"
                value="wildcard_429"
                checked={mode === 'wildcard_429'}
                onChange={() => onChange('wildcard_429')}
              />
              <div className="sim-option-body">
                <span className="sim-option-title">Simulate All Keys (429)</span>
                <span className="sim-option-desc">Exhausts pool to verify HTTP 503 error contract</span>
              </div>
            </label>
          </div>
        </div>
      )}
    </div>
  );
};
