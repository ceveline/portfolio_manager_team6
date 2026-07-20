const API_BASE = "/api";
let holdingsData = [];

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

function loadConsolidated(consolidated) {
  const tbody = document.getElementById("consolidated-body");
  tbody.innerHTML = "";

  let totalValue = 0;
  let totalShares = 0;

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
  document.getElementById("sell-quantity").textContent = "-";
  document.getElementById("sell-price").textContent = "-";
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

  document.getElementById("sell-quantity").textContent = holding.quantity;
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
    }
  } catch (err) {
    console.error("Error fetching price:", err);
    priceDisplay.textContent = "-";
  }
});

document.getElementById("holding-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const body = {
    ticker: document.getElementById("ticker").value,
    quantity: parseFloat(document.getElementById("quantity").value),
    purchase_price: parseFloat(document.getElementById("purchase_price").textContent.replace("$", "")),
  };

  const purchaseDate = document.getElementById("purchase_date").value;
  if (purchaseDate) body.purchase_date = purchaseDate;

  await fetch(`${API_BASE}/holdings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  e.target.reset();
  document.getElementById("purchase_price").textContent = "-";
  loadPortfolio();
});

document.getElementById("sell-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const holdingId = document.getElementById("sell-ticker").value;
  const quantity = parseFloat(document.getElementById("sell-quantity-input").value);
  const sellDate = document.getElementById("sell_date").value;

  if (!holdingId || !quantity || quantity <= 0) return;

  const url = new URL(`${API_BASE}/holdings/${holdingId}`, window.location.origin);
  url.searchParams.append("quantity", quantity);
  if (sellDate) url.searchParams.append("sell_date", sellDate);

  await fetch(url, { method: "DELETE" });

  e.target.reset();
  loadPortfolio();
});

loadPortfolio();
