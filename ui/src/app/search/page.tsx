"use client";

import { useState, useRef } from "react";
import { Search, Loader2, TrendingUp, TrendingDown, ExternalLink, ChevronDown, ChevronRight } from "lucide-react";
import { searchStocks, getStockData, type StockSearchResult, type StockData } from "@/lib/api";
import { cn } from "@/lib/utils";

function fmt(val: number | null, prefix = "$", suffix = ""): string {
  if (val === null || val === undefined) return "—";
  if (prefix === "%" || suffix === "%") return `${(val * 100).toFixed(2)}%`;
  if (Math.abs(val) >= 1e12) return `${prefix}${(val / 1e12).toFixed(2)}T${suffix}`;
  if (Math.abs(val) >= 1e9)  return `${prefix}${(val / 1e9).toFixed(2)}B${suffix}`;
  if (Math.abs(val) >= 1e6)  return `${prefix}${(val / 1e6).toFixed(2)}M${suffix}`;
  return `${prefix}${val.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
}

function fmtNum(val: number | null, decimals = 2): string {
  if (val === null || val === undefined) return "—";
  return val.toFixed(decimals);
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl px-4 py-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-sm font-semibold text-gray-100">{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  );
}

function StockCard({ data }: { data: StockData }) {
  const [showDesc, setShowDesc] = useState(false);
  const priceChange = data.price && data.prev_close ? data.price - data.prev_close : null;
  const pricePct = priceChange && data.prev_close ? (priceChange / data.prev_close) * 100 : null;
  const isUp = priceChange !== null && priceChange >= 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-gray-100">{data.symbol}</h2>
            {data.sector && (
              <span className="text-xs bg-gray-800 border border-gray-700 text-gray-400 rounded-full px-2 py-0.5">
                {data.sector}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-400">{data.name}</p>
          {data.industry && <p className="text-xs text-gray-600 mt-0.5">{data.industry}</p>}
        </div>
        {data.website && (
          <a
            href={data.website}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Website
          </a>
        )}
      </div>

      {/* Price */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl px-5 py-4 flex items-end gap-4">
        <div>
          <p className="text-3xl font-bold text-gray-100">{fmt(data.price)}</p>
          {priceChange !== null && pricePct !== null && (
            <div className={cn("flex items-center gap-1 mt-1 text-sm", isUp ? "text-green-400" : "text-red-400")}>
              {isUp ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {isUp ? "+" : ""}{fmt(priceChange)} ({isUp ? "+" : ""}{pricePct.toFixed(2)}%)
            </div>
          )}
        </div>
        <div className="ml-auto text-right">
          <p className="text-xs text-gray-500">52-week range</p>
          <p className="text-sm text-gray-300">
            {fmt(data.week_52_low)} – {fmt(data.week_52_high)}
          </p>
        </div>
      </div>

      {/* Key stats grid */}
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Valuation</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <StatCard label="Market Cap"    value={fmt(data.market_cap)} />
          <StatCard label="P/E Ratio"     value={fmtNum(data.pe_ratio)} sub={`Fwd: ${fmtNum(data.forward_pe)}`} />
          <StatCard label="EPS"           value={fmt(data.eps)} />
          <StatCard label="Price/Book"    value={fmtNum(data.price_to_book)} />
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Financials</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <StatCard label="Revenue"       value={fmt(data.revenue)} />
          <StatCard label="Net Income"    value={fmt(data.net_income)} />
          <StatCard label="EBITDA"        value={fmt(data.ebitda)} />
          <StatCard label="Total Debt"    value={fmt(data.total_debt)} />
          <StatCard label="Cash"          value={fmt(data.total_cash)} />
          <StatCard label="Gross Margin"  value={fmtNum(data.gross_margins ? data.gross_margins * 100 : null) + "%"} />
          <StatCard label="Profit Margin" value={fmtNum(data.profit_margins ? data.profit_margins * 100 : null) + "%"} />
          <StatCard label="Beta"          value={fmtNum(data.beta)} />
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Trading</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <StatCard label="Open"          value={fmt(data.open)} />
          <StatCard label="Day Low/High"  value={`${fmt(data.day_low)} / ${fmt(data.day_high)}`} />
          <StatCard label="Volume"        value={fmt(data.volume, "", "")} />
          <StatCard label="Avg Volume"    value={fmt(data.avg_volume, "", "")} />
          {data.dividend_yield && (
            <StatCard label="Dividend Yield" value={fmtNum(data.dividend_yield * 100) + "%"} sub={`$${fmtNum(data.dividend_rate)} / share`} />
          )}
        </div>
      </div>

      {/* Description */}
      {data.description && (
        <div>
          <button
            onClick={() => setShowDesc(!showDesc)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors mb-2"
          >
            {showDesc ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            About {data.name}
          </button>
          {showDesc && (
            <p className="text-xs text-gray-400 leading-relaxed bg-gray-800/30 rounded-xl px-4 py-3 border border-gray-700/30">
              {data.description}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<StockSearchResult[]>([]);
  const [stockData, setStockData] = useState<StockData | null>(null);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleInput(val: string) {
    setQuery(val);
    setError(null);
    if (!val.trim()) { setSuggestions([]); return; }

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await searchStocks(val);
        setSuggestions(results);
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 350);
  }

  async function selectTicker(symbol: string, name: string) {
    setQuery(name || symbol);
    setSuggestions([]);
    setLoading(true);
    setError(null);
    setStockData(null);
    try {
      const data = await getStockData(symbol);
      setStockData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch stock data");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSuggestions([]);
    setLoading(true);
    setError(null);
    setStockData(null);
    try {
      const data = await getStockData(query.trim().toUpperCase());
      setStockData(data);
    } catch {
      // Try searching first result
      try {
        const results = await searchStocks(query.trim());
        if (results.length > 0) {
          await selectTicker(results[0].symbol, results[0].name);
        } else {
          setError(`No results found for "${query}"`);
        }
      } catch {
        setError(`No results found for "${query}"`);
      }
    } finally {
      setLoading(false);
    }
  }

  const POPULAR = ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "AMZN", "META"];

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Company Search</h1>
        <p className="text-xs text-gray-500 mt-1">Live stock data powered by Yahoo Finance via MCP</p>
      </div>

      {/* Search box */}
      <div className="relative mb-6">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              value={query}
              onChange={(e) => handleInput(e.target.value)}
              placeholder="Search company name or ticker (e.g. Apple, AAPL)"
              className="w-full bg-gray-800 border border-gray-700 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-600 transition-colors"
            />
            {searching && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 animate-spin" />
            )}
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white rounded-xl px-5 py-3 text-sm font-medium transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
          </button>
        </form>

        {/* Autocomplete dropdown */}
        {suggestions.length > 0 && (
          <div className="absolute top-full mt-1 left-0 right-14 bg-gray-800 border border-gray-700 rounded-xl shadow-xl z-10 overflow-hidden">
            {suggestions.map((s) => (
              <button
                key={s.symbol}
                onClick={() => selectTicker(s.symbol, s.name)}
                className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-gray-700 transition-colors text-left"
              >
                <div>
                  <span className="text-sm font-mono text-brand-400">{s.symbol}</span>
                  <span className="text-sm text-gray-300 ml-2">{s.name}</span>
                </div>
                <span className="text-xs text-gray-600">{s.exchange}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Popular tickers */}
      {!stockData && !loading && (
        <div className="mb-6">
          <p className="text-xs text-gray-500 mb-2">Popular</p>
          <div className="flex flex-wrap gap-2">
            {POPULAR.map((t) => (
              <button
                key={t}
                onClick={() => selectTicker(t, t)}
                className="text-xs font-mono bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 transition-colors"
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-8 justify-center">
          <Loader2 className="w-5 h-5 animate-spin" />
          Fetching live data...
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-xl px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      {stockData && !loading && <StockCard data={stockData} />}
    </div>
  );
}
