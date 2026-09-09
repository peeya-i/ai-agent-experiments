/**
 * WanderAI - Frontend Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements - Tabs
  const tabBtnGen = document.getElementById("tab-btn-generator");
  const tabBtnLogs = document.getElementById("tab-btn-logs");
  const viewGen = document.getElementById("view-generator");
  const viewLogs = document.getElementById("view-logs");

  // Elements - Generator Form & Results
  const form = document.getElementById("itinerary-form");
  const btnSubmit = document.getElementById("btn-submit-generate");
  const resultPlaceholder = document.getElementById("result-placeholder");
  const resultLoading = document.getElementById("result-loading");
  const resultContent = document.getElementById("result-content");
  const pipelineStatusText = document.getElementById("pipeline-status-text");

  // Elements - Modals
  const modalItinerary = document.getElementById("modal-itinerary");
  const modalPayload = document.getElementById("modal-payload");
  const btnCloseItinerary = document.getElementById("btn-close-itinerary-modal");
  const btnDismissItinerary = document.getElementById("btn-dismiss-itinerary-modal");
  const btnClosePayload = document.getElementById("btn-close-payload-modal");
  const btnDismissPayload = document.getElementById("btn-dismiss-payload-modal");
  const btnCopyPayload = document.getElementById("btn-copy-payload");
  const toast = document.getElementById("toast");

  let currentRawPayload = "";

  // ---------------------------------------------------------
  // 1. Navigation Tabs (Requirement 6)
  // ---------------------------------------------------------
  tabBtnGen.addEventListener("click", () => switchTab("generator"));
  tabBtnLogs.addEventListener("click", () => {
    switchTab("logs");
    loadHistory();
  });

  function switchTab(tab) {
    if (tab === "generator") {
      tabBtnGen.classList.add("active");
      tabBtnGen.setAttribute("aria-selected", "true");
      tabBtnLogs.classList.remove("active");
      tabBtnLogs.setAttribute("aria-selected", "false");
      viewGen.classList.add("active");
      viewLogs.classList.remove("active");
    } else {
      tabBtnLogs.classList.add("active");
      tabBtnLogs.setAttribute("aria-selected", "true");
      tabBtnGen.classList.remove("active");
      tabBtnGen.setAttribute("aria-selected", "false");
      viewLogs.classList.add("active");
      viewGen.classList.remove("active");
    }
  }

  // ---------------------------------------------------------
  // 2. Form Submission & Generation Pipeline
  // ---------------------------------------------------------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const origin = document.getElementById("input-origin").value.trim();
    const destination = document.getElementById("input-destination").value.trim();
    const duration = parseInt(document.getElementById("input-duration").value, 10);
    const budget = parseFloat(document.getElementById("input-budget").value);
    const departure_date = document.getElementById("input-departure").value;
    const interests = document.getElementById("input-interests").value.trim();

    if (!destination) {
      showToast("Please enter a destination city.");
      return;
    }

    // UI Loading State
    resultPlaceholder.classList.add("hidden");
    resultContent.classList.add("hidden");
    resultLoading.classList.remove("hidden");
    btnSubmit.disabled = true;

    // Stepper Animation
    const stepParallel = document.getElementById("step-parallel");
    const stepScheduler = document.getElementById("step-scheduler");
    const stepBudget = document.getElementById("step-budget");

    stepParallel.className = "step-item active";
    stepScheduler.className = "step-item";
    stepBudget.className = "step-item";
    pipelineStatusText.textContent = "Phase 1: Parallel Discovery (Flights, Hotels, Sights)...";

    const stepTimer1 = setTimeout(() => {
      stepParallel.className = "step-item";
      stepScheduler.className = "step-item active";
      pipelineStatusText.textContent = "Phase 2: Geographic Clustering & Skills Enrichment...";
    }, 1500);

    const stepTimer2 = setTimeout(() => {
      stepScheduler.className = "step-item";
      stepBudget.className = "step-item active";
      pipelineStatusText.textContent = "Phase 3: Iterative Loop & Budget Enforcement...";
    }, 3200);

    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          origin,
          destination,
          duration,
          budget,
          departure_date,
          interests
        })
      });

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Failed to generate itinerary");
      }

      renderGeneratedItinerary(data.run_id, data.state);
      showToast("Itinerary generated successfully!");

    } catch (err) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      resultLoading.classList.add("hidden");
      resultPlaceholder.classList.remove("hidden");
      showToast("Error: " + err.message);
    } finally {
      btnSubmit.disabled = false;
    }
  });

  function renderGeneratedItinerary(runId, state) {
    resultLoading.classList.add("hidden");
    resultContent.classList.remove("hidden");

    const userInput = state.user_input || {};
    const itinerary = state.current_itinerary || {};
    const breakdown = itinerary.cost_breakdown || {};
    const approved = state.budget_approved;

    // Header & Badges
    document.getElementById("itinerary-title").textContent = userInput.destination || "Trip";
    const depText = userInput.departure_date ? `Departure: ${userInput.departure_date}` : "Flexible Dates";
    document.getElementById("itinerary-meta").textContent = `From ${userInput.origin || "Origin"} • ${userInput.days} Days • ${depText}`;

    const statusBadge = document.getElementById("itinerary-status-badge");
    if (approved) {
      statusBadge.textContent = "Budget Approved";
      statusBadge.className = "badge badge-success";
    } else {
      statusBadge.textContent = "Budget Exceeded";
      statusBadge.className = "badge badge-warning";
    }

    // Download Links (Requirement 5)
    document.getElementById("btn-download-txt").href = `/download/txt/${runId}`;
    document.getElementById("btn-download-pdf").href = `/download/pdf/${runId}`;

    // Financial Strip
    document.getElementById("stat-target-budget").textContent = `$${parseFloat(userInput.budget || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    document.getElementById("stat-est-cost").textContent = `$${parseFloat(itinerary.total_estimated_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    document.getElementById("stat-flight-cost").textContent = `$${parseFloat(breakdown.flight || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    document.getElementById("stat-hotel-cost").textContent = `$${parseFloat(breakdown.lodging || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    document.getElementById("stat-act-cost").textContent = `$${parseFloat(breakdown.activities || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

    // Logistics
    const flight = itinerary.selected_flight || {};
    const hotel = itinerary.selected_hotel || {};
    document.getElementById("logistics-flight-desc").textContent = 
      `${flight.carrier || 'Flight'} (${flight.route || 'Direct'}) • $${parseFloat(flight.estimated_cost || 0).toFixed(2)}`;
    document.getElementById("logistics-hotel-desc").textContent = 
      `${hotel.name || 'Hotel'} in ${hotel.neighborhood || 'Area'} • $${parseFloat(hotel.nightly_rate || 0).toFixed(2)}/night`;

    // Critic Feedback Banner
    const criticBanner = document.getElementById("critic-feedback-banner");
    const criticText = document.getElementById("critic-feedback-text");
    if (state.critic_feedback) {
      criticText.textContent = state.critic_feedback;
      criticBanner.classList.remove("hidden");
    } else {
      criticBanner.classList.add("hidden");
    }

    // Schedule Timeline
    const scheduleContainer = document.getElementById("schedule-days-container");
    scheduleContainer.innerHTML = "";

    const schedule = itinerary.schedule || [];
    schedule.forEach((day) => {
      const dayCard = document.createElement("div");
      dayCard.className = "day-card";

      const headerDiv = document.createElement("div");
      headerDiv.className = "day-card-header";
      const dayCost = parseFloat(day.estimated_cost || 0);
      headerDiv.innerHTML = `
        <span class="day-title">Day ${day.day}: ${escapeHtml(day.neighborhood_focus || 'City Center')}</span>
        <div class="day-header-meta">
          <span class="day-cost-badge">💰 Day Est: $${dayCost.toFixed(2)}</span>
          <span class="neighborhood-tag">📍 ${escapeHtml(day.neighborhood_focus || 'Area')}</span>
        </div>
      `;
      dayCard.appendChild(headerDiv);

      if (day.insider_tip) {
        const tipDiv = document.createElement("div");
        tipDiv.className = "day-insider-tip";
        tipDiv.innerHTML = `<span>💡</span> <span>${escapeHtml(day.insider_tip)}</span>`;
        dayCard.appendChild(tipDiv);
      }

      const eventsList = document.createElement("div");
      eventsList.className = "events-list";

      (day.events || []).forEach((ev) => {
        const evRow = document.createElement("div");
        const bInfo = getEventBadgeInfo(ev.category, ev.name);
        const isGem = bInfo.cls === "badge-gem";
        evRow.className = `event-row ${isGem ? 'hidden-gem' : ''}`;

        const costVal = parseFloat(ev.estimated_cost || 0);
        const costLabel = costVal > 0 ? `$${costVal.toFixed(2)}` : "Free";
        const durHours = parseFloat(ev.duration_hours || 0);
        const durationText = durHours > 0 ? `${durHours} hr${durHours === 1 ? '' : 's'}` : null;

        evRow.innerHTML = `
          <div class="event-primary">
            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.2rem;">
              <span class="event-time">${escapeHtml(ev.time_slot || 'Anytime')}</span>
              <span class="event-category-badge ${bInfo.cls}">${bInfo.icon} ${escapeHtml(bInfo.label)}</span>
            </div>
            <span class="event-name">${escapeHtml(ev.name)}</span>
            ${ev.description ? `<span class="event-desc">${escapeHtml(ev.description)}</span>` : ''}
            <div class="event-meta-tags">
              ${ev.location ? `<span class="event-meta-tag">📍 ${escapeHtml(ev.location)}</span>` : ''}
              ${durationText ? `<span class="event-meta-tag">⏱️ ${escapeHtml(durationText)}</span>` : ''}
            </div>
          </div>
          <span class="event-cost">${costLabel}</span>
        `;
        eventsList.appendChild(evRow);
      });

      dayCard.appendChild(eventsList);
      scheduleContainer.appendChild(dayCard);
    });
  }

  // ---------------------------------------------------------
  // 3. History & Event Logs Dashboard (Tab 2)
  // ---------------------------------------------------------
  const btnRefreshHistory = document.getElementById("btn-refresh-history");
  btnRefreshHistory.addEventListener("click", loadHistory);

  async function loadHistory() {
    try {
      const resp = await fetch("/api/history");
      const data = await resp.json();
      if (!data.success) return;

      // Metrics (Requirement 7)
      document.getElementById("metric-total-itineraries").textContent = data.metrics.total_itineraries;
      document.getElementById("metric-successful-runs").textContent = data.metrics.successful_runs;
      document.getElementById("metric-failed-runs").textContent = data.metrics.failed_runs;
      document.getElementById("metric-total-events").textContent = data.metrics.total_events;

      // Itineraries Table (Requirement 8)
      const tbody = document.getElementById("tbody-itineraries");
      tbody.innerHTML = "";

      if (!data.itineraries || data.itineraries.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center empty-cell">No itineraries generated yet.</td></tr>`;
        return;
      }

      data.itineraries.forEach((run) => {
        const tr = document.createElement("tr");
        tr.className = "table-row-clickable";
        tr.dataset.runId = run.run_id;

        const isApproved = run.budget_approved === "True" || run.budget_approved === true;
        const statusBadge = isApproved
          ? `<span class="badge badge-success">Approved</span>`
          : `<span class="badge badge-warning">Exceeded</span>`;

        tr.innerHTML = `
          <td><small style="color: var(--text-secondary);">${escapeHtml(run.timestamp || 'N/A')}</small></td>
          <td>${escapeHtml(run.travel_date || 'Flexible')}</td>
          <td>${escapeHtml(run.days || '1')} Days</td>
          <td><strong>${escapeHtml(run.destination || 'N/A')}</strong></td>
          <td>${escapeHtml(run.origin || 'N/A')}</td>
          <td>$${parseFloat(run.budget || 0).toFixed(2)}</td>
          <td>$${parseFloat(run.estimated_cost || 0).toFixed(2)}</td>
          <td>${statusBadge}</td>
          <td>
            <button class="event-count-link" data-run-id="${run.run_id}" title="Click to view events below">
              <span>⚡</span>
              <span>${run.events_count || 0} events</span>
            </button>
          </td>
        `;

        // Row Click: Show full itinerary popup (Requirement 9)
        tr.addEventListener("click", (e) => {
          // If clicked the event count button, don't trigger itinerary modal
          if (e.target.closest(".event-count-link")) {
            return;
          }
          document.querySelectorAll(".table-row-clickable").forEach(r => r.classList.remove("selected-row"));
          tr.classList.add("selected-row");
          showItineraryModal(run.run_id);
        });

        // Event count click: Show event logs in Table 2 below (Requirement 10)
        const eventBtn = tr.querySelector(".event-count-link");
        eventBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          document.querySelectorAll(".table-row-clickable").forEach(r => r.classList.remove("selected-row"));
          tr.classList.add("selected-row");
          loadEventsForRun(run.run_id, run.destination);
        });

        tbody.appendChild(tr);
      });

    } catch (err) {
      console.error("Failed to load history:", err);
      showToast("Error loading history: " + err.message);
    }
  }

  // Load Events for Run into Table 2 (Requirement 10)
  async function loadEventsForRun(runId, destination) {
    const subtitle = document.getElementById("events-table-subtitle");
    const badge = document.getElementById("selected-run-badge");
    const tbody = document.getElementById("tbody-events");

    badge.textContent = `${destination || 'Run'} (${runId.substring(0, 10)})`;
    badge.className = "badge badge-accent";
    subtitle.textContent = `Showing lifecycle event logs for run: ${runId}`;
    tbody.innerHTML = `<tr><td colspan="5" class="text-center empty-cell">Loading event logs...</td></tr>`;

    // Scroll to events table
    document.getElementById("card-events-section").scrollIntoView({ behavior: "smooth", block: "start" });

    try {
      const resp = await fetch(`/api/events/${runId}`);
      const data = await resp.json();

      if (!data.success || !data.events || data.events.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center empty-cell">No event logs recorded for this run.</td></tr>`;
        return;
      }

      tbody.innerHTML = "";
      data.events.forEach((ev) => {
        const row = document.createElement("tr");

        let typeBadgeClass = "badge-neutral";
        if (ev.event_type.includes("request") || ev.event_type.includes("start")) typeBadgeClass = "badge-accent";
        if (ev.event_type.includes("response") || ev.event_type.includes("complete") || ev.event_type.includes("success") || ev.event_type.includes("approved")) typeBadgeClass = "badge-success";
        if (ev.event_type.includes("rejected") || ev.event_type.includes("exceeded")) typeBadgeClass = "badge-warning";
        if (ev.event_type.includes("error") || ev.event_type.includes("failed")) typeBadgeClass = "badge-danger";

        row.innerHTML = `
          <td><small style="color: var(--text-secondary);">${escapeHtml(ev.timestamp)}</small></td>
          <td><span class="badge ${typeBadgeClass}">${escapeHtml(ev.event_type)}</span></td>
          <td><strong>${escapeHtml(ev.agent_source || 'System')}</strong></td>
          <td>${escapeHtml(ev.summary || '')}</td>
          <td style="text-align: center;">
            <button class="btn btn-secondary btn-sm btn-payload" data-event-id="${ev.event_id}">
              Payload
            </button>
          </td>
        `;

        // Payload Button Click (Requirement 11)
        const btnPayload = row.querySelector(".btn-payload");
        btnPayload.addEventListener("click", () => {
          showPayloadModal(ev);
        });

        tbody.appendChild(row);
      });

    } catch (err) {
      console.error("Error loading events:", err);
      tbody.innerHTML = `<tr><td colspan="5" class="text-center empty-cell">Failed to load events: ${err.message}</td></tr>`;
    }
  }

  // ---------------------------------------------------------
  // 4. Modals: Full Itinerary & Event Payload
  // ---------------------------------------------------------

  // Modal 1: Itinerary Full View (Requirement 9)
  async function showItineraryModal(runId) {
    const modalBody = document.getElementById("modal-itinerary-body");
    modalBody.innerHTML = `<div class="text-center" style="padding: 3rem;">Loading full itinerary...</div>`;
    modalItinerary.classList.remove("hidden");

    try {
      const resp = await fetch(`/api/itinerary/${runId}`);
      const data = await resp.json();
      if (!data.success || !data.state) {
        modalBody.innerHTML = `<div class="text-center empty-cell">Itinerary data not available.</div>`;
        return;
      }

      const st = data.state;
      const user = st.user_input || {};
      const itin = st.current_itinerary || {};
      const breakdown = itin.cost_breakdown || {};
      const schedule = itin.schedule || [];

      modalBody.innerHTML = `
        <div class="result-top-bar" style="padding-bottom: 1rem;">
          <div>
            <span class="badge ${st.budget_approved ? 'badge-success' : 'badge-warning'}">
              ${st.budget_approved ? 'Budget Approved' : 'Budget Exceeded'}
            </span>
            <h3 style="font-size: 1.6rem; color: #fff; margin-top: 0.3rem;">${escapeHtml(user.destination || 'Trip')}</h3>
            <p style="color: var(--text-secondary); font-size: 0.85rem;">
              Origin: ${escapeHtml(user.origin || 'N/A')} | Travel Date: ${escapeHtml(user.departure_date || 'Flexible')} | Duration: ${user.days} Days | Target: $${parseFloat(user.budget || 0).toFixed(2)}
            </p>
          </div>
          <div class="export-actions">
            <a href="/download/txt/${runId}" class="btn btn-secondary btn-sm" download>📄 TXT</a>
            <a href="/download/pdf/${runId}" class="btn btn-primary btn-sm" download>📑 PDF</a>
          </div>
        </div>

        <div class="financial-summary-strip" style="margin: 1rem 0;">
          <div class="stat-cell"><span class="stat-lbl">Estimated Total</span><span class="stat-val highlight">$${parseFloat(itin.total_estimated_cost || 0).toFixed(2)}</span></div>
          <div class="stat-cell"><span class="stat-lbl">Transit</span><span class="stat-val">$${parseFloat(breakdown.flight || 0).toFixed(2)}</span></div>
          <div class="stat-cell"><span class="stat-lbl">Lodging</span><span class="stat-val">$${parseFloat(breakdown.lodging || 0).toFixed(2)}</span></div>
          <div class="stat-cell"><span class="stat-lbl">Activities</span><span class="stat-val">$${parseFloat(breakdown.activities || 0).toFixed(2)}</span></div>
        </div>

        ${st.critic_feedback ? `
          <div class="critic-banner" style="margin-bottom: 1rem;">
            <span>💡</span>
            <div><strong>Optimizer Note:</strong> ${escapeHtml(st.critic_feedback)}</div>
          </div>
        ` : ''}

        <h4 style="color: #fff; margin: 1rem 0 0.5rem;">Daily Schedule</h4>
        <div class="days-container">
          ${schedule.map(d => {
            const dayCost = parseFloat(d.estimated_cost || 0);
            return `
            <div class="day-card" style="padding: 1rem;">
              <div class="day-card-header">
                <span class="day-title">Day ${d.day}: ${escapeHtml(d.neighborhood_focus || 'Neighborhood')}</span>
                <div class="day-header-meta">
                  <span class="day-cost-badge">💰 Day Est: $${dayCost.toFixed(2)}</span>
                  <span class="neighborhood-tag">📍 ${escapeHtml(d.neighborhood_focus || 'Area')}</span>
                </div>
              </div>
              ${d.insider_tip ? `<div class="day-insider-tip">💡 ${escapeHtml(d.insider_tip)}</div>` : ''}
              <div class="events-list">
                ${(d.events || []).map(ev => {
                  const bInfo = getEventBadgeInfo(ev.category, ev.name);
                  const isGem = bInfo.cls === "badge-gem";
                  const cVal = parseFloat(ev.estimated_cost || 0);
                  const cLabel = cVal > 0 ? '$' + cVal.toFixed(2) : 'Free';
                  const dHours = parseFloat(ev.duration_hours || 0);
                  const dText = dHours > 0 ? `${dHours} hr${dHours === 1 ? '' : 's'}` : null;
                  return `
                  <div class="event-row ${isGem ? 'hidden-gem' : ''}">
                    <div class="event-primary">
                      <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.2rem;">
                        <span class="event-time">${escapeHtml(ev.time_slot || 'Anytime')}</span>
                        <span class="event-category-badge ${bInfo.cls}">${bInfo.icon} ${escapeHtml(bInfo.label)}</span>
                      </div>
                      <span class="event-name">${escapeHtml(ev.name)}</span>
                      ${ev.description ? `<span class="event-desc">${escapeHtml(ev.description)}</span>` : ''}
                      <div class="event-meta-tags">
                        ${ev.location ? `<span class="event-meta-tag">📍 ${escapeHtml(ev.location)}</span>` : ''}
                        ${dText ? `<span class="event-meta-tag">⏱️ ${escapeHtml(dText)}</span>` : ''}
                      </div>
                    </div>
                    <span class="event-cost">${cLabel}</span>
                  </div>
                `}).join('')}
              </div>
            </div>
          `}).join('')}
        </div>
      `;

    } catch (err) {
      modalBody.innerHTML = `<div class="text-center empty-cell">Error: ${err.message}</div>`;
    }
  }

  // Modal 2: Event Payload Popup (Requirement: Displays all information stored in the event)
  function showPayloadModal(event) {
    document.getElementById("modal-payload-source").textContent = event.agent_source || "Agent";
    document.getElementById("modal-payload-type").textContent = event.event_type || "Event";
    document.getElementById("modal-payload-time").textContent = event.timestamp || "";
    document.getElementById("modal-payload-id").textContent = event.event_id || "ID";
    document.getElementById("modal-payload-run").textContent = `Run: ${event.run_id || 'N/A'}`;
    document.getElementById("modal-payload-summary").textContent = event.summary || "";

    // Show all information stored in the event object
    currentRawPayload = JSON.stringify(event, null, 2);
    document.querySelector("#modal-payload-code code").textContent = currentRawPayload;

    // Reset copy button state
    document.getElementById("copy-text").textContent = "Copy to Clipboard";
    document.getElementById("copy-icon").textContent = "📋";

    modalPayload.classList.remove("hidden");
  }

  // Copy to Clipboard (Requirement 12)
  btnCopyPayload.addEventListener("click", async () => {
    if (!currentRawPayload) return;
    try {
      await navigator.clipboard.writeText(currentRawPayload);
      document.getElementById("copy-text").textContent = "Copied!";
      document.getElementById("copy-icon").textContent = "✅";
      showToast("Payload copied to clipboard!");
      setTimeout(() => {
        document.getElementById("copy-text").textContent = "Copy to Clipboard";
        document.getElementById("copy-icon").textContent = "📋";
      }, 2500);
    } catch (err) {
      // Fallback
      const textArea = document.createElement("textarea");
      textArea.value = currentRawPayload;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      showToast("Payload copied to clipboard!");
    }
  });

  // Modal Dismiss Listeners
  [btnCloseItinerary, btnDismissItinerary].forEach(btn => {
    btn.addEventListener("click", () => modalItinerary.classList.add("hidden"));
  });

  [btnClosePayload, btnDismissPayload].forEach(btn => {
    btn.addEventListener("click", () => modalPayload.classList.add("hidden"));
  });

  window.addEventListener("click", (e) => {
    if (e.target === modalItinerary) modalItinerary.classList.add("hidden");
    if (e.target === modalPayload) modalPayload.classList.add("hidden");
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      modalItinerary.classList.add("hidden");
      modalPayload.classList.add("hidden");
    }
  });

  // Toast Helper
  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.remove("hidden");
    setTimeout(() => {
      toast.classList.add("hidden");
    }, 3500);
  }

  function getEventBadgeInfo(category, name) {
    const cat = (category || "").toLowerCase();
    const nm = (name || "").toLowerCase();
    const isGem = cat.includes("hidden gem") || nm.includes("hidden gem");
    const isBreakfast = cat.includes("breakfast") || nm.includes("breakfast");
    const isLunch = cat.includes("lunch") || nm.includes("lunch");
    const isDinner = cat.includes("dinner") || nm.includes("dinner");
    const isDining = isBreakfast || isLunch || isDinner || cat.includes("dining") || cat.includes("restaurant") || cat.includes("food");

    if (isBreakfast) return { cls: "badge-meal", icon: "🍳", label: "Breakfast" };
    if (isLunch) return { cls: "badge-meal", icon: "🥗", label: "Lunch" };
    if (isDinner) return { cls: "badge-meal", icon: "🍽️", label: "Dinner" };
    if (isDining) return { cls: "badge-meal", icon: "🍴", label: category || "Dining" };
    if (isGem) return { cls: "badge-gem", icon: "💎", label: category || "Hidden Gem" };
    return { cls: "badge-sight", icon: "🏛️", label: category || "Sight" };
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
