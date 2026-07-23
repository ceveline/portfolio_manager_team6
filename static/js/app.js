const API_BASE = "/api";
let holdingsData = [];

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

  loadConsolidated(consolidated);
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
  document.getElementById("history-filter-action").value = "";
  document.getElementById("history-filter-ticker").value = "";
  document.getElementById("history-filter-quantity-operator").value = "";
  document.getElementById("history-filter-quantity").value = "";
  document.getElementById("history-filter-price-operator").value = "";
  document.getElementById("history-filter-price").value = "";
  document.getElementById("history-filter-price-range").value = "";
  document.getElementById("history-filter-year").value = "";
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

function loadConsolidated(consolidated) {
  const tbody = document.getElementById("consolidated-body");
  tbody.innerHTML = "";

  let totalValue = 0;
  let totalShares = 0;

  if (!consolidated.length) {
    tbody.innerHTML = '<tr class="empty-state"><td colspan="3">No portfolio data yet.</td></tr>';
    document.querySelector("#total-value strong").textContent = "$0.00";
    document.querySelector("#total-shares strong").textContent = "0";
    return;
  }

  consolidated.forEach((item) => {
    const row = document.createElement("tr");
    const itemValue = item.quantity * item.avg_price;
    totalValue += itemValue;
    totalShares += item.quantity;

    row.innerHTML = `
      <td>${item.ticker}</td>
      <td>${item.quantity}</td>
      <td>$${item.avg_price.toFixed(2)}</td>
    `;
    tbody.appendChild(row);
  });

  document.querySelector("#total-value strong").textContent = `$${totalValue.toFixed(2)}`;
  document.querySelector("#total-shares strong").textContent = totalShares.toFixed(0);
}

function loadHistory(history) {
  const tbody = document.getElementById("history-body");
  tbody.innerHTML = "";

  if (!history.length) {
    tbody.innerHTML = '<tr class="empty-state"><td colspan="5">No transaction history yet.</td></tr>';
    return;
  }

  history.forEach((t) => {
    const row = document.createElement("tr");
    const action = t.action.charAt(0).toUpperCase() + t.action.slice(1);
    row.innerHTML = `
      <td>${action}</td>
      <td>${t.ticker}</td>
      <td>${t.quantity}</td>
      <td>$${t.price.toFixed(2)}</td>
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

document.getElementById("ticker").addEventListener("change", async (e) => {
  const ticker = e.target.value.trim();
  const priceDisplay = document.getElementById("purchase_price");

  if (!ticker) {
    priceDisplay.textContent = "-";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/price/${ticker}`);
    if (res.ok) {
      const data = await res.json();
      priceDisplay.textContent = `$${data.price.toFixed(2)}`;
    }
  } catch (err) {
    console.error("Error fetching price:", err);
    priceDisplay.textContent = "-";
  }
});

document.getElementById("holding-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const ticker = document.getElementById("ticker").value;
  const quantity = parseFloat(document.getElementById("quantity").value);
  const purchasePrice = parseFloat(document.getElementById("purchase_price").textContent.replace("$", ""));
  const purchaseDate = getTodayDate();

  if (!ticker || !quantity || !purchasePrice) {
    return;
  }

  try {
    await buyStock(ticker, quantity, purchasePrice, purchaseDate);
    e.target.reset();
    document.getElementById("purchase_price").textContent = "-";
    resetHistoryFilter();
    await loadPortfolio();
  } catch (err) {
    console.error("Buy failed:", err);
    alert(err.message);
  }
});

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

document.getElementById("refresh-data-btn").addEventListener("click", () => loadPortfolio());
document.getElementById("history-filter-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const filters = {};
  const action = document.getElementById("history-filter-action").value.trim();
  const ticker = document.getElementById("history-filter-ticker").value.trim();
  const quantityOperator = document.getElementById("history-filter-quantity-operator").value;
  const quantityValue = document.getElementById("history-filter-quantity").value.trim();
  const priceOperator = document.getElementById("history-filter-price-operator").value;
  const priceValue = document.getElementById("history-filter-price").value.trim();
  const priceRange = document.getElementById("history-filter-price-range").value;
  const year = document.getElementById("history-filter-year").value.trim();

  if (action) filters.action = action;
  if (ticker) filters.ticker = ticker;
  if (quantityOperator && quantityValue) filters.quantity = `${quantityOperator}${quantityValue}`;
  if (priceOperator && priceValue) {
    const normalizedPrice = Number(priceValue).toString();
    filters.price = `${priceOperator}${normalizedPrice}`;
  }
  if (priceRange) filters.price_range = priceRange;
  if (year) filters.year = year;

  if (Object.keys(filters).length === 0) {
    await loadPortfolio();
    return;
  }

  await loadPortfolio(filters);
});

document.getElementById("clear-filter-btn").addEventListener("click", async () => {
  resetHistoryFilter();
  await loadPortfolio();
});

// Handle date and load data as soon as the page is ready
window.addEventListener("DOMContentLoaded", () => {
  const currentDateEl = document.getElementById("current-date");
  if (currentDateEl) {
    currentDateEl.textContent = getTodayDate();
  }
  loadPortfolio();
});
