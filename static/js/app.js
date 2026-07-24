const API_BASE = "/api";
let holdingsData = [];
let portfolioPieChart = null;

async function loadPortfolio(filters = {}) {
  const holdingsRes = await fetch(`${API_BASE}/holdings`);
  const holdings = await holdingsRes.json();
  holdingsData = holdings;

  const consolidatedRes = await fetch(`${API_BASE}/consolidated`);
  const consolidated = await consolidatedRes.json();

  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      params.append(key, value);
    }
  });

  const historyUrl = `${API_BASE}/transactions${params.toString() ? `?${params.toString()}` : ""}`;
  const historyRes = await fetch(historyUrl);
  const history = await historyRes.json();

  await loadConsolidated(consolidated);
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

async function loadConsolidated(consolidated) {
  const tbody = document.getElementById("consolidated-body");
  tbody.innerHTML = "";

  let totalValue = 0;
  let totalShares = 0;
  let totalCostBasis = 0;
  let totalGainLoss = 0;

  const currentPrices = await Promise.all(
    consolidated.map(async (item) => {
      try {
        const res = await fetch(`${API_BASE}/price/${item.ticker}`);

        if (res.ok) {
          const data = await res.json();
          const priceValue =
            data.price ??
            data.price_data?.close ??
            data.close;

          return Number(priceValue || 0);
        }
      } catch (err) {
        console.error("Error fetching price:", err);
      }

      return null;
    })
  );


  if (!consolidated.length) {
    tbody.innerHTML =
      '<tr class="empty-state"><td colspan="5">No portfolio data yet.</td></tr>';

    document.querySelector("#total-value strong").textContent = "$0.00";
    document.querySelector("#total-shares strong").textContent = "0";
    document.querySelector("#total-holdings strong").textContent = "0";
    document.querySelector("#total-gain-loss strong").textContent =
      "$0.00 (0.00%)";

    return;
  }


  consolidated.forEach((item, index) => {

    const row = document.createElement("tr");

    const avgPrice = Number(item.avg_price || 0);
    const quantity = Number(item.quantity || 0);

    const itemValue = quantity * avgPrice;
    const costBasis = itemValue;

    const currentPrice = currentPrices[index];


    totalValue += itemValue;
    totalShares += quantity;
    totalCostBasis += costBasis;


    let gainLossCell = "-";

    if (currentPrice != null) {

      const gainLoss =
        (currentPrice - avgPrice) * quantity;

      const gainLossPct =
        costBasis ? (gainLoss / costBasis) * 100 : 0;


      totalGainLoss += gainLoss;


      const sign = gainLoss >= 0 ? "+" : "";


      gainLossCell =
        `${sign}$${gainLoss.toFixed(2)}
        (${sign}${gainLossPct.toFixed(2)}%)`;
    }


    row.innerHTML = `
      <td>${item.ticker}</td>
      <td>${quantity}</td>
      <td>$${avgPrice.toFixed(2)}</td>
      <td>$${itemValue.toFixed(2)}</td>
      <td>${gainLossCell}</td>
    `;


    tbody.appendChild(row);

  });


  document.querySelector("#total-value strong").textContent =
    `$${totalValue.toFixed(2)}`;

  document.querySelector("#total-shares strong").textContent =
    totalShares.toFixed(0);

  document.querySelector("#total-holdings strong").textContent =
    consolidated.length;


  const totalGainLossPct =
    totalCostBasis
      ? (totalGainLoss / totalCostBasis) * 100
      : 0;


  const sign =
    totalGainLoss >= 0 ? "+" : "";


  document.querySelector("#total-gain-loss strong").textContent =
    `${sign}$${totalGainLoss.toFixed(2)}
    (${sign}${totalGainLossPct.toFixed(2)}%)`;


  renderPortfolioPieChart(consolidated);
}

function renderPortfolioPieChart(consolidated) {

  const canvas = document.getElementById(
    "portfolio-pie-chart"
  );

  if (!canvas || typeof Chart === "undefined") {
    return;
  }


  const labels = consolidated.map(
    item => item.ticker
  );


  const values = consolidated.map(
    item =>
      Number(item.quantity || 0) *
      Number(item.avg_price || 0)
  );


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
      responsive:true,
      maintainAspectRatio:true,
      aspectRatio:1
    }

  });

}

function loadHistory(history) {
  const tbody = document.getElementById("history-body");
  tbody.innerHTML = "";

  if (!history.length) {
    tbody.innerHTML = '<tr class="empty-state"><td colspan="6">No transaction history yet.</td></tr>';
    return;
  }

  history.forEach((t) => {
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
}

function populateSellDropdown(holdings) {
  const sellSelect = document.getElementById("sell-ticker");
  sellSelect.innerHTML = '<option value="">Select a stock to sell...</option>';

  holdings.forEach((h) => {
    const option = document.createElement("option");
    option.value = h.id;
    option.textContent = `${h.ticker} (${h.quantity} shares)`;
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

  const holding = holdingsData.find(h => h.id == holdingId);
  if (!holding) return;

  const sellQuantityEl = document.getElementById("sell-quantity");
  if (sellQuantityEl) sellQuantityEl.textContent = holding.quantity;

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

    if (!ticker || !quantity || !Number.isFinite(purchasePrice)) {
      if (ticker) {
        purchasePrice = await fetchAndDisplayPrice(ticker);
      }
    }

    if (!ticker || !quantity || !Number.isFinite(purchasePrice)) {
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
  const quantity = parseFloat(document.getElementById("sell-quantity-input").value);
  const sellDate = getTodayDate();

  if (!holdingId || !quantity || quantity <= 0) return;

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

// Handle date and load data as soon as the page is ready
window.addEventListener("DOMContentLoaded", () => {
  const currentDateEl = document.getElementById("current-date");
  if (currentDateEl) {
    currentDateEl.textContent = getTodayDate();
  }
  loadPortfolio();
});
