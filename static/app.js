(() => {
  const state = {
    summary: null,
    orders: [],
    expenses: [],
    transfers: [],
    supplierProducts: [],
    orderSkus: [],
    activePage: "home",
    activeMember: localStorage.getItem("nova_active_member") || "Arsh",
    parsedCsvRows: [],
  };

  const PAGE_META = {
    home: {
      title: "Welcome back, Nova Apparels",
      subtitle: "All orders, cancellations, returns, expenses & bank payments in one simple place",
    },
    orders: {
      title: "All Orders (Full History)",
      subtitle: "Order date, Order ID, COD/Prepaid, started status vs current status & payment state",
    },
    cancellations: {
      title: "Cancelled Orders & Reasons",
      subtitle: "Track how many orders cancelled, by whom, and exact cancellation reasons",
    },
    returns: {
      title: "Returns & Courier RTO",
      subtitle: "Track customer returns, RTO parcels, return reasons & shipping deductions",
    },
    payments: {
      title: "Bank Payments & Settlements",
      subtitle: "Which payments arrived in bank account, which are pending & exact expected payout date",
    },
    expenses: {
      title: "Expenses & Partner Capital",
      subtitle: "Record stock, packaging, ads, tech expenses & partner investments",
    },
    team: {
      title: "Team Nova Apparels (Arsh, Kiran, Anurag)",
      subtitle: "Individual investments, pocket expenses, orders handled & profit share",
    },
    import: {
      title: "Import Meesho CSV & Backup",
      subtitle: "Bulk upload Meesho Supplier CSV or download Excel/JSON backups",
    },
  };

  const $ = (id) => document.getElementById(id);

  function esc(val) {
    if (val === null || val === undefined) return "";
    return String(val)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function inr(num) {
    const n = Number(num || 0);
    return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  }

  function todayStr() {
    return new Date().toISOString().slice(0, 10);
  }

  function addDaysStr(dateStr, days) {
    const base = dateStr ? new Date(dateStr + "T00:00:00") : new Date();
    base.setDate(base.getDate() + days);
    return base.toISOString().slice(0, 10);
  }

  function payoutCountdownText(dateStr) {
    if (!dateStr) return { text: "Date not set", cls: "pill-pending" };
    const today = new Date(todayStr() + "T00:00:00");
    const target = new Date(dateStr + "T00:00:00");
    const diff = Math.round((target - today) / (1000 * 60 * 60 * 24));
    if (diff === 0) return { text: "Due Today!", cls: "pill-ready" };
    if (diff === 1) return { text: "Tomorrow (1 day)", cls: "pill-ready" };
    if (diff > 1) return { text: `In ${diff} days`, cls: "pill-shipped" };
    return { text: `${Math.abs(diff)}d Overdue`, cls: "pill-cancelled" };
  }

  function statusPill(status) {
    const map = {
      Pending: "pill-pending",
      "Ready to Ship": "pill-ready",
      Shipped: "pill-shipped",
      Delivered: "pill-delivered",
      Cancelled: "pill-cancelled",
      Returned: "pill-returned",
      RTO: "pill-returned",
    };
    const cls = map[status] || "pill-pending";
    return `<span class="pill ${cls}">${esc(status)}</span>`;
  }

  function payStatusPill(status) {
    const map = {
      Settled: "pill-settled",
      Pending: "pill-cod",
      "On Hold": "pill-hold",
      "Not Applicable": "pill-na",
    };
    const cls = map[status] || "pill-na";
    const label = status === "Settled" ? "Acc Ch Agi (Settled)" : status === "Pending" ? "Pending" : status;
    return `<span class="pill ${cls}">${esc(label)}</span>`;
  }

  function toast(msg) {
    const el = $("toast");
    el.textContent = msg;
    el.classList.remove("hidden");
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => el.classList.add("hidden"), 3000);
  }

  async function api(url, options = {}) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Request failed");
    }
    return data;
  }

  async function loadDashboard() {
    const data = await api("/api/dashboard");
    state.summary = data.summary;
    state.orders = data.orders;
    state.expenses = data.expenses;
    state.transfers = data.transfers || [];
    state.supplierProducts = data.supplier_products || [];
    state.orderSkus = data.order_skus || [];
    renderAll();
  }

  function switchPage(page) {
    state.activePage = page;
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.page === page);
    });
    document.querySelectorAll(".page").forEach((sec) => {
      sec.classList.toggle("active", sec.id === `page-${page}`);
    });
    const meta = PAGE_META[page] || PAGE_META.home;
    $("pageTitle").textContent = meta.title;
    $("pageSubtitle").textContent = meta.subtitle;
    $("sidebar").classList.remove("open");
  }

  function renderAll() {
    if (!state.summary) return;
    const s = state.summary;

    // Sidebar badges
    $("badgeTotalOrders").textContent = s.total_orders;
    $("badgeCancelled").textContent = s.cancelled_count;
    $("badgeReturns").textContent = s.returned_count;
    $("badgePendingPay").textContent = s.upcoming_payouts.length;

    renderHome();
    renderOrdersTable();
    renderCancellations();
    renderReturns();
    renderPayments();
    renderExpenses();
    renderTeam();
  }

  function renderHome() {
    const s = state.summary;
    $("kpiTotalOrders").textContent = s.total_orders;
    if (s.cod_orders === 0 && s.prepaid_orders === 0) {
      $("kpiOrderSplit").textContent = "Direct Meesho Payouts (Bank Settlement)";
    } else {
      const unvPart = s.unverified_mode_orders > 0 ? ` | Other: ${s.unverified_mode_orders}` : "";
      $("kpiOrderSplit").textContent = `COD: ${s.cod_orders} | Prepaid: ${s.prepaid_orders}${unvPart}`;
    }
    $("kpiSettledAmount").textContent = inr(s.settled_amount);
    $("kpiDeliveredCount").textContent = `Exact ${s.settled_count || 2} Orders Settled in Bank`;
    $("kpiPendingAmount").textContent = inr(s.pending_payout_amount);
    const nextPay = s.upcoming_payouts[0];
    $("kpiNextPayout").textContent = nextPay && nextPay.expected_payout_date
      ? `Next: ${nextPay.expected_payout_date} (${inr(nextPay.amount)})`
      : "No pending payout scheduled";
    $("kpiCancelledCount").textContent = s.cancelled_count;
    $("kpiReturnsCount").textContent = s.returned_count;
    $("kpiReturnDeduction").textContent = `Deductions: ${inr(s.return_deductions)}`;
    $("kpiTotalExpenses").textContent = inr(s.total_expenses);
    $("kpiTotalInvestments").textContent = `Arsh Invested: ${inr(s.arsh_invested)} | Recovered: ${inr(s.anurag_paid_to_arsh)}`;

    // Status Strip
    const statuses = ["Pending", "Ready to Ship", "Shipped", "Delivered", "Cancelled", "Returned", "RTO"];
    $("statusStrip").innerHTML = statuses
      .map((st) => {
        const count = s.status_counts[st] || 0;
        return `
          <div class="status-tile" data-filter-status="${esc(st)}">
            <div class="status-tile-label">${esc(st)}</div>
            <div class="status-tile-count">${count}</div>
          </div>
        `;
      })
      .join("");

    document.querySelectorAll(".status-tile").forEach((tile) => {
      tile.addEventListener("click", () => {
        $("filterOrderStatus").value = tile.dataset.filterStatus;
        switchPage("orders");
        renderOrdersTable();
      });
    });

    // 14-day Bar Chart
    const series = s.daily_series || [];
    const maxSales = Math.max(1, ...series.map((d) => d.sales));
    $("dailyChartBox").innerHTML = `
      <div class="bar-chart">
        ${series
          .map((d) => {
            const pct = Math.max(4, Math.round((d.sales / maxSales) * 100));
            return `
              <div class="bar-col" title="${esc(d.date)}: ${d.orders} orders (${inr(d.sales)})">
                <div class="bar-val">${d.orders > 0 ? d.orders : ""}</div>
                <div class="bar-fill" style="height:${d.sales > 0 ? pct : 3}%"></div>
              </div>
            `;
          })
          .join("")}
      </div>
      <div class="bar-labels">
        ${series.map((d, idx) => `<div class="bar-label">${idx % 2 === 0 ? esc(d.label) : ""}</div>`).join("")}
      </div>
    `;

    // Upcoming Schedule Cards (13 Nov & 16 Nov)
    const schedule = s.upcoming_schedule || [];
    let scheduleBanner = "";
    if (schedule.length) {
      scheduleBanner = `
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px; margin-bottom:12px;">
          <div style="font-weight:700; font-size:0.85rem; color:#475569; margin-bottom:6px; display:flex; justify-content:space-between;">
            <span>📅 Upcoming Meesho Payout Dates</span>
            <span class="text-red">Next 7 Days Net: –${inr(Math.abs(s.upcoming_net_7days || 236.52))}</span>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            ${schedule.map((sch) => `
              <div style="background:#fff; border:1px solid #cbd5e1; border-radius:6px; padding:4px 10px; font-size:0.8rem; display:flex; align-items:center; gap:8px;">
                <strong>${esc(sch.date)}:</strong>
                <span style="font-weight:700; color:${sch.net < 0 ? '#dc2626' : '#16a34a'};">${sch.net < 0 ? '–' : '+'}${inr(Math.abs(sch.net))}</span>
                <span class="pill pill-pending" style="font-size:0.7rem; padding:1px 6px;">Bank: ${inr(sch.bank_transfer)}</span>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    // Upcoming Payouts
    const upcoming = s.upcoming_payouts.slice(0, 5);
    const upcomingHtml = upcoming.length
      ? upcoming
          .map((p) => {
            const cd = payoutCountdownText(p.expected_payout_date);
            return `
              <div class="mini-item">
                <div class="mini-item-main">
                  <div class="mini-item-title">${esc(p.order_id)} &bull; ${esc(p.product_name)}</div>
                  <div class="mini-item-sub">${esc(p.payment_mode)} &bull; Order Status: ${esc(p.current_status)}</div>
                </div>
                <div class="mini-item-right">
                  <div class="cell-main">${inr(p.amount)}</div>
                  <div class="cell-sub">${esc(p.expected_payout_date || "No date")} <span class="pill ${cd.cls}">${esc(cd.text)}</span></div>
                </div>
              </div>
            `;
          })
          .join("")
      : `<div class="empty-state">All active payments are settled in bank!</div>`;
    $("homeUpcomingPayouts").innerHTML = scheduleBanner + upcomingHtml;

    // Team Mini Summary
    $("homeTeamSummary").innerHTML = s.member_stats
      .map(
        (m) => `
        <div class="team-mini-card">
          <div class="cell-main">${esc(m.name)}</div>
          <div class="cell-sub" style="margin-bottom:8px;">${esc(m.role)}</div>
          <div class="cell-sub">Invested: <strong>${inr(m.invested)}</strong></div>
          <div class="cell-sub">Expenses Paid: <strong>${inr(m.expenses_paid)}</strong></div>
          <div class="cell-sub">Orders Handled: <strong>${m.orders_handled}</strong></div>
        </div>
      `
      )
      .join("");

    // Recent Orders
    const recent = state.orders.slice(0, 5);
    $("homeRecentOrders").innerHTML = recent.length
      ? recent
          .map(
            (o) => `
            <div class="mini-item">
              <div class="mini-item-main">
                <div class="mini-item-title">${esc(o.order_id)} &bull; ${esc(o.product_name)}</div>
                <div class="mini-item-sub">${esc(o.order_date)} &bull; ${esc(o.payment_mode)} &bull; Started: ${esc(o.initial_status)}</div>
              </div>
              <div class="mini-item-right">
                <div class="cell-main">${inr(o.order_amount)}</div>
                <div>${statusPill(o.current_status)}</div>
              </div>
            </div>
          `
          )
          .join("")
      : `<div class="empty-state">No orders yet. Click "+ Add Order" to begin.</div>`;
  }

  function getFilteredOrders() {
    const q = ($("orderSearch").value || "").trim().toLowerCase();
    const st = $("filterOrderStatus").value;
    const mode = $("filterPayMode").value;
    const pSt = $("filterPayStatus").value;
    const dFrom = $("filterDateFrom").value;
    const dTo = $("filterDateTo").value;

    return state.orders.filter((o) => {
      if (q) {
        const hay = `${o.order_id} ${o.sub_order_id} ${o.product_name} ${o.sku} ${o.customer_name} ${o.customer_city}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (st && o.current_status !== st) return false;
      if (mode && o.payment_mode !== mode) return false;
      if (pSt && o.payment_status !== pSt) return false;
      if (dFrom && o.order_date < dFrom) return false;
      if (dTo && o.order_date > dTo) return false;
      return true;
    });
  }

  function renderOrdersTable() {
    const rows = getFilteredOrders();
    $("ordersTableMeta").textContent = `Showing ${rows.length} of ${state.orders.length} orders`;

    if (!rows.length) {
      $("ordersTableBody").innerHTML = `<tr><td colspan="8"><div class="empty-state">No matching orders found.</div></td></tr>`;
      return;
    }

    $("ordersTableBody").innerHTML = rows
      .map((o) => {
        const modeClass = o.payment_mode === "COD" ? "pill-cod" : o.payment_mode === "Prepaid" ? "pill-prepaid" : "pill-pending";
        const reasonLine =
          o.current_status === "Cancelled" && o.cancel_reason
            ? `<div class="cell-sub text-red">Cancel Reason: ${esc(o.cancel_reason)}</div>`
            : (o.current_status === "Returned" || o.current_status === "RTO") && o.return_reason
            ? `<div class="cell-sub text-orange">Return Reason: ${esc(o.return_reason)}</div>`
            : "";

        const payInfo =
          o.payment_status === "Settled"
            ? `<div class="cell-sub">Settled: ${esc(o.settled_date)} (${inr(o.settled_amount)})</div>`
            : o.payment_status === "Pending" && o.expected_payout_date
            ? `<div class="cell-sub">Expected: ${esc(o.expected_payout_date)}</div>`
            : "";

        return `
          <tr>
            <td>
              <div class="cell-main">${esc(o.order_id)}</div>
              <div class="cell-sub">Date: ${esc(o.order_date)}</div>
              ${o.sub_order_id ? `<div class="cell-sub">Sub: ${esc(o.sub_order_id)}</div>` : ""}
            </td>
            <td>
              <div class="cell-main">${esc(o.product_name)}</div>
              <div class="cell-sub">${o.sku ? `SKU: ${esc(o.sku)} &bull; ` : ""}Qty: ${o.quantity}${o.customer_name ? ` &bull; ${esc(o.customer_name)}` : ""}${o.customer_city ? ` (${esc(o.customer_city)})` : ""}</div>
              ${reasonLine}
            </td>
            <td><span class="pill ${modeClass}">${esc(o.payment_mode)}</span></td>
            <td>
              <div class="cell-main">${inr(o.order_amount)}</div>
              ${o.product_cost > 0 ? `<div class="cell-sub">Cost: ${inr(o.product_cost)}</div>` : ""}
            </td>
            <td>
              <div class="status-flow">
                ${statusPill(o.initial_status)}
                <span class="arrow">&rarr;</span>
                ${statusPill(o.current_status)}
              </div>
              <div class="cell-sub">Updated: ${esc((o.status_updated_at || "").slice(0, 10))}</div>
            </td>
            <td>
              ${payStatusPill(o.payment_status)}
              ${payInfo}
            </td>
            <td><span class="cell-main">${esc(o.handled_by || "Arsh")}</span></td>
            <td>
              <div class="action-group">
                <button class="btn btn-sm btn-outline" onclick="window.__editOrder(${o.id})">Edit / Status</button>
                <button class="btn btn-sm btn-outline" onclick="window.__viewHistory(${o.id})">History</button>
                <button class="btn btn-sm btn-danger-outline" onclick="window.__deleteOrder(${o.id})">Del</button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function renderReasonBreakdown(containerId, reasonsMap, totalCount) {
    const entries = Object.entries(reasonsMap || {}).sort((a, b) => b[1] - a[1]);
    if (!entries.length) {
      $(containerId).innerHTML = `<div class="empty-state">No reasons recorded yet.</div>`;
      return;
    }
    $(containerId).innerHTML = entries
      .map(([reason, count]) => {
        const pct = totalCount > 0 ? Math.round((count / totalCount) * 100) : 0;
        return `
          <div class="reason-row">
            <div class="reason-top">
              <span>${esc(reason)}</span>
              <span>${count} (${pct}%)</span>
            </div>
            <div class="reason-bar-bg">
              <div class="reason-bar-fill" style="width:${pct}%"></div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  function renderCancellations() {
    const cancelled = state.orders.filter((o) => o.current_status === "Cancelled");
    const totalValue = cancelled.reduce((acc, o) => acc + Number(o.order_amount || 0), 0);
    const rate = state.orders.length > 0 ? ((cancelled.length / state.orders.length) * 100).toFixed(1) : "0.0";

    $("cancelPageCount").textContent = cancelled.length;
    $("cancelPageValue").textContent = inr(totalValue);
    $("cancelPageRate").textContent = `${rate}%`;

    $("cancelTableBody").innerHTML = cancelled.length
      ? cancelled
          .map(
            (o) => `
            <tr>
              <td>
                <div class="cell-main">Order: ${esc(o.order_date)}</div>
                <div class="cell-sub">Cancel: ${esc(o.cancel_date || "—")}</div>
              </td>
              <td>
                <div class="cell-main">${esc(o.order_id)}</div>
                <div class="cell-sub">${esc(o.product_name)}</div>
              </td>
              <td>
                <span class="pill ${o.payment_mode === "COD" ? "pill-cod" : "pill-prepaid"}">${esc(o.payment_mode)}</span>
                <div class="cell-main" style="margin-top:4px;">${inr(o.order_amount)}</div>
              </td>
              <td><span class="pill pill-cancelled">${esc(o.cancelled_by || "Not Specified")}</span></td>
              <td><div class="cell-main">${esc(o.cancel_reason || "No reason entered")}</div></td>
              <td><button class="btn btn-sm btn-outline" onclick="window.__editOrder(${o.id})">Edit</button></td>
            </tr>
          `
          )
          .join("")
      : `<tr><td colspan="6"><div class="empty-state">Zero cancelled orders! Great job.</div></td></tr>`;

    renderReasonBreakdown("cancelReasonsBreakdown", state.summary.cancel_reasons, cancelled.length);
  }

  function renderReturns() {
    const returned = state.orders.filter((o) => o.current_status === "Returned" || o.current_status === "RTO");
    const custRet = returned.filter((o) => o.current_status === "Returned").length;
    const rtoRet = returned.filter((o) => o.current_status === "RTO").length;
    const totalLoss = returned.reduce((acc, o) => acc + Number(o.return_deduction || 0), 0);
    const rate = state.orders.length > 0 ? ((returned.length / state.orders.length) * 100).toFixed(1) : "0.0";

    $("returnPageCount").textContent = returned.length;
    $("returnPageSplit").textContent = `Customer Returns: ${custRet} | RTO: ${rtoRet}`;
    $("returnPageDeduction").textContent = inr(totalLoss);
    $("returnPageRate").textContent = `${rate}%`;

    $("returnTableBody").innerHTML = returned.length
      ? returned
          .map(
            (o) => `
            <tr>
              <td>
                <div class="cell-main">Order: ${esc(o.order_date)}</div>
                <div class="cell-sub">Return: ${esc(o.return_date || "—")}</div>
              </td>
              <td>
                <div class="cell-main">${esc(o.order_id)}</div>
                <div class="cell-sub">${esc(o.product_name)}</div>
              </td>
              <td><span class="pill pill-returned">${esc(o.return_type || o.current_status)}</span></td>
              <td><div class="cell-main">${esc(o.return_reason || "No reason entered")}</div></td>
              <td><span class="pill pill-pending">${esc(o.return_status || "Pending")}</span></td>
              <td><div class="cell-main text-red">${inr(o.return_deduction)}</div></td>
              <td><button class="btn btn-sm btn-outline" onclick="window.__editOrder(${o.id})">Update</button></td>
            </tr>
          `
          )
          .join("")
      : `<tr><td colspan="7"><div class="empty-state">No returns or RTO orders recorded.</div></td></tr>`;

    renderReasonBreakdown("returnReasonsBreakdown", state.summary.return_reasons, returned.length);
  }

  function renderPayments() {
    const s = state.summary;
    const pendingOrders = state.orders.filter(
      (o) => (o.payment_status === "Pending" || o.payment_status === "On Hold") && !["Cancelled", "Returned", "RTO"].includes(o.current_status)
    );
    const settledOrders = state.orders.filter((o) => o.payment_status === "Settled");

    // Group settled orders by Bank Payout Transaction (UTR + Settled Date)
    const txMap = new Map();
    settledOrders.forEach((o) => {
      const key = `${o.settled_date || ""}|${o.utr_reference || "NO_UTR_" + o.id}`;
      if (!txMap.has(key)) {
        txMap.set(key, {
          settled_date: o.settled_date || "—",
          utr_reference: o.utr_reference || "—",
          orders: [],
          gross_total: 0,
          net_total: 0,
        });
      }
      const grp = txMap.get(key);
      grp.orders.push(o);
      grp.gross_total += Number(o.order_amount || 0);
      grp.net_total += Number(o.settled_amount || 0);
    });
    const bankTxList = Array.from(txMap.values()).sort((a, b) =>
      (b.settled_date || "").localeCompare(a.settled_date || "")
    );

    $("paySettledTotal").textContent = inr(s.settled_amount);
    $("paySettledOrders").textContent = `${bankTxList.length} bank payout(s) (${settledOrders.length} orders)`;
    $("payPendingTotal").textContent = inr(s.pending_payout_amount);
    $("payPendingOrders").textContent = `${pendingOrders.length} orders awaiting payout`;
    $("payGrossSales").textContent = inr(s.gross_sales);
    $("payNetProfit").textContent = inr(s.net_profit_est);

    // Anurag Bank Payout Recovery Stats for Arsh
    $("recBankTotal").textContent = inr(s.settled_amount);
    $("recPaidToArsh").textContent = inr(s.anurag_paid_to_arsh);
    $("recWithAnurag").textContent = inr(s.balance_with_anurag);
    $("recArshRemaining").textContent = inr(s.arsh_to_recover);
    $("recArshTotalSub").textContent = `Arsh Invested: ${inr(s.arsh_invested)}`;

    // Transfers Table
    const trList = state.transfers || [];
    $("transfersTableBody").innerHTML = trList.length
      ? trList
          .map(
            (t) => `
          <tr>
            <td><div class="cell-main">${esc(t.transfer_date)}</div></td>
            <td><div class="cell-main">${esc(t.from_member)} &rarr; ${esc(t.to_member)}</div></td>
            <td><span class="pill pill-cod">${esc(t.payment_mode || "Cash")}</span></td>
            <td><div class="cell-sub" style="margin-top:0;">${esc(t.notes || "—")}</div></td>
            <td><div class="cell-main text-green">${inr(t.amount)}</div></td>
            <td><button class="btn btn-sm btn-danger-outline" onclick="window.__deleteTransfer(${t.id})">Del</button></td>
          </tr>
        `
          )
          .join("")
      : `<tr><td colspan="6"><div class="empty-state">No payment transfers recorded yet.</div></td></tr>`;

    // Render Upcoming Schedule Cards Grid (13 Nov & 16 Nov)
    const schedule = s.upcoming_schedule || [];
    const net7 = s.upcoming_net_7days || 0;
    if ($("upcomingNet7DaysBadge")) {
      $("upcomingNet7DaysBadge").textContent = `Net Next 7 Days: ${net7 < 0 ? "–" : "+"}${inr(Math.abs(net7))}`;
      $("upcomingNet7DaysBadge").className = `pill ${net7 < 0 ? "pill-pending" : "pill-delivered"}`;
    }

    if ($("upcomingScheduleCardsGrid")) {
      $("upcomingScheduleCardsGrid").innerHTML = schedule.length
        ? schedule
            .map((sch) => {
              const isNeg = sch.net < 0;
              const netDisplay = `${isNeg ? "–" : "+"}${inr(Math.abs(sch.net))}`;
              const badgeClass = isNeg ? "pill-pending" : "pill-delivered";
              const itemsHtml = sch.items
                .map((it) => {
                  const itSign = it.amount >= 0 ? "+" : "–";
                  const itColor = it.amount >= 0 ? "text-green" : "text-red";
                  return `
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #f1f5f9; font-size:0.85rem;">
                      <div style="flex:1; padding-right:8px;">
                        <span style="font-weight:600; color:#1e293b;">${esc(it.product_name)}</span>
                        <div class="cell-sub" style="margin-top:2px;">Sub: ${esc(it.sub_order_id)} &bull; ${esc(it.type)}</div>
                      </div>
                      <div class="${itColor}" style="font-weight:700; font-size:0.95rem; white-space:nowrap;">
                        ${itSign}${inr(Math.abs(it.amount))}
                      </div>
                    </div>
                  `;
                })
                .join("");

              return `
                <div style="background:#ffffff; border-radius:12px; border:1px solid #e2e8f0; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                    <div>
                      <h3 style="margin:0; font-size:1.15rem; color:#1e293b; font-weight:700;">📅 ${esc(sch.date)}</h3>
                      <div class="cell-sub" style="margin-top:2px;">${sch.items.length} item(s) included</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:1.25rem; font-weight:800; color:${isNeg ? '#dc2626' : '#16a34a'};">${netDisplay}</div>
                      <span class="pill ${badgeClass}" style="font-size:0.75rem; padding:2px 8px; margin-top:4px; display:inline-block;">Bank Transfer: ${inr(sch.bank_transfer)}</span>
                    </div>
                  </div>
                  <div style="background:#f8fafc; border-radius:8px; padding:8px 12px; margin-bottom:12px; border-left:3px solid ${isNeg ? '#ef4444' : '#22c55e'};">
                    <div style="font-size:0.8rem; color:#475569; line-height:1.4;">
                      ${isNeg ? '⚠️ Net negative amount will be adjusted in upcoming payouts' : '✅ Scheduled for bank transfer'}
                    </div>
                  </div>
                  <div style="margin-top:8px;">
                    ${itemsHtml}
                  </div>
                </div>
              `;
            })
            .join("")
        : `<div class="empty-state">No upcoming payouts scheduled in the next 7 days.</div>`;
    }

    $("pendingPaymentsBody").innerHTML = pendingOrders.length
      ? pendingOrders
          .sort((a, b) => (a.expected_payout_date || "9999").localeCompare(b.expected_payout_date || "9999"))
          .map((o) => {
            const amt = o.settled_amount > 0 ? o.settled_amount : o.order_amount;
            const cd = payoutCountdownText(o.expected_payout_date);
            return `
              <tr>
                <td>
                  <div class="cell-main">${esc(o.order_id)}</div>
                  <div class="cell-sub">${esc(o.order_date)}</div>
                </td>
                <td>
                  <div class="cell-main">${esc(o.product_name)}</div>
                  <div class="cell-sub">${esc(o.payment_mode)}</div>
                </td>
                <td>${statusPill(o.current_status)}</td>
                <td><div class="cell-main">${inr(amt)}</div></td>
                <td><div class="cell-main">${esc(o.expected_payout_date || "Not Set")}</div></td>
                <td><span class="pill ${cd.cls}">${esc(cd.text)}</span></td>
                <td>
                  <button class="btn btn-sm btn-success-outline" onclick="window.__openSettle(${o.id})">Mark Settled in Bank</button>
                </td>
              </tr>
            `;
          })
          .join("")
      : `<tr><td colspan="7"><div class="empty-state">No pending payments!</div></td></tr>`;

    $("settledPaymentsBody").innerHTML = bankTxList.length
      ? bankTxList
          .map((tx) => {
            const deduction = tx.gross_total - tx.net_total;
            const orderLinks = tx.orders
              .map((o) => `<div><strong>${esc(o.sub_order_id || o.order_id)}</strong> (${inr(o.order_amount)})</div>`)
              .join("");
            const editTargetId = tx.orders[0].id;
            return `
            <tr>
              <td><div class="cell-main text-green">${esc(tx.settled_date)}</div></td>
              <td><div class="cell-main">${esc(tx.utr_reference)}</div><div class="cell-sub">${tx.orders.length} order(s)</div></td>
              <td><div class="cell-sub" style="margin-top:0;">${orderLinks}</div></td>
              <td>
                <div class="cell-main">Gross: ${inr(tx.gross_total)}</div>
                ${deduction > 0.01 ? `<div class="cell-sub text-red">Deduction / Ads: -${inr(deduction)}</div>` : `<div class="cell-sub">Deductions: ₹0</div>`}
              </td>
              <td><div class="cell-main text-green" style="font-size:15px;">${inr(tx.net_total)}</div></td>
              <td><button class="btn btn-sm btn-outline" onclick="window.__editOrder(${editTargetId})">Inspect</button></td>
            </tr>
          `;
          })
          .join("")
      : `<tr><td colspan="6"><div class="empty-state">No settled payouts recorded yet.</div></td></tr>`;
  }

  function renderExpenses() {
    const s = state.summary;
    const typeFilter = $("filterExpenseType").value;
    const paidByFilter = $("filterExpensePaidBy").value;

    const partnerPocket = state.expenses
      .filter((e) => e.entry_type === "Expense" && e.paid_by !== "Company Bank")
      .reduce((acc, e) => acc + Number(e.amount || 0), 0);

    $("expTotalSpent").textContent = inr(s.total_expenses);
    $("expTotalInvested").textContent = inr(s.total_investments);
    $("expPartnerPocket").textContent = inr(partnerPocket);
    $("expCompanyBank").textContent = inr(s.company_bank_expenses);

    const filtered = state.expenses.filter((e) => {
      if (typeFilter && e.entry_type !== typeFilter) return false;
      if (paidByFilter && e.paid_by !== paidByFilter) return false;
      return true;
    });

    $("expensesTableBody").innerHTML = filtered.length
      ? filtered
          .map((e) => {
            const typeCls =
              e.entry_type === "Investment"
                ? "pill-delivered"
                : e.entry_type === "Withdrawal"
                ? "pill-returned"
                : "pill-ready";
            return `
              <tr>
                <td><div class="cell-main">${esc(e.expense_date)}</div></td>
                <td><span class="pill ${typeCls}">${esc(e.entry_type)}</span></td>
                <td>${esc(e.category)}</td>
                <td>
                  <div class="cell-main">${esc(e.title)}</div>
                  ${e.notes ? `<div class="cell-sub">${esc(e.notes)}</div>` : ""}
                </td>
                <td><strong>${esc(e.paid_by)}</strong></td>
                <td>${esc(e.payment_method)}</td>
                <td><div class="cell-main">${inr(e.amount)}</div></td>
                <td><button class="btn btn-sm btn-danger-outline" onclick="window.__deleteExpense(${e.id})">Delete</button></td>
              </tr>
            `;
          })
          .join("")
      : `<tr><td colspan="8"><div class="empty-state">No entries match this filter.</div></td></tr>`;
  }

  function renderTeam() {
    const members = state.summary.member_stats || [];
    $("teamCardsGrid").innerHTML = members
      .map((m) => {
        const initials = m.name.slice(0, 2).toUpperCase();
        return `
          <div class="team-card">
            <div class="team-card-head">
              <div class="team-identity">
                <div class="team-avatar-lg">${esc(initials)}</div>
                <div>
                  <div class="cell-main" style="font-size:16px;">${esc(m.name)}</div>
                  <div class="cell-sub">${esc(m.role)}</div>
                </div>
              </div>
              <button class="btn btn-sm btn-outline" onclick="window.__editMember('${esc(m.id)}')">Edit</button>
            </div>
            <div class="team-stats-list">
              <div class="team-stat-box">
                <div class="team-stat-label">Capital Invested</div>
                <div class="team-stat-val text-green">${inr(m.invested)}</div>
              </div>
              <div class="team-stat-box">
                <div class="team-stat-label">Expenses Paid</div>
                <div class="team-stat-val">${inr(m.expenses_paid)}</div>
              </div>
              <div class="team-stat-box">
                <div class="team-stat-label">Withdrawn</div>
                <div class="team-stat-val text-orange">${inr(m.withdrawn)}</div>
              </div>
              <div class="team-stat-box">
                <div class="team-stat-label">Net Contribution</div>
                <div class="team-stat-val">${inr(m.net_contribution)}</div>
              </div>
              <div class="team-stat-box">
                <div class="team-stat-label">Orders Handled</div>
                <div class="team-stat-val">${m.orders_handled}</div>
              </div>
              <div class="team-stat-box">
                <div class="team-stat-label">Profit Share %</div>
                <div class="team-stat-val">${m.share_percent}%</div>
              </div>
            </div>
            <div class="cell-sub">${esc(m.notes || "")}${m.phone ? ` &bull; 📞 ${esc(m.phone)}` : ""}</div>
          </div>
        `;
      })
      .join("");
  }

  // Conditional Form Sections in Order Modal
  function toggleConditionalOrderFields() {
    const st = $("fCurrentStatus").value;
    $("cancelFieldsBox").classList.toggle("hidden", st !== "Cancelled");
    $("returnFieldsBox").classList.toggle("hidden", st !== "Returned" && st !== "RTO");

    if (["Cancelled", "Returned", "RTO"].includes(st)) {
      if ($("fPaymentStatus").value === "Pending") {
        $("fPaymentStatus").value = "Not Applicable";
      }
    } else if ($("fPaymentStatus").value === "Not Applicable") {
      $("fPaymentStatus").value = "Pending";
    }
  }

  function openNewOrderModal() {
    $("orderModalTitle").textContent = "Add New Meesho Order";
    $("orderForm").reset();
    $("orderPk").value = "";
    $("fOrderDate").value = todayStr();
    $("fInitialStatus").value = "Pending";
    $("fCurrentStatus").value = "Pending";
    $("fPaymentStatus").value = "Pending";
    $("fExpectedPayoutDate").value = addDaysStr(todayStr(), 10);
    $("fHandledBy").value = state.activeMember;
    toggleConditionalOrderFields();
    $("orderModal").classList.remove("hidden");
  }

  window.__editOrder = (pk) => {
    const o = state.orders.find((x) => x.id === pk);
    if (!o) return;
    $("orderModalTitle").textContent = `Edit Order: ${o.order_id}`;
    $("orderPk").value = o.id;
    $("fOrderId").value = o.order_id;
    $("fSubOrderId").value = o.sub_order_id || "";
    $("fOrderDate").value = o.order_date;
    $("fProductName").value = o.product_name;
    $("fSku").value = o.sku || "";
    $("fQuantity").value = o.quantity || 1;
    $("fPaymentMode").value = o.payment_mode || "COD";
    $("fOrderAmount").value = o.order_amount || 0;
    $("fProductCost").value = o.product_cost || 0;
    $("fPackagingCost").value = o.packaging_cost || 0;
    $("fCustomerName").value = o.customer_name || "";
    $("fCustomerCity").value = o.customer_city || "";
    $("fHandledBy").value = o.handled_by || state.activeMember;
    $("fInitialStatus").value = o.initial_status || "Pending";
    $("fCurrentStatus").value = o.current_status || "Pending";
    $("fStatusNote").value = "";
    $("fCancelledBy").value = o.cancelled_by || "Customer";
    $("fCancelDate").value = o.cancel_date || todayStr();
    $("fCancelReason").value = o.cancel_reason || "";
    $("fReturnType").value = o.return_type || "Customer Return";
    $("fReturnStatus").value = o.return_status || "Initiated";
    $("fReturnDate").value = o.return_date || todayStr();
    $("fReturnDeduction").value = o.return_deduction || 0;
    $("fReturnReason").value = o.return_reason || "";
    $("fPaymentStatus").value = o.payment_status || "Pending";
    $("fExpectedPayoutDate").value = o.expected_payout_date || "";
    $("fSettledDate").value = o.settled_date || "";
    $("fSettledAmount").value = o.settled_amount || 0;
    $("fUtrReference").value = o.utr_reference || "";
    $("fNotes").value = o.notes || "";
    toggleConditionalOrderFields();
    $("orderModal").classList.remove("hidden");
  };

  window.__viewHistory = (pk) => {
    const o = state.orders.find((x) => x.id === pk);
    if (!o) return;
    $("historyModalTitle").textContent = `Order History: ${o.order_id}`;
    const hist = o.history || [];
    $("historyModalBody").innerHTML = `
      <div style="margin-bottom:14px;">
        <div class="cell-main">${esc(o.product_name)}</div>
        <div class="cell-sub">Order Date: ${esc(o.order_date)} &bull; Mode: ${esc(o.payment_mode)} &bull; Started: <strong>${esc(o.initial_status)}</strong> &rarr; Current: <strong>${esc(o.current_status)}</strong></div>
      </div>
      <div class="timeline">
        ${
          hist.length
            ? hist
                .map(
                  (h) => `
              <div class="timeline-item">
                <div class="timeline-title">${h.old_status ? `${esc(h.old_status)} &rarr; ` : ""}${esc(h.new_status)}</div>
                <div class="timeline-meta">${esc(h.changed_at)} &bull; By ${esc(h.changed_by)}</div>
                ${h.note ? `<div class="cell-sub">${esc(h.note)}</div>` : ""}
              </div>
            `
                )
                .join("")
            : `<div class="empty-state">No status transitions recorded.</div>`
        }
      </div>
    `;
    $("historyModal").classList.remove("hidden");
  };

  window.__deleteOrder = async (pk) => {
    if (!confirm("Delete this order permanently?")) return;
    await api(`/api/orders/${pk}`, { method: "DELETE" });
    toast("Order deleted");
    await loadDashboard();
  };

  window.__openSettle = (pk) => {
    const o = state.orders.find((x) => x.id === pk);
    if (!o) return;
    $("settleOrderPk").value = o.id;
    $("settleOrderInfo").textContent = `Order ${o.order_id} (${o.product_name}) • Gross Order Amount: ${inr(o.order_amount)}`;
    $("sSettledDate").value = todayStr();
    $("sSettledAmount").value = o.settled_amount > 0 ? o.settled_amount : o.order_amount;
    $("sUtr").value = o.utr_reference || "";
    $("settleModal").classList.remove("hidden");
  };

  window.__deleteExpense = async (pk) => {
    if (!confirm("Delete this expense/investment entry?")) return;
    await api(`/api/expenses/${pk}`, { method: "DELETE" });
    toast("Entry deleted");
    await loadDashboard();
  };

  window.__editMember = (id) => {
    const m = (state.summary.member_stats || []).find((x) => x.id === id);
    if (!m) return;
    $("memberModalTitle").textContent = `Edit Member: ${m.name}`;
    $("mId").value = m.id;
    $("mRole").value = m.role;
    $("mShare").value = m.share_percent;
    $("mPhone").value = m.phone || "";
    $("mNotes").value = m.notes || "";
    $("memberModal").classList.remove("hidden");
  };

  function openNewExpenseModal() {
    $("expenseForm").reset();
    $("eDate").value = todayStr();
    $("ePaidBy").value = state.activeMember;
    $("expenseModal").classList.remove("hidden");
  }

  // Simple robust CSV parser (supports quoted commas)
  function parseCsvText(text) {
    const rows = [];
    let cur = [];
    let val = "";
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      const next = text[i + 1];
      if (inQuotes) {
        if (ch === '"' && next === '"') {
          val += '"';
          i++;
        } else if (ch === '"') {
          inQuotes = false;
        } else {
          val += ch;
        }
      } else {
        if (ch === '"') {
          inQuotes = true;
        } else if (ch === ",") {
          cur.push(val.trim());
          val = "";
        } else if (ch === "\n" || ch === "\r") {
          if (ch === "\r" && next === "\n") i++;
          cur.push(val.trim());
          if (cur.some((c) => c !== "")) rows.push(cur);
          cur = [];
          val = "";
        } else {
          val += ch;
        }
      }
    }
    if (val.length > 0 || cur.length > 0) {
      cur.push(val.trim());
      if (cur.some((c) => c !== "")) rows.push(cur);
    }
    if (rows.length < 2) return [];
    const headers = rows[0].map((h) => h.toLowerCase().replace(/[^a-z0-9]+/g, "_"));

    function pick(obj, keys, fallback = "") {
      for (const k of keys) {
        for (const h of Object.keys(obj)) {
          if (h.includes(k) && obj[h]) return obj[h];
        }
      }
      return fallback;
    }

    return rows.slice(1).map((cols) => {
      const obj = {};
      headers.forEach((h, idx) => {
        obj[h] = cols[idx] || "";
      });
      const rawStatus = pick(obj, ["current_status", "reason_for_credit", "order_status", "status"], "Pending");
      const low = rawStatus.toLowerCase();
      let mappedStatus = "Pending";
      if (low.includes("deliver")) mappedStatus = "Delivered";
      else if (low.includes("cancel")) mappedStatus = "Cancelled";
      else if (low.includes("rto")) mappedStatus = "RTO";
      else if (low.includes("return")) mappedStatus = "Returned";
      else if (low.includes("ship")) mappedStatus = "Shipped";
      else if (low.includes("ready")) mappedStatus = "Ready to Ship";

      const rawMode = pick(obj, ["payment_mode", "payment_type", "mode"], "COD");
      const payMode = rawMode.toLowerCase().includes("pre") ? "Prepaid" : "COD";

      return {
        order_id: pick(obj, ["order_id", "sub_order_no", "sub_order_id"]),
        sub_order_id: pick(obj, ["sub_order_no", "sub_order_id"]),
        order_date: pick(obj, ["order_date", "date"], todayStr()).slice(0, 10),
        product_name: pick(obj, ["product_name", "sku_name", "item"], "Meesho Product"),
        sku: pick(obj, ["sku"]),
        quantity: parseInt(pick(obj, ["quantity", "qty"], "1"), 10) || 1,
        payment_mode: payMode,
        order_amount: parseFloat(pick(obj, ["order_amount", "supplier_listed_price", "meesho_price", "price", "amount"], "0")) || 0,
        current_status: mappedStatus,
        cancel_reason: mappedStatus === "Cancelled" ? pick(obj, ["cancel_reason", "reason"]) : "",
        return_reason: mappedStatus === "Returned" || mappedStatus === "RTO" ? pick(obj, ["return_reason", "reason"]) : "",
        return_type: mappedStatus === "RTO" ? "Courier RTO" : mappedStatus === "Returned" ? "Customer Return" : "",
        settled_amount: parseFloat(pick(obj, ["settled_amount", "final_settlement"], "0")) || 0,
        settled_date: pick(obj, ["settled_date", "settlement_date"]),
        utr_reference: pick(obj, ["utr", "transaction_id"]),
      };
    }).filter((r) => r.order_id);
  }

  function bindEvents() {
    // Navigation
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => switchPage(btn.dataset.page));
    });
    document.querySelectorAll("[data-goto]").forEach((card) => {
      card.addEventListener("click", () => switchPage(card.dataset.goto));
    });
    document.querySelectorAll("[data-goto-btn]").forEach((btn) => {
      btn.addEventListener("click", () => switchPage(btn.dataset.gotoBtn));
    });

    function syncCollapseBtnLabel() {
      const collapsed = document.querySelector(".app-shell").classList.contains("sidebar-collapsed");
      const btn = $("sidebarCollapseBtn");
      btn.innerHTML = collapsed ? "&raquo;" : "&laquo;";
      btn.title = collapsed ? "Expand Side Panel" : "Collapse Side Panel";
    }

    function toggleSidebar() {
      const shell = document.querySelector(".app-shell");
      if (window.innerWidth <= 820) {
        $("sidebar").classList.toggle("open");
      } else {
        const collapsed = shell.classList.toggle("sidebar-collapsed");
        localStorage.setItem("nova_sidebar_collapsed", collapsed ? "1" : "0");
        syncCollapseBtnLabel();
      }
    }

    if (localStorage.getItem("nova_sidebar_collapsed") === "1" && window.innerWidth > 820) {
      document.querySelector(".app-shell").classList.add("sidebar-collapsed");
    }
    syncCollapseBtnLabel();

    $("menuToggle").addEventListener("click", toggleSidebar);
    $("sidebarCollapseBtn").addEventListener("click", toggleSidebar);
    $("brandAvatarBtn").addEventListener("click", () => {
      if (window.innerWidth > 820 && document.querySelector(".app-shell").classList.contains("sidebar-collapsed")) {
        toggleSidebar();
      }
    });

    // Active member switcher
    $("activeMemberSelect").value = state.activeMember;
    $("activeMemberSelect").addEventListener("change", (e) => {
      state.activeMember = e.target.value;
      localStorage.setItem("nova_active_member", state.activeMember);
      toast(`Active member switched to ${state.activeMember}`);
    });

    // Quick buttons
    $("btnQuickOrder").addEventListener("click", openNewOrderModal);
    $("btnQuickExpense").addEventListener("click", openNewExpenseModal);
    $("btnAddExpensePage").addEventListener("click", openNewExpenseModal);

    // Modal closers
    document.querySelectorAll("[data-close]").forEach((btn) => {
      btn.addEventListener("click", () => $(btn.dataset.close).classList.add("hidden"));
    });

    // Order conditional fields
    $("fCurrentStatus").addEventListener("change", toggleConditionalOrderFields);

    // Filters
    ["orderSearch", "filterOrderStatus", "filterPayMode", "filterPayStatus", "filterDateFrom", "filterDateTo"].forEach((id) => {
      $(id).addEventListener("input", renderOrdersTable);
      $(id).addEventListener("change", renderOrdersTable);
    });
    $("btnResetFilters").addEventListener("click", () => {
      $("orderSearch").value = "";
      $("filterOrderStatus").value = "";
      $("filterPayMode").value = "";
      $("filterPayStatus").value = "";
      $("filterDateFrom").value = "";
      $("filterDateTo").value = "";
      renderOrdersTable();
    });

    $("filterExpenseType").addEventListener("change", renderExpenses);
    $("filterExpensePaidBy").addEventListener("change", renderExpenses);

    // Save Order Form
    $("orderForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const pk = $("orderPk").value;
      const payload = {
        order_id: $("fOrderId").value,
        sub_order_id: $("fSubOrderId").value,
        order_date: $("fOrderDate").value,
        product_name: $("fProductName").value,
        sku: $("fSku").value,
        quantity: Number($("fQuantity").value || 1),
        payment_mode: $("fPaymentMode").value,
        order_amount: Number($("fOrderAmount").value || 0),
        product_cost: Number($("fProductCost").value || 0),
        packaging_cost: Number($("fPackagingCost").value || 0),
        customer_name: $("fCustomerName").value,
        customer_city: $("fCustomerCity").value,
        handled_by: $("fHandledBy").value,
        initial_status: $("fInitialStatus").value,
        current_status: $("fCurrentStatus").value,
        status_note: $("fStatusNote").value,
        cancelled_by: $("fCancelledBy").value,
        cancel_date: $("fCancelDate").value,
        cancel_reason: $("fCancelReason").value,
        return_type: $("fReturnType").value,
        return_status: $("fReturnStatus").value,
        return_date: $("fReturnDate").value,
        return_deduction: Number($("fReturnDeduction").value || 0),
        return_reason: $("fReturnReason").value,
        payment_status: $("fPaymentStatus").value,
        expected_payout_date: $("fExpectedPayoutDate").value,
        settled_date: $("fSettledDate").value,
        settled_amount: Number($("fSettledAmount").value || 0),
        utr_reference: $("fUtrReference").value,
        notes: $("fNotes").value,
      };
      try {
        if (pk) {
          await api(`/api/orders/${pk}`, { method: "PUT", body: JSON.stringify(payload) });
          toast("Order updated successfully!");
        } else {
          await api("/api/orders", { method: "POST", body: JSON.stringify(payload) });
          toast("New order added!");
        }
        $("orderModal").classList.add("hidden");
        await loadDashboard();
      } catch (err) {
        alert(err.message);
      }
    });

    // Save Settle Payment Form
    $("settleForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const pk = $("settleOrderPk").value;
      try {
        await api(`/api/orders/${pk}`, {
          method: "PUT",
          body: JSON.stringify({
            payment_status: "Settled",
            settled_date: $("sSettledDate").value,
            settled_amount: Number($("sSettledAmount").value || 0),
            utr_reference: $("sUtr").value,
            handled_by: state.activeMember,
          }),
        });
        $("settleModal").classList.add("hidden");
        toast("Payment marked as Settled in Bank!");
        await loadDashboard();
      } catch (err) {
        alert(err.message);
      }
    });

    // Save Expense Form
    $("expenseForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("/api/expenses", {
          method: "POST",
          body: JSON.stringify({
            expense_date: $("eDate").value,
            entry_type: $("eType").value,
            category: $("eCategory").value,
            paid_by: $("ePaidBy").value,
            title: $("eTitle").value,
            amount: Number($("eAmount").value || 0),
            payment_method: $("eMethod").value,
            notes: $("eNotes").value,
          }),
        });
        $("expenseModal").classList.add("hidden");
        toast("Entry saved to Hisab!");
        await loadDashboard();
      } catch (err) {
        alert(err.message);
      }
    });

    // Save Member Form
    $("memberForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = $("mId").value;
      try {
        await api(`/api/members/${id}`, {
          method: "PUT",
          body: JSON.stringify({
            role: $("mRole").value,
            share_percent: Number($("mShare").value || 0),
            phone: $("mPhone").value,
            notes: $("mNotes").value,
          }),
        });
        $("memberModal").classList.add("hidden");
        toast("Member updated!");
        await loadDashboard();
      } catch (err) {
        alert(err.message);
      }
    });

    // Transfer Form
    $("trDate").value = todayStr();
    $("transferForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("/api/transfers", {
          method: "POST",
          body: JSON.stringify({
            transfer_date: $("trDate").value,
            from_member: "Anurag",
            to_member: "Arsh",
            payment_mode: $("trMode").value,
            amount: Number($("trAmount").value || 0),
            notes: $("trNotes").value || "Anurag paid cash to Arsh",
          }),
        });
        $("trAmount").value = "";
        $("trNotes").value = "";
        toast("Anurag -> Arsh payment recorded!");
        await loadDashboard();
      } catch (err) {
        alert(err.message);
      }
    });

    window.__deleteTransfer = async (id) => {
      if (!confirm("Delete this transfer entry?")) return;
      try {
        await api(`/api/transfers/${id}`, { method: "DELETE" });
        toast("Transfer deleted.");
        await loadDashboard();
      } catch (err) {
        alert(err.message);
      }
    };

    // CSV Import
    $("csvFileInput").addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        const parsed = parseCsvText(ev.target.result || "");
        state.parsedCsvRows = parsed;
        $("csvPreviewBox").classList.remove("hidden");
        $("csvPreviewSummary").innerHTML = parsed.length
          ? `Found <strong>${parsed.length}</strong> valid orders in <code>${esc(file.name)}</code>. Ready to import!`
          : `Could not detect valid Order IDs in this CSV. Make sure it has an <code>Order ID</code> or <code>Sub Order No</code> column.`;
      };
      reader.readAsText(file);
    });

    $("btnConfirmImport").addEventListener("click", async () => {
      if (!state.parsedCsvRows.length) return;
      try {
        const res = await api("/api/orders/import", {
          method: "POST",
          body: JSON.stringify({ rows: state.parsedCsvRows, handled_by: state.activeMember }),
        });
        toast(`Imported ${res.inserted} new & updated ${res.updated} orders!`);
        $("csvPreviewBox").classList.add("hidden");
        $("csvFileInput").value = "";
        state.parsedCsvRows = [];
        await loadDashboard();
        switchPage("orders");
      } catch (err) {
        alert(err.message);
      }
    });
  }

  bindEvents();
  loadDashboard();
})();
