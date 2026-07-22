const API_BASE = "/api";
let holdingsData = [];
let portfolioPieChart = null;

async function loadPortfolio() {
  const holdingsRes = await fetch(`${API_BASE}/holdings`);
  const holdings = await holdingsRes.json();
  holdingsData = holdings;

  const consolidatedRes = await fetch(`${API_BASE}/consolidated`);
  const consolidated = await consolidatedRes.json();

  const historyRes = await fetch(`${API_BASE}/transactions`);
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
          return data.price;
        }
      } catch (err) {
        console.error("Error fetching price:", err);
      }
      return null;
    })
  );

  consolidated.forEach((item, i) => {
    const row = document.createElement("tr");
    const itemValue = item.quantity * item.avg_price;
    totalValue += itemValue;
    totalShares += item.quantity;

    const currentPrice = currentPrices[i];
    const costBasis = item.quantity * item.avg_price;
    totalCostBasis += costBasis;

    let gainLossCell = "-";
    if (currentPrice != null) {
      const gainLoss = (currentPrice - item.avg_price) * item.quantity;
      const gainLossPct = (gainLoss / costBasis) * 100;
      totalGainLoss += gainLoss;
      const sign = gainLoss >= 0 ? "+" : "";
      gainLossCell = `${sign}$${gainLoss.toFixed(2)} (${sign}${gainLossPct.toFixed(2)}%)`;
    }

    row.innerHTML = `
      <td>${item.ticker}</td>
      <td>${item.quantity}</td>
      <td>$${item.avg_price.toFixed(2)}</td>
      <td>${gainLossCell}</td>
    `;
    tbody.appendChild(row);
  });

  document.querySelector("#total-value strong").textContent = `$${totalValue.toFixed(2)}`;
  document.querySelector("#total-shares strong").textContent = totalShares.toFixed(0);
  document.querySelector("#total-holdings strong").textContent = consolidated.length;

  const totalGainLossPct = totalCostBasis ? (totalGainLoss / totalCostBasis) * 100 : 0;
  const totalSign = totalGainLoss >= 0 ? "+" : "";
  document.querySelector("#total-gain-loss strong").textContent =
    `${totalSign}$${totalGainLoss.toFixed(2)} (${totalSign}${totalGainLossPct.toFixed(2)}%)`;

  renderPortfolioPieChart(consolidated);
}

function renderPortfolioPieChart(consolidated) {
  const canvas = document.getElementById("portfolio-pie-chart");
  if (!canvas) return;

  const labels = consolidated.map((item) => item.ticker);
  const values = consolidated.map((item) => item.quantity * item.avg_price);
  const colors = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
    "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
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
      datasets: [{ data: values, backgroundColor: colors }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 1,
    },
  });
}

function loadHistory(history) {
  const tbody = document.getElementById("history-body");
  tbody.innerHTML = "";

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

  try {
    const res = await fetch(`${API_BASE}/price/${holding.ticker}`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById("sell-price").textContent = `$${data.price.toFixed(2)}`;
    }
  } catch (err) {
    console.error("Error fetching price:", err);
    document.getElementById("sell-price").textContent = "-";
  }
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
    } else {
      priceDisplay.textContent = "Unavailable";
      alert(`Could not fetch a price for ${ticker}. Please try again.`);
    }
  } catch (err) {
    console.error("Error fetching price:", err);
    priceDisplay.textContent = "Unavailable";
    alert(`Could not fetch a price for ${ticker}. Please try again.`);
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
  loadPortfolio();
});

document.getElementById("refresh-data-btn").addEventListener("click", loadPortfolio);


//Handle date
document.getElementById("current-date").textContent = getTodayDate();
loadPortfolio();
