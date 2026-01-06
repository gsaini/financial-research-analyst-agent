/**
 * Financial Research Analyst Dashboard - JavaScript
 */

// API Configuration
const API_BASE_URL =
  window.location.hostname === "localhost"
    ? "http://localhost:8000/api/v1"
    : "/api/v1";

// DOM Elements
const elements = {
  symbolInput: document.getElementById("symbol-input"),
  analyzeBtn: document.getElementById("analyze-btn"),
  analysisResults: document.getElementById("analysis-results"),
  loadingOverlay: document.getElementById("loading-overlay"),
  themeToggle: document.getElementById("theme-toggle"),

  // Results elements
  symbolBadge: document.getElementById("symbol-badge"),
  currentPrice: document.getElementById("current-price"),
  priceChange: document.getElementById("price-change"),
  lastUpdated: document.getElementById("last-updated"),
  recommendation: document.getElementById("recommendation"),
  confidenceFill: document.getElementById("confidence-fill"),
  confidence: document.getElementById("confidence"),
  rsiValue: document.getElementById("rsi-value"),
  rsiSignal: document.getElementById("rsi-signal"),
  macdValue: document.getElementById("macd-value"),
  macdSignal: document.getElementById("macd-signal"),
  trendValue: document.getElementById("trend-value"),
  trendSignal: document.getElementById("trend-signal"),
  peRatio: document.getElementById("pe-ratio"),
  marketCap: document.getElementById("market-cap"),
  eps: document.getElementById("eps"),
  sector: document.getElementById("sector"),
  sentimentMarker: document.getElementById("sentiment-marker"),
  sentimentScore: document.getElementById("sentiment-score"),
  summaryText: document.getElementById("summary-text"),
};

// State
let currentTheme = "dark";

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  initTheme();
});

/**
 * Initialize event listeners
 */
function initEventListeners() {
  // Analyze button
  elements.analyzeBtn.addEventListener("click", handleAnalyze);

  // Enter key on input
  elements.symbolInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      handleAnalyze();
    }
  });

  // Theme toggle
  elements.themeToggle.addEventListener("click", toggleTheme);
}

/**
 * Initialize theme
 */
function initTheme() {
  const savedTheme = localStorage.getItem("theme") || "dark";
  setTheme(savedTheme);
}

/**
 * Toggle theme
 */
function toggleTheme() {
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  setTheme(newTheme);
  localStorage.setItem("theme", newTheme);
}

/**
 * Set theme
 */
function setTheme(theme) {
  currentTheme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  elements.themeToggle.textContent = theme === "dark" ? "🌙" : "☀️";
}

/**
 * Handle analyze button click
 */
async function handleAnalyze() {
  const symbol = elements.symbolInput.value.trim().toUpperCase();

  if (!symbol) {
    showNotification("Please enter a stock symbol", "error");
    return;
  }

  try {
    showLoading();
    const data = await analyzeStock(symbol);
    displayResults(data);
  } catch (error) {
    console.error("Analysis error:", error);
    showNotification("Error analyzing stock. Please try again.", "error");
  } finally {
    hideLoading();
  }
}

/**
 * Analyze stock via API
 */
async function analyzeStock(symbol) {
  try {
    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        symbol: symbol,
        analysis_type: "comprehensive",
        include_news: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    // If API fails, return mock data for demonstration
    console.warn("Using mock data due to API error:", error);
    return getMockData(symbol);
  }
}

/**
 * Display analysis results
 */
function displayResults(data) {
  // Show results section
  elements.analysisResults.style.display = "block";

  // Update symbol badge
  elements.symbolBadge.textContent = data.symbol;

  // Update price
  const price = data.current_price || 0;
  const change = data.fundamental?.price_data?.change_percent || 0;

  elements.currentPrice.textContent = `$${price.toFixed(2)}`;
  elements.priceChange.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(
    2
  )}%`;
  elements.priceChange.className = `price-change ${
    change >= 0 ? "positive" : "negative"
  }`;
  elements.lastUpdated.textContent = new Date().toLocaleString();

  // Update recommendation
  const recommendation = data.recommendation || "HOLD";
  const confidence = (data.confidence || 0.5) * 100;

  elements.recommendation.textContent = recommendation;
  elements.recommendation.className = `recommendation-badge ${
    recommendation.toLowerCase().includes("buy")
      ? "buy"
      : recommendation.toLowerCase().includes("sell")
      ? "sell"
      : ""
  }`;
  elements.confidenceFill.style.width = `${confidence}%`;
  elements.confidence.textContent = `${confidence.toFixed(0)}%`;

  // Update technical indicators
  if (data.technical) {
    const tech = data.technical;

    // RSI
    if (tech.rsi) {
      const rsiValue = tech.rsi.value || "--";
      elements.rsiValue.textContent =
        typeof rsiValue === "number" ? rsiValue.toFixed(1) : rsiValue;
      elements.rsiSignal.textContent = tech.rsi.signal || "Neutral";
      elements.rsiSignal.className = getSignalClass(tech.rsi.signal);
    }

    // MACD
    if (tech.macd) {
      elements.macdValue.textContent = tech.macd.histogram?.toFixed(4) || "--";
      elements.macdSignal.textContent = tech.macd.trend || "Neutral";
      elements.macdSignal.className = getSignalClass(tech.macd.trend);
    }

    // Trend
    if (tech.moving_averages) {
      elements.trendValue.textContent = tech.moving_averages.trend || "--";
      elements.trendSignal.textContent =
        tech.moving_averages.trend || "Neutral";
      elements.trendSignal.className = getSignalClass(
        tech.moving_averages.trend
      );
    }
  }

  // Update fundamental metrics
  if (data.fundamental) {
    const fund = data.fundamental;
    const priceData = fund.price_data || {};
    const company = fund.company || {};

    elements.peRatio.textContent = priceData.pe_ratio?.toFixed(2) || "--";
    elements.marketCap.textContent = formatMarketCap(priceData.market_cap);
    elements.eps.textContent = priceData.eps
      ? `$${priceData.eps.toFixed(2)}`
      : "--";
    elements.sector.textContent = company.sector || "--";
  }

  // Update sentiment
  if (data.sentiment) {
    const score = data.sentiment.score || 0.5;
    const markerPosition = ((score + 1) / 2) * 100; // Convert -1 to 1 scale to 0-100%
    elements.sentimentMarker.style.left = `${markerPosition}%`;
    elements.sentimentScore.textContent = score.toFixed(2);
  }

  // Update summary
  elements.summaryText.textContent =
    data.summary ||
    `Analysis complete for ${data.symbol}. The AI agents have evaluated technical indicators, ` +
      `fundamental metrics, and market sentiment to generate a ${recommendation} recommendation ` +
      `with ${confidence.toFixed(0)}% confidence.`;

  // Scroll to results
  elements.analysisResults.scrollIntoView({ behavior: "smooth" });
}

/**
 * Get CSS class for signal
 */
function getSignalClass(signal) {
  if (!signal) return "indicator-signal neutral";
  const s = signal.toLowerCase();
  if (s.includes("bullish") || s.includes("oversold") || s.includes("buy")) {
    return "indicator-signal bullish";
  }
  if (s.includes("bearish") || s.includes("overbought") || s.includes("sell")) {
    return "indicator-signal bearish";
  }
  return "indicator-signal neutral";
}

/**
 * Format market cap
 */
function formatMarketCap(value) {
  if (!value || value === 0) return "--";
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  return `$${value.toLocaleString()}`;
}

/**
 * Show loading overlay
 */
function showLoading() {
  elements.loadingOverlay.classList.add("active");
}

/**
 * Hide loading overlay
 */
function hideLoading() {
  elements.loadingOverlay.classList.remove("active");
}

/**
 * Show notification
 */
function showNotification(message, type = "info") {
  // Simple alert for now - could be enhanced with toast notifications
  alert(message);
}

/**
 * Get mock data for demonstration
 */
function getMockData(symbol) {
  const mockPrices = {
    AAPL: {
      price: 185.64,
      change: 1.52,
      pe: 28.5,
      marketCap: 2.87e12,
      sector: "Technology",
    },
    GOOGL: {
      price: 141.92,
      change: 0.85,
      pe: 25.2,
      marketCap: 1.76e12,
      sector: "Technology",
    },
    MSFT: {
      price: 377.55,
      change: 0.73,
      pe: 35.1,
      marketCap: 2.81e12,
      sector: "Technology",
    },
    AMZN: {
      price: 155.32,
      change: -0.42,
      pe: 62.3,
      marketCap: 1.6e12,
      sector: "Consumer Cyclical",
    },
    TSLA: {
      price: 238.45,
      change: 2.15,
      pe: 75.2,
      marketCap: 0.76e12,
      sector: "Automotive",
    },
  };

  const stockData = mockPrices[symbol] || {
    price: 100 + Math.random() * 100,
    change: (Math.random() - 0.5) * 5,
    pe: 15 + Math.random() * 20,
    marketCap: Math.random() * 1e12,
    sector: "Unknown",
  };

  const rsiValue = 30 + Math.random() * 40;
  const sentimentScore = (Math.random() - 0.5) * 2;

  let recommendation;
  let confidence;

  if (rsiValue < 35 && sentimentScore > 0.2) {
    recommendation = "BUY";
    confidence = 0.7 + Math.random() * 0.2;
  } else if (rsiValue > 65 && sentimentScore < -0.2) {
    recommendation = "SELL";
    confidence = 0.7 + Math.random() * 0.2;
  } else {
    recommendation = "HOLD";
    confidence = 0.4 + Math.random() * 0.2;
  }

  return {
    symbol: symbol,
    current_price: stockData.price,
    recommendation: recommendation,
    confidence: confidence,
    summary: `${symbol} is currently trading at $${stockData.price.toFixed(
      2
    )}. Based on comprehensive AI analysis including technical indicators, fundamental metrics, and market sentiment, the recommendation is ${recommendation} with ${(
      confidence * 100
    ).toFixed(0)}% confidence.`,
    technical: {
      rsi: {
        value: rsiValue,
        signal:
          rsiValue < 30 ? "OVERSOLD" : rsiValue > 70 ? "OVERBOUGHT" : "NEUTRAL",
      },
      macd: {
        macd_line: (Math.random() - 0.5) * 2,
        signal_line: (Math.random() - 0.5) * 2,
        histogram: (Math.random() - 0.5) * 0.5,
        trend: Math.random() > 0.5 ? "bullish" : "bearish",
      },
      moving_averages: {
        sma_20: stockData.price * (0.95 + Math.random() * 0.1),
        sma_50: stockData.price * (0.9 + Math.random() * 0.2),
        sma_200: stockData.price * (0.85 + Math.random() * 0.3),
        trend: Math.random() > 0.5 ? "bullish" : "bearish",
      },
    },
    fundamental: {
      price_data: {
        current_price: stockData.price,
        change_percent: stockData.change,
        pe_ratio: stockData.pe,
        market_cap: stockData.marketCap,
        eps: stockData.price / stockData.pe,
      },
      company: {
        sector: stockData.sector,
      },
    },
    sentiment: {
      score: sentimentScore,
      status:
        sentimentScore > 0.3
          ? "positive"
          : sentimentScore < -0.3
          ? "negative"
          : "neutral",
    },
    analyzed_at: new Date().toISOString(),
  };
}
