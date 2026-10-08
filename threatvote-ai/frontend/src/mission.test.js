import test from 'node:test';
import assert from 'node:assert/strict';
import { winners, comparison, completeMission, sameSettings, DEFAULT_SETTINGS } from './mission.js';

test('guessing accepts every detector tied for most attacks caught', () => {
  assert.deepEqual(winners([{ name: 'Tree', caught: 12 }, { name: 'Forest', caught: 12 }, { name: 'Boost', caught: 10 }]), ['Tree', 'Forest']);
});
test('comparisons describe tradeoffs and ties without calling a tie fewer', () => {
  const a = { name: 'Tree', missed: 5, false_alarms: 3 };
  assert.equal(comparison(a, { name: 'Forest', missed: 2, false_alarms: 7 }), 'Compared with Tree, Forest misses 3 fewer attacks and raises 4 more false alarms.');
  assert.equal(comparison(a, { ...a, name: 'Vote' }), 'Compared with Tree, Vote misses the same number of attacks and raises the same number of false alarms.');
});
test('mission completion is independent of navigation order and cannot count twice', () => {
  const completed = completeMission(completeMission([], 2), 2);
  assert.deepEqual(completed, [2]);
  assert.deepEqual(completeMission(completeMission(completed, 0), 1), [2, 0, 1]);
});
test('unapplied settings remain distinct from the settings that produced displayed scores', () => {
  assert.equal(sameSettings(DEFAULT_SETTINGS, { ...DEFAULT_SETTINGS }), true);
  assert.equal(sameSettings(DEFAULT_SETTINGS, { ...DEFAULT_SETTINGS, source: 'real.csv' }), false);
  assert.equal(sameSettings(DEFAULT_SETTINGS, { ...DEFAULT_SETTINGS, tree_depth: 10 }), false);
});
