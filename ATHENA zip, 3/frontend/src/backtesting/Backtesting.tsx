import { useEffect, useMemo, useRef, useState, type ChangeEvent, type PointerEvent, type WheelEvent } from 'react';
import { ArrowDownRight, ArrowUpRight, Circle, Crosshair, Eraser, Maximize2, Minus, MoveHorizontal, RefreshCw, RotateCcw, Square, Triangle, TrendingUp } from 'lucide-react';
import { authService, type AccountProfile, type BacktestingMarketData, type HistoricalDataset, type ReplayMetrics, type ReplaySession, type SavedBacktestingDrawing } from '../authentication/services/authService';

const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];
const CHART_WIDTH = 1400;
const CHART_HEIGHT = 760;
const PADDING = { top: 18, right: 92, bottom: 34, left: 14 };
type Candle = NonNullable<BacktestingMarketData['candles']>[number];
type Tool = 'crosshair' | 'trendline' | 'horizontal' | 'vertical' | 'ray' | 'rectangle' | 'triangle' | 'ellipse' | 'long_position' | 'short_position';
type Point = { time: number; price: number };
type Drawing = { id: string; type: SavedBacktestingDrawing['type']; start: Point; end?: Point };

function formatPrice(value?: number) {
  if (value === undefined || !Number.isFinite(value)) return '--';
  return value >= 100 ? value.toFixed(2) : value.toFixed(5);
}

function Chart({ candles, symbol, timeframe, livePrice, tool, drawings, onDrawing }: { candles: Candle[]; symbol?: string; timeframe?: string; livePrice?: number; tool: Tool; drawings: Drawing[]; onDrawing: (drawing: Drawing) => void }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [visibleCount, setVisibleCount] = useState(120);
  const [priceZoom, setPriceZoom] = useState(1);
  const [offset, setOffset] = useState(0);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [pendingStart, setPendingStart] = useState<Point | null>(null);
  const [hovered, setHovered] = useState<Candle | null>(null);
  const chart = useMemo(() => {
    const count = Math.min(visibleCount, candles.length);
    const maxOffset = Math.max(0, candles.length - count);
    const boundedOffset = Math.min(offset, maxOffset);
    const start = Math.max(0, candles.length - count - boundedOffset);
    const display = candles.slice(start, start + count);
    const minimum = Math.min(...display.map((candle) => candle.low));
    const maximum = Math.max(...display.map((candle) => candle.high));
    const pricePadding = (maximum - minimum || Math.abs(maximum) * 0.01 || 1) * 0.06;
    const center = (maximum + minimum) / 2;
    const range = (maximum - minimum + pricePadding * 2) / priceZoom;
    const low = center - range / 2;
    const high = center + range / 2;
    const plotWidth = CHART_WIDTH - PADDING.left - PADDING.right;
    const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
    const step = plotWidth / display.length;
    return { display, low, high, step, bodyWidth: Math.max(1, Math.min(12, step * 0.65)), plotHeight, x: (index: number) => PADDING.left + index * step + step / 2, y: (price: number) => PADDING.top + ((high - price) / (high - low)) * plotHeight };
  }, [candles, offset, priceZoom, visibleCount]);
  const priceTicks = useMemo(() => Array.from({ length: 7 }, (_, index) => chart.high - ((chart.high - chart.low) * index) / 6), [chart]);
  const activeCandle = hovered ?? chart.display.at(-1);

  useEffect(() => { setOffset(0); }, [candles.length, timeframe]);

  function coordinates(event: PointerEvent<SVGSVGElement>) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return null;
    const x = ((event.clientX - rect.left) / rect.width) * CHART_WIDTH;
    const y = ((event.clientY - rect.top) / rect.height) * CHART_HEIGHT;
    const index = Math.max(0, Math.min(chart.display.length - 1, Math.round((x - PADDING.left - chart.step / 2) / chart.step)));
    return { x, point: { time: chart.display[index].time, price: chart.high - ((y - PADDING.top) / chart.plotHeight) * (chart.high - chart.low) } };
  }

  function handlePointerMove(event: PointerEvent<SVGSVGElement>) {
    const position = coordinates(event);
    if (!position) return;
    const index = Math.max(0, Math.min(chart.display.length - 1, Math.floor((position.x - PADDING.left) / chart.step)));
    setHovered(chart.display[index]);
    if (dragStart !== null) {
      const moved = Math.round((dragStart - position.x) / chart.step);
      setOffset((current) => Math.max(0, Math.min(candles.length - chart.display.length, current + moved)));
      setDragStart(position.x);
    }
  }

  function handlePointerDown(event: PointerEvent<SVGSVGElement>) {
    const position = coordinates(event);
    if (!position) return;
    if (tool === 'crosshair') { setDragStart(position.x); event.currentTarget.setPointerCapture(event.pointerId); return; }
    if (tool === 'horizontal' || tool === 'vertical') { onDrawing({ id: crypto.randomUUID(), type: tool, start: position.point }); return; }
    if (!pendingStart) { setPendingStart(position.point); return; }
    onDrawing({ id: crypto.randomUUID(), type: tool, start: pendingStart, end: position.point });
    setPendingStart(null);
  }

  function handleWheel(event: WheelEvent<SVGSVGElement>) {
    event.preventDefault();
    if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) { setVisibleCount((current) => Math.max(25, Math.min(candles.length, current + (event.deltaY + event.deltaX > 0 ? 12 : -12)))); return; }
    setPriceZoom((current) => Math.max(0.45, Math.min(4, current * (event.deltaY > 0 ? 0.9 : 1.1))));
  }

  const drawingX = (time: number) => chart.x(chart.display.findIndex((candle) => candle.time === time));
  return <section className="backtesting-chart-area">
    <div className="backtesting-ohlc" aria-live="polite"><span>{symbol} · {timeframe}</span><span>O {formatPrice(activeCandle?.open)}</span><span>H {formatPrice(activeCandle?.high)}</span><span>L {formatPrice(activeCandle?.low)}</span><span>C {formatPrice(activeCandle?.close)}</span><span>Vol {activeCandle?.volume.toLocaleString() ?? '--'}</span></div>
    <svg ref={svgRef} className="backtesting-chart" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img" aria-label={`${symbol ?? 'Market'} ${timeframe ?? ''} live MT5 candlestick chart`} onPointerMove={handlePointerMove} onPointerLeave={() => { setHovered(null); setDragStart(null); }} onPointerDown={handlePointerDown} onPointerUp={() => setDragStart(null)} onWheel={handleWheel}>
      {priceTicks.map((price) => <g key={price}><line className="backtesting-grid-line" x1={PADDING.left} x2={CHART_WIDTH - PADDING.right} y1={chart.y(price)} y2={chart.y(price)} /><text className="backtesting-price-label" x={CHART_WIDTH - PADDING.right + 10} y={chart.y(price) + 4}>{formatPrice(price)}</text></g>)}
      {chart.display.map((candle, index) => { const x = chart.x(index); const openY = chart.y(candle.open); const closeY = chart.y(candle.close); const rising = candle.close >= candle.open; const timeStep = Math.max(1, Math.ceil(chart.display.length / 7)); return <g key={candle.time} className={rising ? 'backtesting-candle-up' : 'backtesting-candle-down'}><line x1={x} x2={x} y1={chart.y(candle.high)} y2={chart.y(candle.low)} /><rect x={x - chart.bodyWidth / 2} y={Math.min(openY, closeY)} width={chart.bodyWidth} height={Math.max(1, Math.abs(closeY - openY))} />{index % timeStep === 0 && <text className="backtesting-time-label" x={x} y={CHART_HEIGHT - 12}>{new Date(candle.time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</text>}</g>; })}
      {livePrice !== undefined && <g className="backtesting-live-price"><line x1={PADDING.left} x2={CHART_WIDTH - PADDING.right} y1={chart.y(livePrice)} y2={chart.y(livePrice)} /><text x={CHART_WIDTH - PADDING.right + 10} y={chart.y(livePrice) + 4}>{formatPrice(livePrice)}</text></g>}
      {drawings.map((drawing) => { const startIndex = chart.display.findIndex((candle) => candle.time === drawing.start.time); const endIndex = drawing.end ? chart.display.findIndex((candle) => candle.time === drawing.end?.time) : -1; if (startIndex < 0 || (drawing.end && endIndex < 0)) return null; const x1 = drawingX(drawing.start.time); const y1 = chart.y(drawing.start.price); const x2 = drawing.end ? drawingX(drawing.end.time) : x1; const y2 = drawing.end ? chart.y(drawing.end.price) : y1; const left = Math.min(x1, x2); const top = Math.min(y1, y2); const width = Math.abs(x2 - x1); const height = Math.abs(y2 - y1); if (drawing.type === 'horizontal') return <line key={drawing.id} className="backtesting-drawing" x1={PADDING.left} x2={CHART_WIDTH - PADDING.right} y1={y1} y2={y1} />; if (drawing.type === 'vertical') return <line key={drawing.id} className="backtesting-drawing" x1={x1} x2={x1} y1={PADDING.top} y2={CHART_HEIGHT - PADDING.bottom} />; if (drawing.type === 'rectangle') return <rect key={drawing.id} className="backtesting-drawing backtesting-rectangle" x={left} y={top} width={width} height={height} />; if (drawing.type === 'triangle') return <polygon key={drawing.id} className="backtesting-drawing backtesting-shape" points={`${x1},${y2} ${x2},${y2} ${(x1 + x2) / 2},${y1}`} />; if (drawing.type === 'ellipse') return <ellipse key={drawing.id} className="backtesting-drawing backtesting-shape" cx={left + width / 2} cy={top + height / 2} rx={Math.max(width / 2, 2)} ry={Math.max(height / 2, 2)} />; if (drawing.type === 'long_position' || drawing.type === 'short_position') { const distance = Math.abs(y2 - y1) || 18; const stopY = drawing.type === 'long_position' ? y1 + distance : y1 - distance; return <g key={drawing.id} className={`backtesting-position backtesting-position-${drawing.type === 'long_position' ? 'long' : 'short'}`}><rect x={left} y={Math.min(y1, y2)} width={Math.max(width, 8)} height={distance} /><rect className="backtesting-position-stop" x={left} y={Math.min(y1, stopY)} width={Math.max(width, 8)} height={distance} /><line x1={left} x2={left + Math.max(width, 8)} y1={y1} y2={y1} /><text x={left + 5} y={y1 - 5}>{drawing.type === 'long_position' ? 'LONG' : 'SHORT'}</text></g>; } return <line key={drawing.id} className="backtesting-drawing" x1={x1} y1={y1} x2={drawing.type === 'ray' ? CHART_WIDTH - PADDING.right : x2} y2={drawing.type === 'ray' ? y1 + ((CHART_WIDTH - PADDING.right - x1) * (y2 - y1)) / (x2 - x1 || 1) : y2} />; })}
      {pendingStart && <line className="backtesting-drawing backtesting-drawing-pending" x1={drawingX(pendingStart.time)} x2={drawingX(pendingStart.time)} y1={PADDING.top} y2={CHART_HEIGHT - PADDING.bottom} />}
    </svg>
    <p className="backtesting-chart-hint">Drag to pan · scroll to scale the price axis · Shift + scroll to scale candle width · chart follows the latest MT5 data after each refresh.</p>
  </section>;
}

export function Backtesting() {
  const workspaceRef = useRef<HTMLElement>(null);
  const [accounts, setAccounts] = useState<AccountProfile[]>([]);
  const [accountId, setAccountId] = useState<number | undefined>();
  const [timeframe, setTimeframe] = useState('M5');
  const [marketData, setMarketData] = useState<BacktestingMarketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [tool, setTool] = useState<Tool>('crosshair');
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [replaySession, setReplaySession] = useState<ReplaySession | null>(null);
  const [replayMetrics, setReplayMetrics] = useState<ReplayMetrics | null>(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [datasets, setDatasets] = useState<HistoricalDataset[]>([]);
  const [datasetId, setDatasetId] = useState<number | undefined>();
  const [replayStart, setReplayStart] = useState('');
  const [replayEnd, setReplayEnd] = useState('');

  useEffect(() => { authService.getAccounts().then(({ accounts: availableAccounts }) => { const enabled = availableAccounts.filter((account) => account.enabled); setAccounts(enabled); setAccountId(enabled.find((account) => account.isDefault)?.id ?? enabled[0]?.id); }).catch(() => setAccounts([])); }, []);
  useEffect(() => { if (!accountId) return; authService.getHistoricalDatasets(accountId).then(({ datasets: available }) => { setDatasets(available); setDatasetId(available[0]?.id); }).catch(() => setDatasets([])); }, [accountId]);
  useEffect(() => { if (!accountId) { setLoading(false); setMarketData({ status: 'UNAVAILABLE', reason: 'No enabled trading account is available.' }); return; } let active = true; const refresh = () => { setLoading(true); authService.getBacktestingMarketData(accountId, timeframe).then((result) => { if (active) setMarketData(result); }).catch((error: Error) => { if (active) setMarketData({ status: 'UNAVAILABLE', reason: error.message }); }).finally(() => { if (active) setLoading(false); }); }; refresh(); const interval = window.setInterval(refresh, 10_000); return () => { active = false; window.clearInterval(interval); }; }, [accountId, timeframe, refreshVersion]);
  useEffect(() => {
    if (!accountId || !marketData?.brokerSymbol) { setDrawings([]); return; }
    let active = true;
    authService.getBacktestingDrawings(accountId, timeframe, marketData.brokerSymbol)
      .then(({ drawings: saved }) => { if (active) setDrawings(saved.map((drawing) => ({ ...drawing, id: String(drawing.id), end: drawing.end ?? undefined }))); })
      .catch(() => { if (active) setDrawings([]); });
    return () => { active = false; };
  }, [accountId, marketData?.brokerSymbol, timeframe]);
  const candles = useMemo(() => replaySession?.candles ?? marketData?.candles ?? [], [marketData, replaySession]);
  async function startReplay() {
    if (!accountId) return;
    setReplayLoading(true);
    try { setReplaySession(datasetId ? await authService.createDatasetReplay(accountId, datasetId, replayStart || undefined, replayEnd || undefined) : await authService.createReplay(accountId, timeframe)); } finally { setReplayLoading(false); }
  }
  async function uploadDataset(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !accountId) return;
    setReplayLoading(true);
    try { const uploaded = await authService.uploadHistoricalDataset(accountId, file, { timeframe, timezone: 'UTC' }); setDatasets((current) => [uploaded, ...current]); setDatasetId(uploaded.id); } finally { setReplayLoading(false); event.target.value = ''; }
  }
  async function replayAction(action: 'step' | 'reset' | 'play' | 'pause' | 'execute') {
    if (!replaySession) return;
    setReplayLoading(true);
    try { const result = await authService.replayAction(replaySession.id, action); setReplaySession(result.session); if (result.metrics) setReplayMetrics(result.metrics); } finally { setReplayLoading(false); }
  }
  useEffect(() => {
    if (!replaySession || replaySession.status !== 'PLAYING') return;
    const interval = window.setInterval(() => { void replayAction('step'); }, Math.max(250, 1000 / replaySession.speed));
    return () => window.clearInterval(interval);
  }, [replaySession]);
  async function toggleFullscreen() { if (document.fullscreenElement) await document.exitFullscreen(); else await workspaceRef.current?.requestFullscreen(); }
  function saveDrawing(drawing: Drawing) {
    setDrawings((current) => [...current, drawing]);
    if (!accountId || !marketData?.brokerSymbol) return;
    authService.createBacktestingDrawing(accountId, timeframe, { type: drawing.type, start: drawing.start, end: drawing.end }, marketData.brokerSymbol)
      .then((saved) => setDrawings((current) => current.map((item) => item.id === drawing.id ? { ...saved, id: String(saved.id), end: saved.end ?? undefined } : item)))
      .catch(() => setDrawings((current) => current.filter((item) => item.id !== drawing.id)));
  }
  async function clearDrawings() {
    if (!accountId || !marketData?.brokerSymbol) return;
    const previous = drawings;
    setDrawings([]);
    try { await authService.clearBacktestingDrawings(accountId, timeframe, marketData.brokerSymbol); } catch { setDrawings(previous); }
  }

  return <main ref={workspaceRef} className="dashboard-shell backtesting-shell">
    <div className="backtesting-replay-controls" aria-label="Historical replay controls">
      <span className="backtesting-replay-label">{replaySession ? `REPLAY ${replaySession.cursor}/${replaySession.totalCandles}` : 'LIVE MT5 FEED'}</span>
      {!replaySession && <><label className="backtesting-replay-field">Dataset<select value={datasetId ?? ''} onChange={(event) => setDatasetId(event.target.value ? Number(event.target.value) : undefined)}><option value="">MT5 historical window</option>{datasets.map((dataset) => <option value={dataset.id} key={dataset.id}>{dataset.symbol} {dataset.timeframe} / {dataset.version}</option>)}</select></label><label className="backtesting-replay-field">From<input type="date" value={replayStart} onChange={(event) => setReplayStart(event.target.value)} /></label><label className="backtesting-replay-field">To<input type="date" value={replayEnd} onChange={(event) => setReplayEnd(event.target.value)} /></label><label className="backtesting-replay-upload">Import<input type="file" accept=".csv,.parquet,.pq" onChange={(event) => void uploadDataset(event)} disabled={replayLoading} /></label></>}
      {!replaySession ? <button type="button" onClick={() => void startReplay()} disabled={replayLoading || !accountId} title="Start historical replay"><RotateCcw size={15} /> Start replay</button> : <><button type="button" onClick={() => void replayAction('step')} disabled={replayLoading || replaySession.status === 'COMPLETE'} title="Advance one candle">Step</button><button type="button" onClick={() => void replayAction(replaySession.status === 'PLAYING' ? 'pause' : 'play')} disabled={replayLoading}>{replaySession.status === 'PLAYING' ? 'Pause' : 'Play'}</button><button type="button" onClick={() => void replayAction('execute')} disabled={replayLoading} title="Execute current signal">Execute</button><button type="button" onClick={() => void replayAction('reset')} disabled={replayLoading}>Reset</button><button type="button" onClick={() => setReplaySession(null)}>Live</button></>}
    </div>
    {replaySession && <div className="backtesting-replay-ledger">Trades {replaySession.trades.length} <span>Open {replaySession.trades.filter((trade) => trade.status === 'OPEN').length}</span> <span>Closed {replaySession.trades.filter((trade) => trade.status === 'CLOSED').length}</span> <span>P/L {replaySession.trades.reduce((total, trade) => total + trade.pnl, 0).toFixed(2)}</span>{replayMetrics && <><span>Win {Math.round(replayMetrics.winRate * 100)}%</span><span>PF {replayMetrics.profitFactor?.toFixed(2) ?? '--'}</span><span>DD {replayMetrics.maxDrawdown.toFixed(2)}</span><span>Exp {replayMetrics.expectancy.toFixed(2)}</span></>}</div>}
    <header className="backtesting-header"><div className="backtesting-brand"><p className="eyebrow">BACKTESTING / LIVE MT5 TERMINAL</p><strong>{marketData?.brokerSymbol ?? 'CONNECTING'}</strong><span className={marketData?.status === 'HEALTHY' ? 'backtesting-live-state' : 'backtesting-error-state'}>{loading ? 'REFRESHING' : marketData?.status ?? 'CONNECTING'}</span></div><label className="backtesting-header-select"><span>Account</span><select value={accountId ?? ''} onChange={(event) => setAccountId(Number(event.target.value))} disabled={!accounts.length}>{accounts.map((account) => <option value={account.id} key={account.id}>{account.displayName}</option>)}</select></label><nav className="backtesting-timeframes" aria-label="Chart timeframe">{TIMEFRAMES.map((item) => <button type="button" key={item} className={item === timeframe ? 'backtesting-tool-active' : ''} onClick={() => setTimeframe(item)}>{item}</button>)}</nav><div className="backtesting-header-actions"><button type="button" onClick={() => setRefreshVersion((current) => current + 1)} disabled={loading} title="Refresh MT5 data"><RefreshCw size={17} /></button><button type="button" onClick={() => void toggleFullscreen()} title="Full-screen workspace"><Maximize2 size={17} /></button></div></header>
    <section className="backtesting-workspace"><aside className="backtesting-drawing-toolbar" aria-label="Chart drawing tools"><button type="button" className={tool === 'crosshair' ? 'backtesting-tool-active' : ''} onClick={() => setTool('crosshair')} title="Pan and inspect"><MoveHorizontal size={18} /></button><button type="button" className={tool === 'trendline' ? 'backtesting-tool-active' : ''} onClick={() => setTool('trendline')} title="Trend line"><TrendingUp size={18} /></button><button type="button" className={tool === 'ray' ? 'backtesting-tool-active' : ''} onClick={() => setTool('ray')} title="Ray"><ArrowUpRight size={18} /></button><button type="button" className={tool === 'horizontal' ? 'backtesting-tool-active' : ''} onClick={() => setTool('horizontal')} title="Horizontal line"><Minus size={18} /></button><button type="button" className={tool === 'vertical' ? 'backtesting-tool-active' : ''} onClick={() => setTool('vertical')} title="Vertical line"><MoveHorizontal size={18} /></button><button type="button" className={tool === 'rectangle' ? 'backtesting-tool-active' : ''} onClick={() => setTool('rectangle')} title="Rectangle"><Square size={18} /></button><button type="button" className={tool === 'triangle' ? 'backtesting-tool-active' : ''} onClick={() => setTool('triangle')} title="Triangle"><Triangle size={18} /></button><button type="button" className={tool === 'ellipse' ? 'backtesting-tool-active' : ''} onClick={() => setTool('ellipse')} title="Ellipse"><Circle size={18} /></button><button type="button" className={tool === 'long_position' ? 'backtesting-tool-active' : ''} onClick={() => setTool('long_position')} title="Long position"><ArrowUpRight size={18} /></button><button type="button" className={tool === 'short_position' ? 'backtesting-tool-active' : ''} onClick={() => setTool('short_position')} title="Short position"><ArrowDownRight size={18} /></button><button type="button" className={tool === 'crosshair' ? 'backtesting-tool-active' : ''} onClick={() => setTool('crosshair')} title="Crosshair mode"><Crosshair size={18} /></button><button type="button" onClick={() => void clearDrawings()} title="Clear saved drawings"><Eraser size={18} /></button><button type="button" onClick={() => { void clearDrawings(); setRefreshVersion((current) => current + 1); }} title="Reset chart"><RotateCcw size={18} /></button></aside>{marketData?.status === 'HEALTHY' && candles.length > 0 ? <Chart candles={candles} symbol={marketData.brokerSymbol} timeframe={marketData.timeframe} livePrice={marketData.price?.ask} tool={tool} drawings={drawings} onDrawing={saveDrawing} /> : <section className="backtesting-unavailable" role="alert"><p className="eyebrow">LIVE DATA UNAVAILABLE</p><h2>MT5 market data is not available.</h2><p>{marketData?.reason ?? 'Connecting to the selected MT5 terminal.'}</p></section>}</section>
  </main>;
}
