export const DEFAULT_SETTINGS = {
  source: 'sample', max_rows: 20000, test_size: 0.25, seed: 42,
  tree_depth: 8, n_trees: 100, boost_iters: 100, learning_rate: 0.5,
};

export const MODEL_INFO = {
  'Decision Tree': { icon: 'tree', tagline: 'The rule maker', description: 'Learns a series of rules about each connection.' },
  'Random Forest': { icon: 'forest', tagline: 'The team player', description: 'Combines many trees to make a prediction.' },
  AdaBoost: { icon: 'bolt', tagline: 'The fast learner', description: 'Learns in rounds, focusing on earlier mistakes.' },
  'Voting Ensemble': { icon: 'team', tagline: 'The group decision', description: 'Averages the attack probabilities of all three detectors.' },
};

export function winners(models) {
  const most = Math.max(...models.map(model => model.caught));
  return models.filter(model => model.caught === most).map(model => model.name);
}

export function comparison(first, second) {
  const describe = (difference, label) => difference === 0
    ? `the same number of ${label}`
    : `${Math.abs(difference).toLocaleString()} ${difference > 0 ? 'more' : 'fewer'} ${label}`;
  return `Compared with ${first.name}, ${second.name} misses ${describe(second.missed - first.missed, 'attacks')} and raises ${describe(second.false_alarms - first.false_alarms, 'false alarms')}.`;
}

export function completeMission(completed, mission) {
  return completed.includes(mission) ? completed : [...completed, mission];
}

export function sameSettings(first, second) {
  return Object.keys(DEFAULT_SETTINGS).every(key => first[key] === second[key]);
}
