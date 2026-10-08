import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './main';
import { DEFAULT_SETTINGS } from './mission';

const names = ['Decision Tree', 'Random Forest', 'AdaBoost', 'Voting Ensemble'];
function payload(settings = DEFAULT_SETTINGS) {
  return {
    settings,
    dataset: { source: 'sample', synthetic: true, total: 40, benign: 30, attacks: 10, train_rows: 20, test_rows: 20, test_attacks: 10, test_benign: 10, sample: [{ Label: 'BENIGN', 'Flow Duration': 12 }] },
    models: names.map((name, index) => {
      const caught = [8, 9, 7, 9][index], false_alarms = [1, 2, 3, 1][index], missed = 10 - caught;
      return { name, caught, missed, false_alarms, benign_correct: 10 - false_alarms, recall: caught / 10, precision: caught / (caught + false_alarms), accuracy: (caught + 10 - false_alarms) / 20, f1: .8, train_seconds: .1,
        mistakes: { missed_attacks: { total: missed, by_family: { DDoS: missed }, examples: [{ Connection: 42, 'Known label': 'DDoS', 'Flow Duration': 500 }] }, false_alarms: { total: false_alarms, by_family: { BENIGN: false_alarms }, examples: [{ Connection: 23, 'Known label': 'BENIGN', 'Flow Duration': 700 }] } } };
    }),
  };
}

beforeEach(() => {
  const storage = new Map();
  vi.stubGlobal('localStorage', {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    clear: () => storage.clear(),
  });
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  vi.stubGlobal('fetch', vi.fn(async (url, options) => {
    if (url === '/api/datasets') return { ok: true, json: async () => ({ sources: [{ id: 'sample', name: 'Demo traffic (synthetic)' }] }) };
    return { ok: true, json: async () => payload(JSON.parse(options.body)) };
  }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('Monster adventure', () => {
  it('completes all missions, accepts a tied winner, handles wrong answers, and turns animation off', async () => {
    const user = userEvent.setup();
    render(<App/>);
    await screen.findByRole('button', { name: 'Check my guess' });
    await user.click(screen.getByRole('button', { name: /Voting Ensemble/ }));
    await user.click(screen.getByRole('button', { name: 'Check my guess' }));
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('1');
    expect(screen.getByText(/It's a tie/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Compare detectors' }));
    await user.click(screen.getAllByRole('button', { name: 'Choose this detector' })[0]);
    await user.click(screen.getByRole('button', { name: 'Find the mistakes' }));
    await user.click(screen.getByRole('button', { name: 'A false alarm' }));
    await user.click(screen.getByRole('button', { name: 'Check my answer' }));
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('2');
    expect(screen.getByText(/Try again! A false alarm/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'A missed attack' }));
    await user.click(screen.getByRole('button', { name: 'Check my answer' }));
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('3');
    expect(screen.getByText('You think like a detector.')).toBeTruthy();
    await user.click(screen.getByRole('checkbox', { name: /Animate Monster/ }));
    expect(screen.queryByAltText('Monster talks, blinks, and munches its cookie')).toBeNull();
    expect(localStorage.getItem('threatvote-motion')).toBe('off');
    await user.click(screen.getByRole('button', { name: 'Play again' }));
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('0');
    expect(screen.getByRole('button', { name: 'Check my guess' })).toBeTruthy();
  });

  it('keeps existing results on training failure and resets progress after successful retraining', async () => {
    const user = userEvent.setup();
    render(<App/>);
    await screen.findByRole('button', { name: 'Check my guess' });
    await user.click(screen.getByRole('button', { name: 'Check my guess' }));
    await user.click(screen.getByText('Lab settings'));
    fireEvent.change(screen.getByRole('slider', { name: /^Tree depth/ }), { target: { value: '10' } });
    expect(screen.getByText(/You have unapplied settings/)).toBeTruthy();
    fetch.mockImplementationOnce(async () => ({ ok: false, json: async () => ({ error: 'Dataset cannot be split.' }) }));
    await user.click(screen.getByRole('button', { name: 'Apply & retrain' }));
    await screen.findByRole('alert');
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('1');
    expect(screen.getByRole('button', { name: 'Compare detectors' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('0'));
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.queryByText(/You have unapplied settings/)).toBeNull();
  });
});
