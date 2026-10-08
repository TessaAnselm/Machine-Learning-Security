import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { DEFAULT_SETTINGS, MODEL_INFO, comparison, completeMission, sameSettings, winners } from './mission';
import './styles.css';

const MISSIONS = [
  { title: 'Meet the traffic', short: 'Guess the winner', icon: 'radar', message: "Hi, I'm Monster! These detectors learned from examples of normal traffic and attacks. Which one do you think will catch the most attacks? Pick your champion below." },
  { title: 'Compare detectors', short: 'Choose your champion', icon: 'compare', message: 'Now for the tricky part. A detector can catch more attacks but also raise more false alarms. Compare two detectors, then tell me which you would trust.' },
  { title: 'Find the mistakes', short: 'Think like a detective', icon: 'search', message: "Even clever detectors make mistakes. Let's look at the attacks they missed and the normal traffic they flagged. Then help me solve a quick question!" },
];
const format = value => Number(value).toLocaleString();
const percent = value => `${(value * 100).toFixed(1)}%`;

function Icon({ name, size = 22 }) {
  const paths = {
    radar: <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12 19 5M12 3v2M3 12h2"/></>,
    compare: <><path d="M6 4v16M18 4v16M3 8h6M15 16h6"/><circle cx="6" cy="8" r="2"/><circle cx="18" cy="16" r="2"/></>,
    search: <><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/></>,
    tree: <><path d="m12 3 7 9H5l7-9Zm0 9v9M8 21h8"/></>,
    forest: <><path d="m8 3 5 8H3l5-8Zm9 5 4 7h-8l4-7ZM8 11v10M17 15v6"/></>,
    bolt: <path d="m13 2-9 12h7l-1 8 10-13h-7l0-7Z"/>,
    team: <><circle cx="12" cy="7" r="3"/><path d="M6 21v-3a6 6 0 0 1 12 0v3M3 8a3 3 0 0 0 0 6m18-6a3 3 0 0 1 0 6M2 21v-2M22 21v-2"/></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>,
    check: <path d="m5 12 4 4L19 6"/>,
    cookie: <><path d="M20 12a8 8 0 1 1-8-8 4 4 0 0 0 4 4 4 4 0 0 0 4 4Z"/><path d="M8 10h.01M12 15h.01M7 16h.01"/></>,
    settings: <><path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="8" cy="18" r="2"/></>,
    shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.radar}</svg>;
}

function Monster({ motion, celebrate }) {
  return <div className={`monster-stage ${celebrate ? 'celebrate' : ''}`}>
    <div className="monster-glow"/>
    {motion && <img className="monster-animated" src="/mascot/monster-talking.gif" alt="Monster talks, blinks, and munches its cookie"/>}
    <img className={`monster-still ${motion ? 'motion-enabled' : ''}`} src="/mascot/monster-still.png" alt="Monster, your pink cookie-loving guide"/>
    <span className="monster-name"><span className="status-dot"/> YOUR GUIDE · MONSTER</span>
  </div>;
}

function Guide({ mission, motion, celebrate, message }) {
  return <section className="guide-card" aria-label="Monster's guide">
    <Monster motion={motion} celebrate={celebrate}/>
    <div className="guide-message">
      <span className="eyebrow">A LITTLE HELP FROM MONSTER</span>
      <h2>{mission === 0 ? "Let's catch some attacks." : mission === 1 ? 'More alerts ≠ a better detector.' : 'Mistakes tell a story.'}</h2>
      <p aria-live="polite">{message || MISSIONS[mission].message}</p>
      <div className="guide-footnote"><Icon name="cookie" size={16}/> Learning is better with a cookie.</div>
    </div>
  </section>;
}

function DataTable({ rows, empty = 'No connections to show.' }) {
  if (!rows?.length) return <div className="empty-state"><Icon name="shield"/>{empty}</div>;
  const columns = Object.keys(rows[0]);
  return <div className="table-scroll" tabIndex="0" aria-label="Scrollable connection data">
    <table><thead><tr>{columns.map(name => <th key={name}>{name}</th>)}</tr></thead>
      <tbody>{rows.map((row, index) => <tr key={index}>{columns.map(name => <td key={name}>{typeof row[name] === 'number' ? row[name].toLocaleString(undefined, { maximumFractionDigits: 2 }) : row[name]}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}

function Matrix({ model }) {
  const cells = [
    ['Normal correctly classified', model.benign_correct, 'good'],
    ['False alarms', model.false_alarms, 'bad'],
    ['Missed attacks', model.missed, 'bad'],
    ['Attacks caught', model.caught, 'good'],
  ];
  return <div className="matrix-wrap">
    <span className="muted small">PREDICTED →</span>
    <div className="matrix"><div/><span>Normal</span><span>Attack</span>
      <span className="matrix-axis">Actually normal</span>{cells.slice(0, 2).map(([label, value, style]) => <div className={`matrix-cell ${style}`} key={label}><b>{format(value)}</b><span>{label}</span></div>)}
      <span className="matrix-axis">Actually attack</span>{cells.slice(2).map(([label, value, style]) => <div className={`matrix-cell ${style}`} key={label}><b>{format(value)}</b><span>{label}</span></div>)}
    </div>
  </div>;
}

function NextButton({ children, onClick }) {
  return <button className="button primary" onClick={onClick}>{children}<Icon name="arrow" size={18}/></button>;
}

function MeetTraffic({ result, onComplete, onNext, guess, setGuess, revealed, setRevealed, onMessage }) {
  const champions = winners(result.models);
  const selected = result.models.find(model => model.name === guess);
  const checkGuess = () => {
    setRevealed(true);
    onComplete(0);
    onMessage(champions.includes(guess)
      ? `Good instinct! ${guess} is one of the detectors that caught the most attacks. But catching attacks is only half the story. Let's look at false alarms next!`
      : `Nice experiment! ${guess} caught ${format(selected.caught)} attacks. ${champions.join(' and ')} caught the most this time. Every guess helps us learn.`);
  };
  return <>
    <section className="section-heading"><div><span className="eyebrow">MISSION 01 / YOUR FIRST EXPERIMENT</span><h2>Pick your champion.</h2><p>You don't need to know the algorithms. Take a guess, then we'll test it.</p></div><span className="step-tag">1 minute</span></section>
    <div className="detector-grid">
      {result.models.map(model => <button key={model.name} className={`detector-card ${guess === model.name ? 'selected' : ''}`} aria-pressed={guess === model.name} disabled={revealed} onClick={() => setGuess(model.name)}>
        <span className="detector-top"><span className="model-icon"><Icon name={MODEL_INFO[model.name].icon} size={27}/></span><span className="choice-circle">{guess === model.name && <Icon name="check" size={14}/>}</span></span>
        <span className="model-tagline">{MODEL_INFO[model.name].tagline}</span>
        <h3>{model.name}</h3><p>{MODEL_INFO[model.name].description}</p>
        {revealed && <span className="revealed-count"><b>{format(model.caught)}</b> attacks caught{champions.includes(model.name) && <span className="winner-pill">Most caught</span>}</span>}
      </button>)}
    </div>
    {!revealed ? <div className="action-row"><NextButton onClick={checkGuess}>Check my guess</NextButton><span className="muted small">No wrong guesses. We're here to explore.</span></div>
      : <div className="result-banner" role="status"><div><span className="eyebrow">RESULTS ARE IN</span><h3>{guess} caught {format(selected.caught)} of {format(result.dataset.test_attacks)} attacks.</h3><p>{champions.length > 1 ? `It's a tie: ${champions.join(', ')} caught the most.` : `${champions[0]} caught the most attacks in this test.`} Does that make it the best choice?</p></div><NextButton onClick={onNext}>Compare detectors</NextButton></div>}
    <section className="panel traffic-panel"><div className="panel-heading"><div><h3>What are we actually looking at?</h3><p>Each row is one network connection. Its known label tells us the answer.</p></div><Icon name="radar"/></div>
      <div className="traffic-totals"><div><b>{format(result.dataset.total)}</b><span>Total connections</span></div><div><b>{format(result.dataset.benign)}</b><span><i className="legend-dot normal"/>Normal traffic</span></div><div><b>{format(result.dataset.attacks)}</b><span><i className="legend-dot attack"/>Attack traffic</span></div></div>
      <div className="traffic-bar" aria-label={`${result.dataset.benign} normal and ${result.dataset.attacks} attack connections`}><span style={{ width: `${result.dataset.benign / result.dataset.total * 100}%` }}/></div>
      <div className="split-note"><Icon name="shield" size={18}/><span><b>{format(result.dataset.train_rows)} connections for learning.</b> {format(result.dataset.test_rows)} different connections for testing. All detectors get the same split.</span></div>
      <details><summary>Peek at the traffic data</summary><DataTable rows={result.dataset.sample}/></details>
    </section>
  </>;
}

function ModelStats({ model, total, selected, onChoose, disabled }) {
  return <article className={`panel comparison-card ${selected ? 'chosen' : ''}`}>
    <div className="comparison-title"><span className="model-icon"><Icon name={MODEL_INFO[model.name].icon}/></span><div><span className="model-tagline">{MODEL_INFO[model.name].tagline}</span><h3>{model.name}</h3></div></div>
    <div className="caught-stat"><span>Attacks caught</span><b>{format(model.caught)}<small> / {format(total)}</small></b><div className="score-track"><span style={{ width: `${model.recall * 100}%` }}/></div></div>
    <div className="mistake-pair"><div><span>Missed attacks</span><b>{format(model.missed)}</b><small>Attacks that slipped through</small></div><div><span>False alarms</span><b>{format(model.false_alarms)}</b><small>Normal traffic flagged</small></div></div>
    <button className={`button ${selected ? 'primary' : 'secondary'}`} disabled={disabled} onClick={onChoose}>{selected ? <><Icon name="check" size={17}/>My chosen detector</> : 'Choose this detector'}</button>
  </article>;
}

function Scores({ models }) {
  const metrics = [
    ['accuracy', 'Accuracy', 'All predictions that are correct'],
    ['precision', 'Precision', 'Attack alerts that are correct'],
    ['recall', 'Recall', 'Actual attacks caught'],
    ['f1', 'F1 score', 'Balance of precision and recall'],
  ];
  return <details className="panel details-panel"><summary>Go deeper: scores & confusion matrices</summary><p>Higher scores are better. When most traffic is normal, accuracy alone can hide missed attacks.</p>
    <div className="score-grid">{metrics.map(([key, title, description]) => <section key={key}><h4>{title}</h4><p className="small muted">{description}</p>{models.map(model => <div className="score-row" key={model.name}><div><span>{model.name}</span><b>{percent(model[key])}</b></div><div className="score-track"><span style={{ width: `${model[key] * 100}%` }}/></div></div>)}</section>)}</div>
    <h3>Prediction breakdown</h3><p className="muted">Rows show the known answer; columns show the detector's prediction.</p>
    <div className="matrix-grid">{models.map(model => <section key={model.name}><h4>{model.name}</h4><Matrix model={model}/><p className="small muted">Trained in {model.train_seconds.toFixed(2)} seconds</p></section>)}</div>
  </details>;
}

function CompareDetectors({ result, favorite, choose, onNext, first, setFirst, second, setSecond }) {
  const a = result.models.find(model => model.name === first);
  const b = result.models.find(model => model.name === second);
  const distinct = first !== second;
  return <>
    <section className="section-heading"><div><span className="eyebrow">MISSION 02 / MAKE THE TRADEOFF</span><h2>Which would you trust?</h2><p>Look for fewer missed attacks and fewer false alarms. Sometimes you have to choose.</p></div><span className="step-tag">2 minutes</span></section>
    <div className="comparison-selectors"><label>First detector<select value={first} onChange={e => setFirst(e.target.value)}>{result.models.map(m => <option key={m.name}>{m.name}</option>)}</select></label><label>Second detector<select value={second} onChange={e => setSecond(e.target.value)}>{result.models.map(m => <option key={m.name}>{m.name}</option>)}</select></label></div>
    {!distinct && <div className="notice">Choose two different detectors to compare their results.</div>}
    <div className="comparison-grid"><ModelStats model={a} total={result.dataset.test_attacks} selected={favorite === first} disabled={!distinct} onChoose={() => choose(first)}/><ModelStats model={b} total={result.dataset.test_attacks} selected={favorite === second} disabled={!distinct} onChoose={() => choose(second)}/></div>
    {distinct && <div className="comparison-note"><Icon name="compare"/><p>{comparison(a, b)}</p></div>}
    {favorite && <div className="result-banner"><div><span className="eyebrow">YOUR CHAMPION</span><h3>{favorite}</h3><p>No single right answer. What matters is understanding your choice.</p></div><NextButton onClick={onNext}>Find the mistakes</NextButton></div>}
    <Scores models={result.models}/>
  </>;
}

function InspectMistakes({ result, modelName, setModelName, answer, setAnswer, checked, onCheck, completed, onRestart }) {
  const [kind, setKind] = useState('missed_attacks');
  const model = result.models.find(m => m.name === modelName);
  const mistakes = model.mistakes[kind];
  return <>
    <section className="section-heading"><div><span className="eyebrow">MISSION 03 / FOLLOW THE CLUES</span><h2>What slipped through?</h2><p>Inspect real predictions from this test, then answer Monster's question.</p></div><span className="step-tag">2 minutes</span></section>
    <section className="panel"><div className="panel-heading"><h3>Investigate a detector</h3><label className="sr-only" htmlFor="inspect-model">Detector to inspect</label><select id="inspect-model" value={modelName} onChange={e => setModelName(e.target.value)}>{result.models.map(m => <option key={m.name}>{m.name}</option>)}</select></div>
      <div className="mistake-switch"><button className={kind === 'missed_attacks' ? 'active' : ''} aria-pressed={kind === 'missed_attacks'} onClick={() => setKind('missed_attacks')}>Missed attacks <b>{format(model.missed)}</b></button><button className={kind === 'false_alarms' ? 'active' : ''} aria-pressed={kind === 'false_alarms'} onClick={() => setKind('false_alarms')}>False alarms <b>{format(model.false_alarms)}</b></button></div>
      <p className="muted">{kind === 'missed_attacks' ? 'These were attacks, but the detector called them normal.' : 'These were normal connections, but the detector called them attacks.'}</p>
      {kind === 'missed_attacks' && mistakes.total > 0 && <div className="family-chips">{Object.entries(mistakes.by_family).map(([name, count]) => <span key={name}>{name}<b>{format(count)}</b></span>)}</div>}
      <DataTable rows={mistakes.examples} empty={`No ${kind === 'missed_attacks' ? 'missed attacks' : 'false alarms'} for this detector on this test split.`}/>
      {mistakes.total > 0 && <p className="small muted">Showing {mistakes.examples.length} of {format(mistakes.total)} mistakes (up to 100 examples). Attack-family names are known labels, not predictions.</p>}
    </section>
    <section className="panel quiz-panel"><span className="eyebrow">MONSTER'S QUICK CHECK</span><h3>A detector says “normal,” but the connection is actually an attack.</h3><p>What happened?</p><div className="quiz-options">{['A false alarm', 'A missed attack'].map(option => <button key={option} className={`quiz-choice ${answer === option ? 'selected' : ''}`} aria-pressed={answer === option} onClick={() => { setAnswer(option); }}>{option}<span className="choice-circle">{answer === option && <Icon name="check" size={14}/>}</span></button>)}</div>
      <button className="button primary" onClick={onCheck} disabled={!answer}>Check my answer<Icon name="arrow" size={18}/></button>
      {checked && <div className={`quiz-feedback ${answer === 'A missed attack' ? 'correct' : ''}`} role="status">{answer === 'A missed attack' ? 'Exactly! The attack slipped through. This is also called a false negative.' : 'Try again! A false alarm flags normal traffic as an attack. Here, an actual attack was missed.'}</div>}
    </section>
    {completed.length === 3 && <section className="completion-panel" role="status"><span className="completion-icon"><Icon name="cookie" size={36}/></span><span className="eyebrow">COOKIE EARNED · ALL MISSIONS COMPLETE</span><h2>You think like a detector.</h2><p>You guessed, compared the tradeoffs, and identified a missed attack.<br/>Try changing one setting to see what happens next.</p><button className="button primary" onClick={onRestart}>Play again<Icon name="arrow" size={18}/></button></section>}
  </>;
}

function SettingsPanel({ settings, setSettings, sources, training, onTrain, dirty }) {
  const update = (key, value) => setSettings(s => ({ ...s, [key]: value }));
  const sliders = [
    ['tree_depth', 'Tree depth', 2, 20, 1, 'How many levels of rules the Decision Tree can learn.'],
    ['n_trees', 'Forest trees', 10, 300, 10, 'More trees take longer to train.'],
    ['boost_iters', 'Boosting rounds', 10, 300, 10, 'Maximum learning rounds for AdaBoost.'],
    ['learning_rate', 'Learning rate', 0.01, 2, 0.01, 'How much each boosting round contributes.'],
    ['test_size', 'Test set share', 0.1, 0.4, 0.05, 'Rows reserved for testing, never used for learning.'],
  ];
  return <details className="settings-panel"><summary><Icon name="settings" size={18}/>Lab settings<span>+</span></summary><div className="settings-content"><p className="small muted">Change one setting at a time. Apply to retrain and start a new adventure.</p><fieldset disabled={training}><label>Traffic source<select value={settings.source} onChange={e => update('source', e.target.value)}>{sources.map(s => <option value={s.id} key={s.id}>{s.name}</option>)}</select></label>
    {settings.source !== 'sample' && <label>Maximum rows<input type="number" min="2000" max="100000" step="2000" value={settings.max_rows} onChange={e => update('max_rows', Number(e.target.value))}/></label>}
    {sliders.map(([key, label, min, max, step, hint]) => <label className="slider-label" key={key} title={hint}><span>{label}<b>{key === 'test_size' ? `${Math.round(settings[key] * 100)}%` : settings[key]}</b></span><input type="range" min={min} max={max} step={step} value={settings[key]} onChange={e => update(key, Number(e.target.value))}/><small>{hint}</small></label>)}
    <label>Random seed<input type="number" min="0" max="4294967295" step="1" value={settings.seed} onChange={e => update('seed', Number(e.target.value))}/><small>Keep fixed to repeat the same experiment.</small></label>
    <button className="button primary" disabled={!dirty || training} onClick={onTrain}>{training ? 'Training detectors…' : 'Apply & retrain'}</button></fieldset></div></details>;
}

export function App() {
  const [mission, setMission] = useState(0);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [sources, setSources] = useState([{ id: 'sample', name: 'Demo traffic (synthetic)' }]);
  const [result, setResult] = useState(null);
  const [training, setTraining] = useState(true);
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState([]);
  const [guess, setGuess] = useState('Decision Tree');
  const [revealed, setRevealed] = useState(false);
  const [favorite, setFavorite] = useState('');
  const [first, setFirst] = useState('Decision Tree');
  const [second, setSecond] = useState('Voting Ensemble');
  const [inspectModel, setInspectModel] = useState('Decision Tree');
  const [answer, setAnswer] = useState('');
  const [checked, setChecked] = useState(false);
  const [message, setMessage] = useState('');
  const [celebrate, setCelebrate] = useState(false);
  const [motion, setMotion] = useState(() => {
    try { return localStorage.getItem('threatvote-motion') !== 'off'; } catch { return true; }
  });
  const controller = useRef(null);
  const heading = useRef(null);
  const firstRender = useRef(true);

  const restart = () => { setCompleted([]); setRevealed(false); setFavorite(''); setAnswer(''); setChecked(false); setMessage(''); setCelebrate(false); setMission(0); };
  const train = async chosenSettings => {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setTraining(true); setError('');
    try {
      const response = await fetch('/api/train', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(chosenSettings), signal: request.signal });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Training failed. Please try again.');
      if (request.signal.aborted) return;
      setResult(payload); restart();
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message === 'Failed to fetch' ? 'Cannot reach the Python lab. Start it with python server.py, then try again.' : e.message);
    } finally { if (!request.signal.aborted) setTraining(false); }
  };
  useEffect(() => {
    const datasetsRequest = new AbortController();
    fetch('/api/datasets', { signal: datasetsRequest.signal }).then(r => r.ok ? r.json() : Promise.reject()).then(p => setSources(p.sources)).catch(() => {});
    train(DEFAULT_SETTINGS);
    return () => { controller.current?.abort(); datasetsRequest.abort(); };
  }, []);
  useEffect(() => { try { localStorage.setItem('threatvote-motion', motion ? 'on' : 'off'); } catch {} }, [motion]);
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    heading.current?.focus();
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [mission]);
  useEffect(() => { if (celebrate) { const timer = setTimeout(() => setCelebrate(false), 2400); return () => clearTimeout(timer); } }, [celebrate]);

  const markComplete = index => { setCompleted(current => completeMission(current, index)); setCelebrate(true); };
  const navigate = index => { setMission(index); setMessage(''); setCelebrate(false); };
  const choose = name => { setFavorite(name); setInspectModel(name); markComplete(1); setMessage(`You chose ${name}! There's no single right choice. What matters is understanding missed attacks and false alarms. Ready to investigate its mistakes?`); };
  const checkAnswer = () => { setChecked(true); if (answer === 'A missed attack') { markComplete(2); setMessage('Exactly! A missed attack slips through the detector. You now know the difference between missing an attack and raising a false alarm. Cookie high-five!'); } };
  const dirty = !result || !sameSettings(settings, result.settings);

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to mission</a>
    <aside className="sidebar">
      <a className="brand" href="#main" onClick={() => navigate(0)}><span className="brand-mark"><Icon name="shield" size={26}/></span><span>ThreatVote<span className="brand-ai"> AI</span><small>MONSTER'S DETECTION LAB</small></span></a>
      <div className="sidebar-intro"><span className="eyebrow">YOUR ADVENTURE</span><h2>Small missions.<br/>Big discoveries.</h2><p>Learn how AI spots attacks,<br/>one cookie at a time.</p></div>
      <nav aria-label="Missions">{MISSIONS.map((item, index) => <button key={item.title} className={`mission-link ${mission === index ? 'active' : ''}`} aria-current={mission === index ? 'step' : undefined} onClick={() => navigate(index)}><span className={`mission-number ${completed.includes(index) ? 'done' : ''}`}>{completed.includes(index) ? <Icon name="check" size={17}/> : `0${index + 1}`}</span><span><b>{item.title}</b><small>{item.short}</small></span>{mission === index && <span className="nav-arrow">›</span>}</button>)}</nav>
      <div className="progress-card"><div><span>Your progress</span><b>{completed.length}/3</b></div><div className="progress-track" role="progressbar" aria-label="Missions complete" aria-valuenow={completed.length} aria-valuemin={0} aria-valuemax={3}>{MISSIONS.map((_, index) => <span className={completed.includes(index) ? 'filled' : ''} key={index}/>)}</div><p>{completed.length === 3 ? 'All done. Cookie earned!' : 'Finish all three to earn your cookie.'}</p></div>
      <SettingsPanel settings={settings} setSettings={setSettings} sources={sources} training={training} dirty={dirty} onTrain={() => train(settings)}/>
      <label className="motion-toggle"><span><Icon name="cookie" size={17}/>Animate Monster</span><input type="checkbox" checked={motion} onChange={e => setMotion(e.target.checked)}/></label>
      <div className="sidebar-footer">Built for curious humans.<br/>Powered by real Python models.</div>
    </aside>
    <main id="main" className="main-content">
      <header className="page-header"><div><span className="eyebrow">THREAT DETECTION, MADE HUMAN</span><h1 ref={heading} tabIndex="-1">{MISSIONS[mission].title}<span className="title-dot">.</span></h1></div><span className={`dataset-badge ${result?.dataset.synthetic !== false ? '' : 'real'}`}><span className="status-dot"/>{result?.dataset.synthetic === false ? 'CSV traffic data' : 'Synthetic demo data'}</span></header>
      <Guide mission={mission} motion={motion} celebrate={motion && celebrate} message={message}/>
      <div className="dataset-note">{result?.dataset.synthetic === false ? `Results describe ${result.dataset.source} and this test split. They do not establish performance on live traffic.` : 'This adventure uses made-up traffic for learning. Its scores are not evidence of real-world detection performance.'}</div>
      {error && <div className="error-panel" role="alert"><h3>We couldn't run that experiment.</h3><p>{error}</p><button className="button secondary" onClick={() => train(settings)} disabled={training}>Try again</button>{result && <p className="small">The results below are from the last successful experiment.</p>}</div>}
      {training ? <section className="loading-panel" role="status"><span className="loading-spinner"/><h2>Monster is getting the lab ready…</h2><p>Learning from traffic, training four detectors, and checking their predictions.<br/>This can take a little longer with larger datasets.</p></section> : result && <>
        {dirty && <div className="notice">You have unapplied settings. These results use the last successful experiment. Click “Apply & retrain” in Lab settings to run your changes.</div>}
        {mission === 0 && <MeetTraffic result={result} guess={guess} setGuess={setGuess} revealed={revealed} setRevealed={setRevealed} onComplete={markComplete} onMessage={setMessage} onNext={() => navigate(1)}/>}
        {mission === 1 && <CompareDetectors result={result} favorite={favorite} choose={choose} onNext={() => navigate(2)} first={first} setFirst={setFirst} second={second} setSecond={setSecond}/>}
        {mission === 2 && <InspectMistakes result={result} modelName={inspectModel} setModelName={setInspectModel} answer={answer} setAnswer={value => { setAnswer(value); setChecked(false); }} checked={checked} onCheck={checkAnswer} completed={completed} onRestart={restart}/>}
      </>}
      <footer className="page-footer"><span><Icon name="shield" size={16}/>ThreatVote AI</span><span>A little less jargon. A lot more discovery.</span></footer>
    </main>
  </div>;
}

const root = document.getElementById('root');
if (root) createRoot(root).render(<App/>);
