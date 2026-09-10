/**
 * Travel Itinerary Builder - Frontend Orchestration & UI Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const form = document.getElementById('itineraryForm');
    const originInput = document.getElementById('originInput');
    const destinationInput = document.getElementById('destinationInput');
    const departureDateInput = document.getElementById('departureDateInput');
    const budgetInput = document.getElementById('budgetInput');
    const daysInput = document.getElementById('daysInput');
    const customInterestInput = document.getElementById('customInterestInput');
    const addInterestBtn = document.getElementById('addInterestBtn');
    const interestTagsContainer = document.getElementById('interestTags');
    const interestsListText = document.getElementById('interestsListText');
    const submitBtn = document.getElementById('submitBtn');

    // Errors
    const originError = document.getElementById('originError');
    const destinationError = document.getElementById('destinationError');
    const departureDateError = document.getElementById('departureDateError');
    const budgetError = document.getElementById('budgetError');
    const daysError = document.getElementById('daysError');

    // Architecture Indicators
    const phaseFlight = document.getElementById('phaseFlight');
    const flightStatus = document.getElementById('flightStatus');
    const discoveryStatus = document.getElementById('discoveryStatus');
    const loopStatus = document.getElementById('loopStatus');
    const agentFlight = document.getElementById('agentFlight');
    const agentHotel = document.getElementById('agentHotel');
    const agentActivity = document.getElementById('agentActivity');
    const agentScheduler = document.getElementById('agentScheduler');
    const agentBudget = document.getElementById('agentBudget');
    const phaseDiscovery = document.getElementById('phaseDiscovery');
    const phaseLoop = document.getElementById('phaseLoop');
    const logsTerminal = document.getElementById('logsTerminal');

    // Results Elements
    const resultsSection = document.getElementById('resultsSection');
    const resDestination = document.getElementById('resDestination');
    const resTripTitle = document.getElementById('resTripTitle');
    const resTotalCost = document.getElementById('resTotalCost');
    const resBudget = document.getElementById('resBudget');
    const resVariance = document.getElementById('resVariance');
    const resApprovalBadge = document.getElementById('resApprovalBadge');
    const resFeedbackText = document.getElementById('resFeedbackText');
    const scheduleContainer = document.getElementById('scheduleContainer');
    const flightsList = document.getElementById('flightsList');
    const hotelsList = document.getElementById('hotelsList');
    const activitiesList = document.getElementById('activitiesList');
    const budgetTable = document.getElementById('budgetTable');
    const copyJsonBtn = document.getElementById('copyJsonBtn');

    let currentJsonState = null;

    // --------------------------------------------------------------------------
    // Interest Tags Management
    // --------------------------------------------------------------------------
    function getSelectedInterests() {
        const activeChips = interestTagsContainer.querySelectorAll('.tag-chip.active');
        return Array.from(activeChips).map(chip => chip.getAttribute('data-tag'));
    }

    function updateInterestsPreview() {
        const selected = getSelectedInterests();
        interestsListText.textContent = selected.length > 0 ? selected.join(', ') : 'None selected (defaults will apply)';
    }

    interestTagsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('tag-chip')) {
            e.target.classList.toggle('active');
            updateInterestsPreview();
        }
    });

    function addCustomInterest() {
        const val = customInterestInput.value.trim();
        if (val) {
            // Check duplicate
            const existing = Array.from(interestTagsContainer.querySelectorAll('.tag-chip'))
                .find(c => c.getAttribute('data-tag').toLowerCase() === val.toLowerCase());
            
            if (!existing) {
                const newChip = document.createElement('button');
                newChip.type = 'button';
                newChip.className = 'tag-chip active';
                newChip.setAttribute('data-tag', val);
                newChip.textContent = val;
                interestTagsContainer.appendChild(newChip);
            } else {
                existing.classList.add('active');
            }
            customInterestInput.value = '';
            updateInterestsPreview();
        }
    }

    addInterestBtn.addEventListener('click', addCustomInterest);
    customInterestInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addCustomInterest();
        }
    });

    // --------------------------------------------------------------------------
    // Logging Terminal
    // --------------------------------------------------------------------------
    function addLog(message, isHighlight = false) {
        const line = document.createElement('div');
        line.className = `log-line ${isHighlight ? 'highlight' : ''}`;
        const time = new Date().toLocaleTimeString();
        line.textContent = `[${time}] ${message}`;
        logsTerminal.appendChild(line);
        logsTerminal.scrollTop = logsTerminal.scrollHeight;
    }

    function clearLogs() {
        logsTerminal.innerHTML = '';
    }

    // --------------------------------------------------------------------------
    // Form Validation
    // --------------------------------------------------------------------------
    function clearErrors() {
        if (destinationError) { destinationError.style.display = 'none'; destinationError.textContent = ''; }
        if (budgetError) { budgetError.style.display = 'none'; budgetError.textContent = ''; }
        if (daysError) { daysError.style.display = 'none'; daysError.textContent = ''; }
    }

    function validateForm() {
        clearErrors();
        let isValid = true;

        const dest = destinationInput.value.trim();
        const budget = parseFloat(budgetInput.value);
        const days = parseInt(daysInput.value, 10);

        if (!dest) {
            destinationError.textContent = 'Please provide a destination (e.g. Kyoto, Japan).';
            destinationError.style.display = 'block';
            isValid = false;
        }

        if (isNaN(budget) || budget <= 0) {
            budgetError.textContent = 'Please enter a valid budget greater than $0.';
            budgetError.style.display = 'block';
            isValid = false;
        }

        if (isNaN(days) || days < 1 || days > 30) {
            daysError.textContent = 'Please enter trip duration between 1 and 30 days.';
            daysError.style.display = 'block';
            isValid = false;
        }

        return isValid;
    }

    // --------------------------------------------------------------------------
    // UI Animation for Pipeline Execution
    // --------------------------------------------------------------------------
    function setPipelineRunning(isRunning) {
        if (isRunning) {
            submitBtn.disabled = true;
            submitBtn.querySelector('.btn-text').style.display = 'none';
            submitBtn.querySelector('.btn-loader').style.display = 'inline-flex';

            // Reset visual states
            if (phaseDiscovery) phaseDiscovery.classList.add('active');
            if (phaseLoop) phaseLoop.classList.remove('active');

            if (discoveryStatus) { discoveryStatus.textContent = 'Running'; discoveryStatus.className = 'phase-status running'; }
            if (loopStatus) { loopStatus.textContent = 'Waiting'; loopStatus.className = 'phase-status'; }

            if (agentFlight) agentFlight.classList.add('active');
            if (agentHotel) agentHotel.classList.add('active');
            if (agentActivity) agentActivity.classList.add('active');
            if (agentScheduler) agentScheduler.classList.remove('active');
            if (agentBudget) agentBudget.classList.remove('active');
        } else {
            submitBtn.disabled = false;
            submitBtn.querySelector('.btn-text').style.display = 'inline-flex';
            submitBtn.querySelector('.btn-loader').style.display = 'none';

            if (discoveryStatus) { discoveryStatus.textContent = 'Completed'; discoveryStatus.className = 'phase-status done'; }
            if (loopStatus) { loopStatus.textContent = 'Completed'; loopStatus.className = 'phase-status done'; }

            if (agentFlight) agentFlight.classList.remove('active');
            if (agentHotel) agentHotel.classList.remove('active');
            if (agentActivity) agentActivity.classList.remove('active');
            if (agentScheduler) agentScheduler.classList.remove('active');
            if (agentBudget) agentBudget.classList.remove('active');

            if (phaseDiscovery) phaseDiscovery.classList.remove('active');
            if (phaseLoop) phaseLoop.classList.remove('active');
        }
    }

    // --------------------------------------------------------------------------
    // Form Submission & API Invocation
    // --------------------------------------------------------------------------
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!validateForm()) {
            addLog('Validation failed: Missing required fields.');
            return;
        }

        const payload = {
            city_of_origin: originInput ? originInput.value.trim() : '',
            destination: destinationInput.value.trim(),
            departure_date: departureDateInput ? departureDateInput.value : '',
            budget: parseFloat(budgetInput.value),
            days: parseInt(daysInput.value, 10),
            interests: getSelectedInterests()
        };

        clearLogs();
        const originTxt = payload.city_of_origin ? ` from ${payload.city_of_origin}` : '';
        addLog(`Initiating trip pipeline for ${payload.destination}${originTxt} (${payload.days} days, budget: $${payload.budget.toFixed(2)})`);
        setPipelineRunning(true);

        try {
            // Stage 1: Parallel Discovery Team
            setTimeout(() => {
                addLog('Phase 1: Parallel Discovery Team (FlightResearcher, HotelResearcher, ActivityPlanner) researching concurrently...');
            }, 600);

            // Stage 2: Optimization Room
            setTimeout(() => {
                if (phaseDiscovery) phaseDiscovery.classList.remove('active');
                if (discoveryStatus) { discoveryStatus.textContent = 'Done'; discoveryStatus.className = 'phase-status done'; }
                if (phaseLoop) phaseLoop.classList.add('active');
                if (loopStatus) { loopStatus.textContent = 'Running'; loopStatus.className = 'phase-status running'; }
                if (agentFlight) agentFlight.classList.remove('active');
                if (agentHotel) agentHotel.classList.remove('active');
                if (agentActivity) agentActivity.classList.remove('active');
                if (agentScheduler) agentScheduler.classList.add('active');
                if (agentBudget) agentBudget.classList.add('active');
                addLog('Phase 2: Optimization Room (Scheduler & BudgetEnforcer) synthesizing and refining schedule...');
            }, 1800);

            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                const errorMsg = result.error || 'Failed to generate itinerary.';
                addLog(`Error: ${errorMsg}`);
                alert(`Error: ${errorMsg}`);
                setPipelineRunning(false);
                return;
            }

            // Success: render pipeline results
            currentJsonState = result.data;
            if (result.data.logs) {
                result.data.logs.forEach(msg => addLog(msg));
            }
            addLog('Itinerary generation complete! Rendering schedule and metrics.', true);

            renderResults(result.data);
            setPipelineRunning(false);

            // Smooth scroll to results
            resultsSection.scrollIntoView({ behavior: 'smooth' });

            // Refresh history in background
            loadItinerariesHistory();

        } catch (err) {
            console.error('Request failed:', err);
            addLog(`Network or execution error: ${err.message}`);
            alert(`An unexpected error occurred: ${err.message}`);
            setPipelineRunning(false);
        }
    });

    // --------------------------------------------------------------------------
    // Results Rendering
    // --------------------------------------------------------------------------
    function renderResults(state) {
        const userInput = state.user_input || {};
        const research = state.raw_research || {};
        const itinerary = state.current_itinerary || {};
        const schedule = itinerary.schedule || [];
        const budget = parseFloat(userInput.budget) || 0.0;
        const totalDays = parseInt(userInput.days, 10) || 1;

        // 1. Normalize schedule
        let normalizedSchedule = [];
        if (Array.isArray(schedule) && schedule.length > 0) {
            const hasNestedEvents = schedule.every(item => item && Array.isArray(item.events));
            if (hasNestedEvents) {
                normalizedSchedule = schedule;
            } else {
                // Flat list of events
                const eventsPerDay = Math.max(1, Math.ceil(schedule.length / totalDays));
                for (let d = 1; d <= totalDays; d++) {
                    const dayEvents = schedule.slice((d - 1) * eventsPerDay, d * eventsPerDay);
                    normalizedSchedule.push({
                        day: d,
                        events: dayEvents.length > 0 ? dayEvents : [{
                            time: '10:00 AM',
                            title: `Day ${d} Local Exploration`,
                            category: 'sightseeing',
                            estimated_cost: 0.0,
                            description: 'Explore local sights, cafes, and neighborhoods.'
                        }]
                    });
                }
            }
        }

        // 2. Compute exact sum: Flights + Lodgings + Activities
        let totalFlights = 0;
        if (research.flights && Array.isArray(research.flights) && research.flights.length > 0) {
            totalFlights = parseFloat(research.flights[0].estimated_cost) || 0;
        }

        let totalLodging = 0;
        if (research.hotels && Array.isArray(research.hotels) && research.hotels.length > 0) {
            const perNight = parseFloat(research.hotels[0].price_per_night) || 0;
            totalLodging = perNight * totalDays;
        }

        const totalActivitiesCost = normalizedSchedule.reduce((sum, day) => {
            return sum + (day.events || []).reduce((dSum, ev) => dSum + (parseFloat(ev.estimated_cost) || 0), 0);
        }, 0);

        const computedSum = totalFlights + totalLodging + totalActivitiesCost;
        const totalCost = (computedSum > 0) ? Math.round(computedSum * 100) / 100 : (parseFloat(itinerary.total_estimated_cost) || 0.0);
        const isApproved = totalCost <= budget;
        const feedback = state.critic_feedback || (isApproved ? 'Itinerary within budget.' : 'Total cost exceeds budget limit.');

        // Header Metrics
        resDestination.textContent = userInput.destination;
        resTripTitle.textContent = `${totalDays}-Day Vacation Plan`;
        resTotalCost.textContent = `$${totalCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        resBudget.textContent = `$${budget.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

        const variance = budget - totalCost;
        if (variance >= 0) {
            resVariance.textContent = `+$${variance.toFixed(2)} (Under Budget)`;
            resVariance.style.color = 'var(--accent-emerald)';
        } else {
            resVariance.textContent = `-$${Math.abs(variance).toFixed(2)} (Over Budget)`;
            resVariance.style.color = 'var(--accent-rose)';
        }

        if (isApproved) {
            resApprovalBadge.textContent = 'Approved';
            resApprovalBadge.className = 'metric-badge approved';
        } else {
            resApprovalBadge.textContent = 'Exceeds Budget';
            resApprovalBadge.className = 'metric-badge over-budget';
        }

        resFeedbackText.textContent = feedback;

        // 3. Render Daily Schedule Cards
        scheduleContainer.innerHTML = '';

        if (normalizedSchedule.length === 0) {
            scheduleContainer.innerHTML = '<div class="day-card"><p class="text-muted">No schedule items generated.</p></div>';
        } else {
            normalizedSchedule.forEach((dayPlan, index) => {
                const dayCard = document.createElement('div');
                dayCard.className = 'day-card';
                const dayNum = dayPlan.day !== undefined ? dayPlan.day : (index + 1);

                const dayEvents = Array.isArray(dayPlan.events) ? dayPlan.events : [];
                const dayCost = dayEvents.reduce((acc, ev) => acc + (parseFloat(ev.estimated_cost) || 0), 0);

                let eventsHtml = dayEvents.map(ev => {
                    const categoryClass = (ev.category || 'landmark').toLowerCase().replace(/\s+/g, '-');
                    const costVal = parseFloat(ev.estimated_cost) || 0;
                    const costDisplay = costVal === 0 ? 'Free' : `$${costVal.toFixed(2)}`;

                    return `
                        <div class="event-item">
                            <div class="event-time">
                                <i class="fa-regular fa-clock"></i> ${escapeHtml(ev.time || 'All Day')}
                            </div>
                            <div class="event-content">
                                <h5>${escapeHtml(ev.title || 'Activity')}</h5>
                                <p>${escapeHtml(ev.description || '')}</p>
                                <span class="event-badge ${categoryClass}">${escapeHtml(ev.category || 'Activity')}</span>
                            </div>
                            <div class="event-cost">${costDisplay}</div>
                        </div>
                    `;
                }).join('');

                dayCard.innerHTML = `
                    <div class="day-header">
                        <div class="day-title"><i class="fa-solid fa-calendar-day"></i> Day ${dayNum}</div>
                        <div class="day-total">Daily Estimated: $${dayCost.toFixed(2)}</div>
                    </div>
                    <div class="events-list">
                        ${eventsHtml || '<p class="text-muted" style="padding: 1rem;">No events scheduled for this day.</p>'}
                    </div>
                `;
                scheduleContainer.appendChild(dayCard);
            });
        }

        // 2. Render Raw Research
        // Flights
        flightsList.innerHTML = '';
        (research.flights || []).forEach(fl => {
            const item = document.createElement('div');
            item.className = 'research-item-box';
            item.innerHTML = `
                <div class="research-item-header">
                    <span>${escapeHtml(fl.flight_name || 'Flight')} (${escapeHtml(fl.airline || 'Carrier')})</span>
                    <span class="research-item-price">$${parseFloat(fl.estimated_cost || 0).toFixed(2)}</span>
                </div>
                <div class="research-item-sub">Time: ${escapeHtml(fl.travel_time || 'N/A')} | ${escapeHtml(fl.notes || '')}</div>
            `;
            flightsList.appendChild(item);
        });

        // Hotels
        hotelsList.innerHTML = '';
        (research.hotels || []).forEach(ht => {
            const item = document.createElement('div');
            item.className = 'research-item-box';
            item.innerHTML = `
                <div class="research-item-header">
                    <span>${escapeHtml(ht.hotel_name || 'Hotel')} [${escapeHtml(ht.tier || 'mid-range')}]</span>
                    <span class="research-item-price">$${parseFloat(ht.price_per_night || 0).toFixed(2)}/nt</span>
                </div>
                <div class="research-item-sub">${escapeHtml(ht.safety_rating || '')} | ${escapeHtml(ht.location_notes || '')}</div>
            `;
            hotelsList.appendChild(item);
        });

        // Activities
        activitiesList.innerHTML = '';
        (research.activities || []).forEach(act => {
            const item = document.createElement('div');
            item.className = 'research-item-box';
            const cost = parseFloat(act.estimated_cost || 0);
            item.innerHTML = `
                <div class="research-item-header">
                    <span>${escapeHtml(act.activity_name || 'Activity')}</span>
                    <span class="research-item-price">${cost === 0 ? 'Free' : '$' + cost.toFixed(2)}</span>
                </div>
                <div class="research-item-sub">${escapeHtml(act.category || '')} (${act.duration_hours || 2}h) - ${escapeHtml(act.description || '')}</div>
            `;
            activitiesList.appendChild(item);
        });

        // 3. Render Budget Breakdown Table
        let totalFlightsBreakdown = 0;
        if (research.flights && research.flights.length > 0) {
            totalFlightsBreakdown = parseFloat(research.flights[0].estimated_cost) || 0;
        }

        let totalLodgingBreakdown = 0;
        if (research.hotels && research.hotels.length > 0) {
            const perNight = parseFloat(research.hotels[0].price_per_night) || 0;
            totalLodgingBreakdown = perNight * (userInput.days || 1);
        }

        const totalActivitiesCostBreakdown = normalizedSchedule.reduce((sum, day) => {
            return sum + (day.events || []).reduce((dSum, ev) => dSum + (parseFloat(ev.estimated_cost) || 0), 0);
        }, 0);

        budgetTable.innerHTML = `
            <div class="budget-row">
                <span><i class="fa-solid fa-plane"></i> Estimated Roundtrip Transit</span>
                <span>$${totalFlightsBreakdown.toFixed(2)}</span>
            </div>
            <div class="budget-row">
                <span><i class="fa-solid fa-hotel"></i> Lodging (${userInput.days} nights)</span>
                <span>$${totalLodgingBreakdown.toFixed(2)}</span>
            </div>
            <div class="budget-row">
                <span><i class="fa-solid fa-utensils"></i> Activities, Dining & Attractions</span>
                <span>$${totalActivitiesCostBreakdown.toFixed(2)}</span>
            </div>
            <div class="budget-row total">
                <span>Total Estimated Cost</span>
                <span>$${totalCost.toFixed(2)}</span>
            </div>
        `;

        resultsSection.style.display = 'block';
    }

    // --------------------------------------------------------------------------
    // Results Sub-Tab Navigation
    // --------------------------------------------------------------------------
    document.querySelectorAll('.results-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.results-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            const pane = document.getElementById(targetId);
            if (pane) pane.classList.add('active');
        });
    });

    // --------------------------------------------------------------------------
    // Copy JSON State
    // --------------------------------------------------------------------------
    if (copyJsonBtn) {
        copyJsonBtn.addEventListener('click', () => {
            if (!currentJsonState) return;
            navigator.clipboard.writeText(JSON.stringify(currentJsonState, null, 2))
                .then(() => {
                    const originalText = copyJsonBtn.innerHTML;
                    copyJsonBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                    setTimeout(() => {
                        copyJsonBtn.innerHTML = originalText;
                    }, 2000);
                })
                .catch(err => {
                    alert('Could not copy to clipboard: ' + err);
                });
        });
    }

    // ==========================================================================
    // ITINERARY HISTORY & EVENT LOGS (Two Coordinated Tables View)
    // ==========================================================================

    // Top Navigation Tabs
    const topNavBtns = document.querySelectorAll('.top-nav-btn');
    const appViews = document.querySelectorAll('.app-view');
    const navItineraryCount = document.getElementById('navItineraryCount');

    // Quick Stats Elements
    const statTotalItineraries = document.getElementById('statTotalItineraries');
    const statApprovedItineraries = document.getElementById('statApprovedItineraries');
    const statOverBudgetItineraries = document.getElementById('statOverBudgetItineraries');
    const statTotalEventsCount = document.getElementById('statTotalEventsCount');

    // Table 1 Elements
    const itinerariesTableBody = document.getElementById('itinerariesTableBody');
    const itinSearchInput = document.getElementById('itinSearchInput');
    const itinStatusFilter = document.getElementById('itinStatusFilter');
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');
    const visibleItinerariesCount = document.getElementById('visibleItinerariesCount');

    // Table 2 Elements
    const eventsTableBody = document.getElementById('eventsTableBody');
    const selectedItinSubtitle = document.getElementById('selectedItinSubtitle');
    const selectedItinMetaBar = document.getElementById('selectedItinMetaBar');
    const selMetaDestination = document.getElementById('selMetaDestination');
    const selMetaId = document.getElementById('selMetaId');
    const selMetaBudget = document.getElementById('selMetaBudget');
    const selMetaCost = document.getElementById('selMetaCost');
    const selMetaStatusBadge = document.getElementById('selMetaStatusBadge');
    const selMetaStarted = document.getElementById('selMetaStarted');
    const eventFilterTabs = document.getElementById('eventFilterTabs');
    const eventSearchInput = document.getElementById('eventSearchInput');
    const eventsTableWrapper = document.getElementById('eventsTableWrapper');
    const eventsLogsFeedWrapper = document.getElementById('eventsLogsFeedWrapper');
    const selectedItinLogsFeed = document.getElementById('selectedItinLogsFeed');
    const visibleEventsCount = document.getElementById('visibleEventsCount');

    // Counts on filter buttons
    const countAllEvents = document.getElementById('countAllEvents');
    const countModelEvents = document.getElementById('countModelEvents');
    const countToolEvents = document.getElementById('countToolEvents');
    const countPipelineEvents = document.getElementById('countPipelineEvents');

    // Modal Elements
    const payloadModal = document.getElementById('payloadModal');
    const modalEventTitle = document.getElementById('modalEventTitle');
    const modalPayloadMeta = document.getElementById('modalPayloadMeta');
    const modalPayloadCode = document.getElementById('modalPayloadCode');
    const copyPayloadBtn = document.getElementById('copyPayloadBtn');
    const closePayloadModalBtn = document.getElementById('closePayloadModalBtn');
    const closeModalActionBtn = document.getElementById('closeModalActionBtn');

    // State Variables
    let allItineraries = [];
    let selectedItinerary = null;
    let currentEventFilter = 'all';
    let currentEventSearch = '';

    // --------------------------------------------------------------------------
    // Top Navigation Switching
    // --------------------------------------------------------------------------
    topNavBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetViewId = btn.getAttribute('data-view');

            topNavBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            appViews.forEach(view => {
                if (view.id === targetViewId) {
                    view.style.display = 'block';
                    view.classList.add('active');
                } else {
                    view.style.display = 'none';
                    view.classList.remove('active');
                }
            });

            if (targetViewId === 'viewHistory') {
                loadItinerariesHistory();
            }
        });
    });

    // --------------------------------------------------------------------------
    // Fetch History & Itineraries
    // --------------------------------------------------------------------------
    async function loadItinerariesHistory() {
        try {
            const response = await fetch('/api/itineraries');
            const resData = await response.json();

            if (!response.ok || !resData.success) {
                console.error('Failed to load itineraries:', resData.error);
                if (itinerariesTableBody) {
                    itinerariesTableBody.innerHTML = `<tr><td colspan="10" class="text-center py-4 text-danger">Failed to load itineraries: ${escapeHtml(resData.error || 'Server error')}</td></tr>`;
                }
                return;
            }

            allItineraries = resData.data || [];
            updateHistoryStats(allItineraries);
            renderItinerariesTable();

            // Auto-select latest itinerary if none selected or if previously selected is updated
            if (allItineraries.length > 0) {
                if (!selectedItinerary) {
                    selectItinerary(allItineraries[0]);
                } else {
                    const updated = allItineraries.find(i => i.id === selectedItinerary.id || i.display_id === selectedItinerary.display_id);
                    selectItinerary(updated || allItineraries[0]);
                }
            } else {
                renderEmptyItinerariesState();
            }

        } catch (err) {
            console.error('Error fetching itineraries history:', err);
            if (itinerariesTableBody) {
                itinerariesTableBody.innerHTML = `<tr><td colspan="10" class="text-center py-4 text-danger">Error: ${escapeHtml(err.message)}</td></tr>`;
            }
        }
    }

    // --------------------------------------------------------------------------
    // Update Stats Summary
    // --------------------------------------------------------------------------
    function updateHistoryStats(itineraries) {
        const total = itineraries.length;
        if (navItineraryCount) navItineraryCount.textContent = total;
        if (statTotalItineraries) statTotalItineraries.textContent = total;

        const approved = itineraries.filter(i => i.budget_approved === true).length;
        const overBudget = itineraries.filter(i => i.budget_approved === false).length;
        const totalEvents = itineraries.reduce((sum, i) => sum + (i.event_count || (i.events ? i.events.length : 0)), 0);

        if (statApprovedItineraries) statApprovedItineraries.textContent = approved;
        if (statOverBudgetItineraries) statOverBudgetItineraries.textContent = overBudget;
        if (statTotalEventsCount) statTotalEventsCount.textContent = totalEvents.toLocaleString();
    }

    // --------------------------------------------------------------------------
    // Render Table 1: Created Itineraries
    // --------------------------------------------------------------------------
    function renderItinerariesTable() {
        if (!itinerariesTableBody) return;

        const searchTerm = (itinSearchInput ? itinSearchInput.value : '').toLowerCase().trim();
        const statusFilter = (itinStatusFilter ? itinStatusFilter.value : 'all');

        const filtered = allItineraries.filter(itin => {
            // Search filter
            const dest = (itin.destination || '').toLowerCase();
            const orig = (itin.origin || '').toLowerCase();
            const idStr = (itin.display_id || itin.id || '').toLowerCase();
            const matchesSearch = !searchTerm || dest.includes(searchTerm) || orig.includes(searchTerm) || idStr.includes(searchTerm);

            // Status filter
            let matchesStatus = true;
            if (statusFilter === 'approved') {
                matchesStatus = itin.budget_approved === true;
            } else if (statusFilter === 'over_budget') {
                matchesStatus = itin.budget_approved === false;
            } else if (statusFilter === 'fallback') {
                matchesStatus = itin.status === 'Fallback';
            }

            return matchesSearch && matchesStatus;
        });

        if (visibleItinerariesCount) {
            visibleItinerariesCount.textContent = filtered.length;
        }

        if (filtered.length === 0) {
            itinerariesTableBody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center py-4 text-muted">
                        <i class="fa-solid fa-search"></i> No itineraries found matching the current filters.
                    </td>
                </tr>
            `;
            return;
        }

        itinerariesTableBody.innerHTML = filtered.map(itin => {
            const isSelected = selectedItinerary && (selectedItinerary.id === itin.id || selectedItinerary.display_id === itin.display_id);
            const dateStr = formatDate(itin.start_time);
            const budgetVal = itin.budget ? `$${parseFloat(itin.budget).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-';
            const costVal = itin.total_estimated_cost ? `$${parseFloat(itin.total_estimated_cost).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-';
            const evCount = itin.event_count || (itin.events ? itin.events.length : 0);

            let statusBadge = '<span class="status-tag in-progress"><i class="fa-solid fa-spinner fa-spin"></i> In Progress</span>';
            if (itin.status === 'Fallback') {
                statusBadge = '<span class="status-tag fallback"><i class="fa-solid fa-shield-halved"></i> Fallback</span>';
            } else if (itin.budget_approved === true) {
                statusBadge = '<span class="status-tag approved"><i class="fa-solid fa-check"></i> Approved</span>';
            } else if (itin.budget_approved === false) {
                statusBadge = '<span class="status-tag over-budget"><i class="fa-solid fa-triangle-exclamation"></i> Over Budget</span>';
            }

            const originHtml = itin.origin ? `<div class="origin-sub"><i class="fa-solid fa-plane-departure"></i> ${escapeHtml(itin.origin)}</div>` : '<span class="text-muted">-</span>';

            return `
                <tr class="${isSelected ? 'selected-row' : ''}" data-id="${escapeHtml(itin.id || '')}">
                    <td><span class="badge-code">${escapeHtml(itin.display_id || itin.id || 'ITIN')}</span></td>
                    <td><span class="date-text"><i class="fa-regular fa-clock"></i> ${dateStr}</span></td>
                    <td>
                        <div class="dest-text">${escapeHtml(itin.destination || 'Unknown')}</div>
                    </td>
                    <td>${originHtml}</td>
                    <td><strong>${itin.days || 1}</strong> days</td>
                    <td><strong>${budgetVal}</strong></td>
                    <td><strong>${costVal}</strong></td>
                    <td>${statusBadge}</td>
                    <td><span class="badge-code" style="color: var(--accent-emerald);">${evCount} evts</span></td>
                    <td>
                        <button class="btn-sm btn-outline select-itin-btn" data-id="${escapeHtml(itin.id || '')}">
                            ${isSelected ? '<i class="fa-solid fa-circle-check"></i> Selected' : '<i class="fa-solid fa-arrow-right"></i> View'}
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        // Add Click Events to rows and buttons
        itinerariesTableBody.querySelectorAll('tr').forEach(row => {
            row.addEventListener('click', (e) => {
                const id = row.getAttribute('data-id');
                const targetItin = allItineraries.find(i => (i.id === id || i.display_id === id));
                if (targetItin) {
                    selectItinerary(targetItin);
                }
            });
        });
    }

    function renderEmptyItinerariesState() {
        if (itinerariesTableBody) {
            itinerariesTableBody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center py-4 text-muted">
                        No itineraries have been generated yet. Go to <a href="#" id="linkGoToPlanner" style="color: var(--accent-cyan);">Trip Planner</a> to generate your first itinerary!
                    </td>
                </tr>
            `;
            const link = document.getElementById('linkGoToPlanner');
            if (link) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    document.getElementById('btnViewPlanner').click();
                });
            }
        }
    }

    // --------------------------------------------------------------------------
    // Select Itinerary & Populate Table 2
    // --------------------------------------------------------------------------
    function selectItinerary(itin) {
        selectedItinerary = itin;

        // Highlight selected row in Table 1
        renderItinerariesTable();

        // Update Metadata Bar in Table 2
        if (selectedItinMetaBar) {
            selectedItinMetaBar.style.display = 'flex';
        }
        if (selectedItinSubtitle) {
            selectedItinSubtitle.textContent = `Displaying full generation stream for ${itin.destination} (${itin.display_id || itin.id})`;
        }
        if (selMetaDestination) {
            selMetaDestination.textContent = `${itin.destination}${itin.origin ? ` (from ${itin.origin})` : ''} - ${itin.days || 1} Days`;
        }
        if (selMetaId) {
            selMetaId.textContent = itin.display_id || itin.id;
        }
        if (selMetaBudget) {
            selMetaBudget.textContent = itin.budget ? `$${parseFloat(itin.budget).toFixed(2)}` : '-';
        }
        if (selMetaCost) {
            selMetaCost.textContent = itin.total_estimated_cost ? `$${parseFloat(itin.total_estimated_cost).toFixed(2)}` : '-';
        }
        if (selMetaStarted) {
            selMetaStarted.textContent = formatDate(itin.start_time);
        }

        if (selMetaStatusBadge) {
            if (itin.status === 'Fallback') {
                selMetaStatusBadge.textContent = 'Fallback';
                selMetaStatusBadge.className = 'metric-badge fallback';
            } else if (itin.budget_approved === true) {
                selMetaStatusBadge.textContent = 'Approved';
                selMetaStatusBadge.className = 'metric-badge approved';
            } else if (itin.budget_approved === false) {
                selMetaStatusBadge.textContent = 'Over Budget';
                selMetaStatusBadge.className = 'metric-badge over-budget';
            } else {
                selMetaStatusBadge.textContent = 'In Progress';
                selMetaStatusBadge.className = 'metric-badge';
            }
        }

        // Update Sub-Tab counts
        updateEventCounts(itin.events || []);

        // Render Events Table
        renderEventsTable();

        // Render Activity Logs Feed
        renderSelectedItinLogs(itin);
    }

    // --------------------------------------------------------------------------
    // Update Event Counts
    // --------------------------------------------------------------------------
    function updateEventCounts(events) {
        const allCount = events.length;
        const modelCount = events.filter(e => ['model_request', 'model_response'].includes(e.event_type)).length;
        const toolCount = events.filter(e => ['tool_call', 'tool_invocation', 'tool_execution', 'tool_response', 'skill_invocation', 'skill_response'].includes(e.event_type)).length;
        const pipeCount = events.filter(e => ['pipeline_start', 'pipeline_complete', 'pipeline_fallback'].includes(e.event_type)).length;

        if (countAllEvents) countAllEvents.textContent = allCount;
        if (countModelEvents) countModelEvents.textContent = modelCount;
        if (countToolEvents) countToolEvents.textContent = toolCount;
        if (countPipelineEvents) countPipelineEvents.textContent = pipeCount;
    }

    // --------------------------------------------------------------------------
    // Render Table 2: Events Table
    // --------------------------------------------------------------------------
    function renderEventsTable() {
        if (!selectedItinerary || !eventsTableBody) return;

        const events = selectedItinerary.events || [];
        const searchVal = currentEventSearch.toLowerCase().trim();

        const filteredEvents = events.filter((ev, idx) => {
            const etype = ev.event_type || '';
            const agent = (ev.agent || '').toLowerCase();
            const summary = (ev.summary || '').toLowerCase();
            const detailsStr = JSON.stringify(ev.details || {}).toLowerCase();

            // Sub-tab filter
            let matchesTab = true;
            if (currentEventFilter === 'models') {
                matchesTab = ['model_request', 'model_response'].includes(etype);
            } else if (currentEventFilter === 'tools') {
                matchesTab = ['tool_call', 'tool_invocation', 'tool_execution', 'tool_response', 'skill_invocation', 'skill_response'].includes(etype);
            } else if (currentEventFilter === 'pipeline') {
                matchesTab = ['pipeline_start', 'pipeline_complete', 'pipeline_fallback'].includes(etype);
            }

            // Search filter
            const matchesSearch = !searchVal || 
                etype.includes(searchVal) || 
                agent.includes(searchVal) || 
                summary.includes(searchVal) || 
                detailsStr.includes(searchVal);

            return matchesTab && matchesSearch;
        });

        if (visibleEventsCount) {
            visibleEventsCount.textContent = filteredEvents.length;
        }

        if (filteredEvents.length === 0) {
            eventsTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-muted">
                        <i class="fa-solid fa-filter"></i> No events found for the selected filter or search term.
                    </td>
                </tr>
            `;
            return;
        }

        eventsTableBody.innerHTML = filteredEvents.map((ev, index) => {
            const timeStr = formatEventTime(ev.timestamp);
            const etype = ev.event_type || 'unknown';
            const agent = ev.agent || 'System';
            const summary = ev.summary || formatEventFallbackSummary(ev);

            let agentIcon = 'fa-robot';
            if (agent.includes('Flight')) agentIcon = 'fa-plane-departure';
            else if (agent.includes('Hotel')) agentIcon = 'fa-hotel';
            else if (agent.includes('Activity')) agentIcon = 'fa-map-location-dot';
            else if (agent.includes('Scheduler')) agentIcon = 'fa-calendar-check';
            else if (agent.includes('Budget')) agentIcon = 'fa-scale-balanced';
            else if (agent === 'System') agentIcon = 'fa-gear';

            return `
                <tr data-event-index="${index}">
                    <td><span class="badge-code">${index + 1}</span></td>
                    <td><span class="date-text"><i class="fa-regular fa-clock"></i> ${timeStr}</span></td>
                    <td>
                        <span class="ev-type-badge ${escapeHtml(etype)}">
                            ${escapeHtml(etype)}
                        </span>
                    </td>
                    <td>
                        <span class="agent-source-tag">
                            <i class="fa-solid ${agentIcon}"></i>
                            ${escapeHtml(agent)}
                        </span>
                    </td>
                    <td>
                        <div class="event-summary-text">${escapeHtml(summary)}</div>
                    </td>
                    <td>
                        <button class="btn-sm btn-outline inspect-event-btn" data-event-idx="${index}">
                            <i class="fa-solid fa-code"></i> Payload
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        // Attach Payload Inspector Click Handlers
        eventsTableBody.querySelectorAll('.inspect-event-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.getAttribute('data-event-idx'), 10);
                const ev = filteredEvents[idx];
                if (ev) {
                    openPayloadModal(ev);
                }
            });
        });
    }

    function formatEventFallbackSummary(ev) {
        if (ev.details && ev.details.tool_name) {
            return `Tool [${ev.details.tool_name}] interaction`;
        }
        return `Event ${ev.event_type} logged`;
    }

    // --------------------------------------------------------------------------
    // Render Activity Logs Feed for Selected Itinerary
    // --------------------------------------------------------------------------
    function renderSelectedItinLogs(itin) {
        if (!selectedItinLogsFeed) return;

        const logs = itin.logs || [];
        if (logs.length === 0) {
            selectedItinLogsFeed.innerHTML = '<div class="log-line text-muted">No textual logs recorded for this itinerary run.</div>';
            return;
        }

        selectedItinLogsFeed.innerHTML = logs.map(msg => {
            const isHighlight = msg.includes('complete') || msg.includes('Starting') || msg.includes('Approved');
            return `<div class="log-line ${isHighlight ? 'highlight' : ''}">${escapeHtml(msg)}</div>`;
        }).join('');
    }

    // --------------------------------------------------------------------------
    // Sub-Tab Filter Handling in Table 2
    // --------------------------------------------------------------------------
    if (eventFilterTabs) {
        eventFilterTabs.querySelectorAll('.event-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                eventFilterTabs.querySelectorAll('.event-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const filter = btn.getAttribute('data-filter');
                currentEventFilter = filter;

                if (filter === 'logs_feed') {
                    if (eventsTableWrapper) eventsTableWrapper.style.display = 'none';
                    if (eventsLogsFeedWrapper) eventsLogsFeedWrapper.style.display = 'block';
                } else {
                    if (eventsTableWrapper) eventsTableWrapper.style.display = 'block';
                    if (eventsLogsFeedWrapper) eventsLogsFeedWrapper.style.display = 'none';
                    renderEventsTable();
                }
            });
        });
    }

    // Search and filter listeners
    if (itinSearchInput) {
        itinSearchInput.addEventListener('input', () => renderItinerariesTable());
    }
    if (itinStatusFilter) {
        itinStatusFilter.addEventListener('change', () => renderItinerariesTable());
    }
    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener('click', () => {
            refreshHistoryBtn.querySelector('i').classList.add('fa-spin');
            loadItinerariesHistory().finally(() => {
                setTimeout(() => {
                    refreshHistoryBtn.querySelector('i').classList.remove('fa-spin');
                }, 500);
            });
        });
    }
    if (eventSearchInput) {
        eventSearchInput.addEventListener('input', (e) => {
            currentEventSearch = e.target.value;
            renderEventsTable();
        });
    }

    // --------------------------------------------------------------------------
    // Payload Inspection Modal
    // --------------------------------------------------------------------------
    let currentModalPayload = null;

    function openPayloadModal(eventObj) {
        if (!payloadModal) return;
        currentModalPayload = eventObj.raw_event || eventObj;

        if (modalEventTitle) {
            modalEventTitle.textContent = `Event: ${eventObj.event_type} (${eventObj.agent || 'System'})`;
        }
        if (modalPayloadMeta) {
            modalPayloadMeta.innerHTML = `
                <strong>Timestamp:</strong> ${formatDate(eventObj.timestamp)} | 
                <strong>Type:</strong> <span class="ev-type-badge ${escapeHtml(eventObj.event_type)}">${escapeHtml(eventObj.event_type)}</span> | 
                <strong>Agent:</strong> ${escapeHtml(eventObj.agent || 'System')}
            `;
        }
        if (modalPayloadCode) {
            modalPayloadCode.textContent = JSON.stringify(currentModalPayload, null, 2);
        }

        payloadModal.style.display = 'flex';
    }

    function closePayloadModal() {
        if (payloadModal) {
            payloadModal.style.display = 'none';
        }
    }

    if (closePayloadModalBtn) closePayloadModalBtn.addEventListener('click', closePayloadModal);
    if (closeModalActionBtn) closeModalActionBtn.addEventListener('click', closePayloadModal);
    if (payloadModal) {
        payloadModal.addEventListener('click', (e) => {
            if (e.target === payloadModal) closePayloadModal();
        });
    }

    if (copyPayloadBtn) {
        copyPayloadBtn.addEventListener('click', () => {
            if (!currentModalPayload) return;
            navigator.clipboard.writeText(JSON.stringify(currentModalPayload, null, 2))
                .then(() => {
                    const original = copyPayloadBtn.innerHTML;
                    copyPayloadBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                    setTimeout(() => { copyPayloadBtn.innerHTML = original; }, 2000);
                })
                .catch(err => alert('Failed to copy: ' + err));
        });
    }

    // Helper Date Formatters
    function formatDate(isoStr) {
        if (!isoStr) return '-';
        try {
            const d = new Date(isoStr);
            return d.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return String(isoStr).substring(0, 19);
        }
    }

    function formatEventTime(isoStr) {
        if (!isoStr) return '-';
        try {
            const d = new Date(isoStr);
            return d.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                fractionalSecondDigits: 3
            });
        } catch {
            return String(isoStr).substring(11, 23);
        }
    }

    // Initial Load of History on Page Load
    loadItinerariesHistory();

    // Utility: HTML Escaping
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
