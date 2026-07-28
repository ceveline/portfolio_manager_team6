const API_BASE = "/api";
let holdingsData = [];
let portfolioPieChart = null;
let performanceChart = null;
let pnlBarChart = null;
let portfolioData = [];
let currentSortColumn = "ticker"; // Default sort by ticker
let currentSortDirection = "asc";
let availableQuantities = {}; // Map of ticker to total available quantity
let historyData = []; // Store transaction data for sorting
let sortedHistoryData = []; // Store currently sorted transaction data for pagination
let currentHistorySortColumn = "transaction_date"; // Default sort by date
let currentHistorySortDirection = "desc"; // Descending for most recent first
let historyCurrentPage = 1;
const historyRowsPerPage = 5;

async function loadPortfolio(filters = {}) {
  
  const holdingsRes = await fetch(`${API_BASE}/holdings`);
  const holdings = await holdingsRes.json();
  holdingsData = holdings;

  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      params.append(key, value);
    }
  });

  const historyUrl = `${API_BASE}/transactions${params.toString() ? `?${params.toString()}` : ""}`;
  const historyRes = await fetch(historyUrl);
  const history = await historyRes.json();

  await loadPortfolioWithSummary();
  loadHistory(history);
  populateSellDropdown(holdings);
  clearSellDetails();
}

function getTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function resetHistoryFilter() {
  const actionEl = document.getElementById("history-filter-action");
  const tickerEl = document.getElementById("history-filter-ticker");
  const quantityOperatorEl = document.getElementById("history-filter-quantity-operator");
  const quantityEl = document.getElementById("history-filter-quantity");
  const priceOperatorEl = document.getElementById("history-filter-price-operator");
  const priceEl = document.getElementById("history-filter-price");
  const priceRangeEl = document.getElementById("history-filter-price-range");
  const yearEl = document.getElementById("history-filter-year");
  const dateEl = document.getElementById("history-filter-date");

  if (actionEl) actionEl.value = "";
  if (tickerEl) tickerEl.value = "";
  if (quantityOperatorEl) quantityOperatorEl.value = "";
  if (quantityEl) quantityEl.value = "";
  if (priceOperatorEl) priceOperatorEl.value = "";
  if (priceEl) priceEl.value = "";
  if (priceRangeEl) priceRangeEl.value = "";
  if (yearEl) yearEl.value = "";
  if (dateEl) dateEl.value = "";
}

function getDisplayedPurchasePrice() {
  const priceDisplay = document.getElementById("purchase_price");
  if (!priceDisplay) return null;

  const rawText = (priceDisplay.textContent || priceDisplay.innerText || "").trim();
  if (!rawText || rawText === "-") return null;

  const cleaned = rawText.replace(/[$,\s]/g, "");
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

async function fetchAndDisplayPrice(ticker) {
  const priceDisplay = document.getElementById("purchase_price");
  if (!priceDisplay) return null;

  if (!ticker) {
    priceDisplay.textContent = "-";
    return null;
  }

  priceDisplay.textContent = "Loading...";

  try {
    const res = await fetch(`${API_BASE}/price/${encodeURIComponent(ticker)}`);
    const payload = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(payload.error || "price request failed");
    }

    const priceValue = Number(payload.price ?? payload.price_data?.close?.[0] ?? payload.close);

    if (Number.isFinite(priceValue)) {
      priceDisplay.textContent = `$${priceValue.toFixed(2)}`;
      return priceValue;
    }

    throw new Error("invalid price response");
  } catch (err) {
    console.error("Error fetching price:", err);
    priceDisplay.textContent = "Unavailable";
    return null;
  }
}

async function buyStock(ticker, quantity, purchasePrice, purchaseDate) {
  const body = {
    ticker,
    quantity,
    purchase_price: purchasePrice,
    purchase_date: purchaseDate || getTodayDate(),
  };

  const response = await fetch(`${API_BASE}/holdings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || "Unable to buy stock");
  }

  return response.json();
}

async function loadPortfolioWithSummary() {
  try {
    const res = await fetch(`${API_BASE}/summary`);
    if (!res.ok) throw new Error("Failed to load summary");
    const summary = await res.json();

    document.querySelector("#portfolio-cost-basis").textContent = `$${summary.total_cost_basis.toFixed(2)}`;
    document.querySelector("#portfolio-market-value").textContent = `$${summary.total_market_value.toFixed(2)}`;
    document.querySelector("#portfolio-unrealized-pnl").textContent = `$${summary.total_unrealized_pnl.toFixed(2)}`;
    document.querySelector("#portfolio-total-return").textContent = `${summary.total_return_pct.toFixed(2)}%`;

    document.querySelector("#total-value strong").textContent = `$${summary.total_market_value.toFixed(2)}`;
    document.querySelector("#total-holdings strong").textContent = summary.positions.length;

    let totalShares = 0;
    summary.positions.forEach(pos => {
      totalShares += pos.shares_held;
    });
    document.querySelector("#total-shares strong").textContent = totalShares.toFixed(0);

    const sign = summary.total_unrealized_pnl >= 0 ? "+" : "";
    document.querySelector("#total-gain-loss strong").textContent =
      `${sign}$${summary.total_unrealized_pnl.toFixed(2)} (${sign}${summary.total_return_pct.toFixed(2)}%)`;

    if (!summary.positions || summary.positions.length === 0) {
      const tbody = document.getElementById("consolidated-body");
      tbody.innerHTML = '<tr class="empty-state"><td colspan="8">No portfolio data yet.</td></tr>';
      renderPortfolioPieChart([]);
      return;
    }

    // Store portfolio data and render with default sorting by ticker
    portfolioData = summary.positions;
    sortPortfolioTable("ticker"); // Apply default sort
    renderPortfolioPieChart(summary.positions);
    renderPnLBarChart(summary.positions);
  } catch (err) {
    console.error("Error loading portfolio summary:", err);
  }
}

function renderPortfolioTable(positions) {
  const tbody = document.getElementById("consolidated-body");
  tbody.innerHTML = "";

  positions.forEach((pos) => {
    const row = document.createElement("tr");
    const unrealizedPnlStr = pos.unrealized_pnl !== null ? `$${pos.unrealized_pnl.toFixed(2)}` : "-";
    const marketValueStr = pos.market_value !== null ? `$${pos.market_value.toFixed(2)}` : "-";
    const currentPriceStr = pos.current_price !== null ? `$${pos.current_price.toFixed(2)}` : "-";

    row.innerHTML = `
      <td>${pos.ticker}</td>
      <td>${pos.shares_held}</td>
      <td>$${pos.avg_cost.toFixed(2)}</td>
      <td>${currentPriceStr}</td>
      <td>$${pos.cost_basis.toFixed(2)}</td>
      <td>${marketValueStr}</td>
      <td>${unrealizedPnlStr}</td>
      <td>$${pos.realized_pnl.toFixed(2)}</td>
    `;
    tbody.appendChild(row);
  });
}

function sortPortfolioTable(column) {
  if (currentSortColumn === column) {
    currentSortDirection = currentSortDirection === "asc" ? "desc" : "asc";
  } else {
    currentSortColumn = column;
    currentSortDirection = "asc";
  }

  // Update header indicators in portfolio table only
  const consolidatedBody = document.getElementById("consolidated-body");
  const portfolioTable = consolidatedBody?.closest("table");
  if (portfolioTable) {
    portfolioTable.querySelectorAll("th.sortable").forEach(th => {
      th.classList.remove("asc", "desc");
      if (th.dataset.sort === column) {
        th.classList.add(currentSortDirection);
      }
    });
  }

  // Sort data
  const sorted = [...portfolioData].sort((a, b) => {
    let aVal = a[column];
    let bVal = b[column];

    // Handle null values
    if (aVal === null) aVal = -Infinity;
    if (bVal === null) bVal = -Infinity;

    // String comparison for ticker
    if (typeof aVal === "string") {
      return currentSortDirection === "asc"
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    // Numeric comparison
    return currentSortDirection === "asc" ? aVal - bVal : bVal - aVal;
  });

  renderPortfolioTable(sorted);
}

function renderPortfolioPieChart(positions) {
  const canvas = document.getElementById("portfolio-pie-chart");

  if (!canvas || typeof Chart === "undefined" || !positions || positions.length === 0) {
    return;
  }

  const labels = positions.map(pos => pos.ticker);
  const values = positions.map(pos => pos.market_value !== null ? pos.market_value : 0);

  const colors = [
    "#4e79a7",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#59a14f",
    "#edc948",
    "#b07aa1",
    "#ff9da7"
  ];

  if (portfolioPieChart) {
    portfolioPieChart.data.labels = labels;
    portfolioPieChart.data.datasets[0].data = values;
    portfolioPieChart.update();
    return;
  }

  portfolioPieChart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors
        }
      ]
    },

    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 1
    }

    
  });
}

function loadHistory(history) {
  historyData = history;
  historyCurrentPage = 1;
  renderHistoryPage();

}

function renderHistoryPage() {
  const tbody = document.getElementById("history-body");
  tbody.innerHTML = "";

  if (!historyData.length) {
    tbody.innerHTML = '<tr class="empty-state"><td colspan="6">No transaction history yet.</td></tr>';
    return;
  }

  const start = (historyCurrentPage - 1) * historyRowsPerPage;
  const end = start + historyRowsPerPage;

  const pageData = historyData.slice(start, end);

  pageData.forEach((t) => {
    const row = document.createElement("tr");

    const action = t.action.charAt(0).toUpperCase() + t.action.slice(1);
    const pricePerShare = Number(t.price || 0);
    const quantity = Number(t.quantity || 0);
    const totalValue = quantity * pricePerShare;
    row.innerHTML = `
      <td>${action}</td>
      <td>${t.ticker}</td>
      <td>${quantity}</td>
      <td>$${pricePerShare.toFixed(2)}</td>
      <td>$${totalValue.toFixed(2)}</td>
      <td>${t.transaction_date}</td>
    `;

    tbody.appendChild(row);
  });
    updateHistoryPagination();
  // Store history data with calculated fields for sorting
  historyData = history.map((t) => ({
    ...t,
    price: Number(t.price || 0),
    quantity: Number(t.quantity || 0),
    totalValue: Number(t.quantity || 0) * Number(t.price || 0),
    action: t.action.charAt(0).toUpperCase() + t.action.slice(1),
  }));

  // Apply default sort by date, descending
  sortTransactionTable("transaction_date");
}

function renderTransactionTable(transactions) {
  const tbody = document.getElementById("history-body");
  tbody.innerHTML = "";

  if (!transactions.length) {
    tbody.innerHTML = '<tr class="empty-state"><td colspan="6">No transaction history.</td></tr>';
    return;
  }

  // Paginate the transactions
  const start = (historyCurrentPage - 1) * historyRowsPerPage;
  const end = start + historyRowsPerPage;
  const pageData = transactions.slice(start, end);

  pageData.forEach((t) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${t.action}</td>
      <td>${t.ticker}</td>
      <td>${t.quantity}</td>
      <td>$${t.price.toFixed(2)}</td>
      <td>$${t.totalValue.toFixed(2)}</td>
      <td>${t.transaction_date}</td>
    `;
    tbody.appendChild(row);
  });

  updateHistoryPagination(transactions.length);
}

function updateHistoryPagination(totalItems) {
  const pageNumber = document.getElementById("history-page-number");
  const prevButton = document.getElementById("history-prev-btn");
  const nextButton = document.getElementById("history-next-btn");

  const totalPages = Math.ceil(totalItems / historyRowsPerPage);

  if (pageNumber) {
    pageNumber.textContent = `Page ${historyCurrentPage} of ${totalPages}`;
  }

  if (prevButton) {
    prevButton.disabled = historyCurrentPage === 1;
  }

  if (nextButton) {
    nextButton.disabled = historyCurrentPage === totalPages;
  }
}

function sortTransactionTable(column) {
  if (currentHistorySortColumn === column) {
    currentHistorySortDirection = currentHistorySortDirection === "asc" ? "desc" : "asc";
  } else {
    currentHistorySortColumn = column;
    // Keep default desc direction for date column, asc for others
    currentHistorySortDirection = column === "transaction_date" ? "desc" : "asc";
  }

  // Reset to first page when sorting
  historyCurrentPage = 1;

  // Update header indicators in history table
  const historyBody = document.getElementById("history-body");
  const historyTable = historyBody?.closest("table");
  if (historyTable) {
    historyTable.querySelectorAll("th.sortable").forEach(th => {
      th.classList.remove("asc", "desc");
      if (th.dataset.sort === column) {
        th.classList.add(currentHistorySortDirection);
      }
    });
  }

  // Sort data
  sortedHistoryData = [...historyData].sort((a, b) => {
    let aVal = a[column];
    let bVal = b[column];

    // Handle null values
    if (aVal === null) aVal = -Infinity;
    if (bVal === null) bVal = -Infinity;

    // String comparison
    if (typeof aVal === "string") {
      return currentHistorySortDirection === "asc"
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    // Numeric comparison
    return currentHistorySortDirection === "asc" ? aVal - bVal : bVal - aVal;
  });

  renderTransactionTable(sortedHistoryData);
}

function populateSellDropdown(holdings) {
  const sellSelect = document.getElementById("sell-ticker");
  sellSelect.innerHTML = '<option value="">Select a stock to sell...</option>';

  // Consolidate holdings by ticker and store available quantities
  const consolidatedMap = {};
  availableQuantities = {}; // Reset available quantities

  holdings.forEach((h) => {
    if (!consolidatedMap[h.ticker]) {
      consolidatedMap[h.ticker] = {
        ticker: h.ticker,
        totalQuantity: 0,
        firstId: h.id
      };
    }
    consolidatedMap[h.ticker].totalQuantity += Number(h.quantity || 0);
  });

  // Store available quantities and populate dropdown
  Object.values(consolidatedMap).forEach((consolidated) => {
    availableQuantities[consolidated.ticker] = consolidated.totalQuantity;
    const option = document.createElement("option");
    option.value = consolidated.firstId;
    option.textContent = `${consolidated.ticker} (${consolidated.totalQuantity} shares)`;
    option.dataset.ticker = consolidated.ticker;
    option.dataset.availableQuantity = consolidated.totalQuantity;
    sellSelect.appendChild(option);
  });
}

function getPortfolioAvgPrice(ticker, holdings = holdingsData) {
  const matchingHoldings = holdings.filter((holding) => holding.ticker === ticker);
  if (!matchingHoldings.length) {
    return 0;
  }

  const totalQuantity = matchingHoldings.reduce((sum, holding) => sum + Number(holding.quantity || 0), 0);
  const weightedCost = matchingHoldings.reduce(
    (sum, holding) => sum + Number(holding.quantity || 0) * Number(holding.purchase_price || 0),
    0,
  );

  return totalQuantity ? weightedCost / totalQuantity : 0;
}

function clearSellDetails() {
  const sellQuantityEl = document.getElementById("sell-quantity");
  const sellPriceEl = document.getElementById("sell-price");

  if (sellQuantityEl) sellQuantityEl.textContent = "-";
  if (sellPriceEl) sellPriceEl.textContent = "-";
}

document.getElementById("sell-ticker").addEventListener("change", async (e) => {
  const holdingId = e.target.value;

  if (!holdingId) {
    clearSellDetails();
    document.getElementById("sell-quantity-input").value = "";
    return;
  }

  const selectedOption = e.target.options[e.target.selectedIndex];
  const ticker = selectedOption.dataset.ticker;
  const totalQuantity = availableQuantities[ticker] || 0;

  const sellQuantityEl = document.getElementById("sell-quantity");
  if (sellQuantityEl) sellQuantityEl.textContent = totalQuantity;

  document.getElementById("sell-quantity-input").value = "";

  const averagePrice = getPortfolioAvgPrice(holding.ticker, holdingsData);
  document.getElementById("sell-price").textContent = `$${averagePrice.toFixed(2)}`;
});

const tickerSelect = document.getElementById("ticker");
if (tickerSelect) {
  tickerSelect.addEventListener("change", async (e) => {
    const ticker = e.target.value.trim();
    await fetchAndDisplayPrice(ticker);
  });
}

const holdingForm = document.getElementById("holding-form");
if (holdingForm) {
  holdingForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const ticker = document.getElementById("ticker")?.value?.trim();
    const quantity = parseFloat(document.getElementById("quantity")?.value || "");
    let purchasePrice = getDisplayedPurchasePrice();
    const purchaseDate = getTodayDate();

    // Validate quantity
    if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isInteger(quantity)) {
      alert("Quantity must be a whole number (1, 2, 3, ...)");
      return;
    }

    if (!ticker || !Number.isFinite(purchasePrice)) {
      if (ticker) {
        purchasePrice = await fetchAndDisplayPrice(ticker);
      }
    }

    if (!ticker || !Number.isFinite(purchasePrice)) {
      return;
    }

    try {
      await buyStock(ticker, quantity, purchasePrice, purchaseDate);
      e.target.reset();
      const purchasePriceEl = document.getElementById("purchase_price");
      if (purchasePriceEl) purchasePriceEl.textContent = "-";
      resetHistoryFilter();
      await loadPortfolio();
    } catch (err) {
      console.error("Buy failed:", err);
      alert(err.message);
    }
  });
}

document.getElementById("sell-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const holdingId = document.getElementById("sell-ticker").value;
  const selectedOption = document.querySelector(`#sell-ticker option[value="${holdingId}"]`);
  const ticker = selectedOption?.dataset.ticker;
  const quantity = parseFloat(document.getElementById("sell-quantity-input").value);
  const sellDate = getTodayDate();

  if (!holdingId) {
    alert("Please select a stock to sell");
    return;
  }

  if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isInteger(quantity)) {
    alert("Quantity must be a whole number (1, 2, 3, ...)");
    return;
  }

  // Use the stored available quantity from dropdown
  const availableQuantity = availableQuantities[ticker] || 0;
  if (quantity > availableQuantity) {
    alert(`Cannot sell ${quantity} shares. Only ${availableQuantity} shares available.`);
    return;
  }

  const url = new URL(`${API_BASE}/holdings/${holdingId}`, window.location.origin);
  url.searchParams.append("quantity", quantity);
  if (sellDate) url.searchParams.append("sell_date", sellDate);

  await fetch(url, { method: "DELETE" });

  e.target.reset();
  resetHistoryFilter();
  loadPortfolio();
});

const refreshButton = document.getElementById("refresh-data-btn");
if (refreshButton) {
  refreshButton.addEventListener("click", () => loadPortfolio());
}

const historyFilterForm = document.getElementById("history-filter-form");
if (historyFilterForm) {
  historyFilterForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const filters = {};
    const action = document.getElementById("history-filter-action")?.value?.trim();
    const ticker = document.getElementById("history-filter-ticker")?.value?.trim();
    const quantityOperator = document.getElementById("history-filter-quantity-operator")?.value;
    const quantityValue = document.getElementById("history-filter-quantity")?.value?.trim();
    const priceOperator = document.getElementById("history-filter-price-operator")?.value;
    const priceValue = document.getElementById("history-filter-price")?.value?.trim();
    const priceRange = document.getElementById("history-filter-price-range")?.value;
    const year = document.getElementById("history-filter-year")?.value?.trim();
    const dateValue = document.getElementById("history-filter-date")?.value?.trim();

    if (action) filters.action = action;
    if (ticker) filters.ticker = ticker;
    if (quantityOperator && quantityValue) filters.quantity = `${quantityOperator}${quantityValue}`;
    if (priceOperator && priceValue) {
      const normalizedPrice = Number(priceValue).toString();
      filters.price = `${priceOperator}${normalizedPrice}`;
    }
    if (priceRange) filters.price_range = priceRange;
    if (year) filters.year = year;
    if (dateValue) filters.date = dateValue;

    if (Object.keys(filters).length === 0) {
      await loadPortfolio();
      return;
    }

    await loadPortfolio(filters);
  });
}

const clearFilterButton = document.getElementById("clear-filter-btn");
if (clearFilterButton) {
  clearFilterButton.addEventListener("click", async () => {
    resetHistoryFilter();
    await loadPortfolio();
  });
}

function getDateRangeForPeriod(period) {
  const end = new Date();
  const start = new Date();

  const formatDate = (date) => date.toISOString().split("T")[0];

  switch (period) {
    case "1m":
      start.setMonth(start.getMonth() - 1);
      break;
    case "3m":
      start.setMonth(start.getMonth() - 3);
      break;
    case "6m":
      start.setMonth(start.getMonth() - 6);
      break;
    case "1y":
      start.setFullYear(start.getFullYear() - 1);
      break;
    case "ytd":
      start.setFullYear(end.getFullYear(), 0, 1);
      break;
    case "5y":
      start.setFullYear(start.getFullYear() - 5);
      break;
    case "10y":
      start.setFullYear(start.getFullYear() - 10);
      break;
    case "all":
      start.setFullYear(1900);
      break;
  }

  return { start: formatDate(start), end: formatDate(end) };
}

async function loadPerformanceChart(startDate, endDate) {
  try {
    const params = new URLSearchParams();
    if (startDate) params.append("start", startDate);
    if (endDate) params.append("end", endDate);

    const url = `${API_BASE}/performance${params.toString() ? `?${params.toString()}` : ""}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load performance");
    const data = await res.json();

    const dates = data.map(d => d.date);
    const values = data.map(d => d.value);

    const canvas = document.getElementById("performance-chart");
    if (!canvas || typeof Chart === "undefined") return;

    if (performanceChart) {
      performanceChart.data.labels = dates;
      performanceChart.data.datasets[0].data = values;
      performanceChart.options.plugins.tooltip.callbacks.label = (context) =>
        `Portfolio Value: $${context.parsed.y.toFixed(2)}`;
      performanceChart.update();
      return;
    }

    let hoveredX = null;

    const verticalLinePlugin = {
      id: "verticalLine",
      afterDatasetsDraw(chart) {
        if (hoveredX !== null) {
          const ctx = chart.ctx;
          const yTop = chart.chartArea.top;
          const yBottom = chart.chartArea.bottom;

          ctx.save();
          ctx.strokeStyle = "#4e79a7";
          ctx.lineWidth = 2;
          ctx.setLineDash([5, 5]);
          ctx.beginPath();
          ctx.moveTo(hoveredX, yTop);
          ctx.lineTo(hoveredX, yBottom);
          ctx.stroke();
          ctx.restore();
        }
      }
    };

    canvas.addEventListener("mousemove", (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      if (
        x >= performanceChart.chartArea.left &&
        x <= performanceChart.chartArea.right &&
        y >= performanceChart.chartArea.top &&
        y <= performanceChart.chartArea.bottom
      ) {
        hoveredX = x;
        performanceChart.draw();
      }
    });

    canvas.addEventListener("mouseleave", () => {
      hoveredX = null;
      performanceChart.draw();
    });

    performanceChart = new Chart(canvas, {
      type: "line",
      data: {
        labels: dates,
        datasets: [
          {
            label: "Portfolio Value",
            data: values,
            borderColor: "#4e79a7",
            backgroundColor: "rgba(78, 121, 167, 0.1)",
            borderWidth: 2,
            fill: true,
            pointRadius: 0,
            pointBackgroundColor: "#4e79a7",
            pointBorderColor: "#fff",
            pointBorderWidth: 2,
            pointHoverRadius: 6,
            tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: {
          mode: "index",
          intersect: false
        },
        plugins: {
          legend: {
            display: true,
            position: "top"
          },
          tooltip: {
            enabled: true,
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            padding: 12,
            titleFont: { size: 14, weight: "bold" },
            bodyFont: { size: 13 },
            borderColor: "#4e79a7",
            borderWidth: 1,
            callbacks: {
              label: (context) => `Portfolio Value: $${context.parsed.y.toFixed(2)}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => `$${value.toFixed(0)}`
            }
          }
        }
      },
      plugins: [verticalLinePlugin]
    });
  } catch (err) {
    console.error("Error loading performance chart:", err);
  }
}

function setDefaultPerformanceDates() {
  const endDateInput = document.getElementById("perf-end-date");
  const startDateInput = document.getElementById("perf-start-date");

  const today = new Date();
  const endDate = new Date(today);
  const startDate = new Date(today);
  startDate.setDate(startDate.getDate() - 90);

  const formatDate = (date) => date.toISOString().split("T")[0];

  if (endDateInput) endDateInput.value = formatDate(endDate);
  if (startDateInput) startDateInput.value = formatDate(startDate);
}

const perfLoadBtn = document.getElementById("perf-load-btn");
if (perfLoadBtn) {
  perfLoadBtn.addEventListener("click", async () => {
    const startDate = document.getElementById("perf-start-date").value;
    const endDate = document.getElementById("perf-end-date").value;
    await loadPerformanceChart(startDate, endDate);
  });
}

document.querySelectorAll(".perf-period-btn").forEach(btn => {
  btn.addEventListener("click", async (e) => {
    const period = e.target.dataset.period;
    const { start, end } = getDateRangeForPeriod(period);
    document.getElementById("perf-start-date").value = start;
    document.getElementById("perf-end-date").value = end;
    await loadPerformanceChart(start, end);
  });
});

// Add sortable header click handlers
document.querySelectorAll("th.sortable").forEach(th => {
  th.addEventListener("click", () => {
    const column = th.dataset.sort;
    const table = th.closest("table");
    const historyBody = table?.querySelector("#history-body");

    if (historyBody) {
      sortTransactionTable(column);
    } else {
      sortPortfolioTable(column);
    }
  });
});

// Handle date and load data as soon as the page is ready
window.addEventListener("DOMContentLoaded", () => {
  const currentDateEl = document.getElementById("current-date");
  if (currentDateEl) {
    currentDateEl.textContent = getTodayDate();
  }
  setDefaultPerformanceDates();
  const startDate = document.getElementById("perf-start-date").value;
  const endDate = document.getElementById("perf-end-date").value;
  loadPerformanceChart(startDate, endDate);

  const prevButton = document.getElementById("history-prev-btn");
  const nextButton = document.getElementById("history-next-btn");

  if (prevButton) {
    prevButton.addEventListener("click", () => {
      if (historyCurrentPage > 1) {
        historyCurrentPage--;
        renderTransactionTable(sortedHistoryData);
      }
    });
  }

  if (nextButton) {
    nextButton.addEventListener("click", () => {
      const totalPages = Math.ceil(sortedHistoryData.length / historyRowsPerPage);

      if (historyCurrentPage < totalPages) {
        historyCurrentPage++;
        renderTransactionTable(sortedHistoryData);
      }
    });
  }
  let refreshing = false;

  async function refreshPortfolio() {
    if (refreshing) return;

    refreshing = true;

    try {
      await loadPortfolio();
    } finally {
      refreshing = false;
    }
}

loadPortfolio(); // Initial load
setInterval(refreshPortfolio, 60000);
});

function renderPnLBarChart(positions) {
  const canvas = document.getElementById("pnl-bar-chart");
  if (!canvas || typeof Chart === "undefined") return;

  const labels = positions.map(p => p.ticker);
  const values = positions.map(p =>
  (p.realized_pnl ?? 0) + (p.unrealized_pnl ?? 0)
);

  const colors = values.map(v =>
    v >= 0 ? "#2ecc71" : "#e74c3c"
  );

  if (pnlBarChart) {
    pnlBarChart.destroy();
  }

  pnlBarChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Profit / Loss",
        data: values,
        backgroundColor: colors
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        x: {
          ticks: {
            callback: value => "$" + value
          }
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', function () {
  const toggleBtn = document.getElementById('filter-toggle-btn');
  const filterPanel = document.getElementById('filter-options-panel');

  toggleBtn.addEventListener('click', function () {
    // Toggles the visibility class
    filterPanel.classList.toggle('d-none');
  });
});
