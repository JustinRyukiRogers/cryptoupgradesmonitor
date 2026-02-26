document.addEventListener('DOMContentLoaded', () => {
    const feedContainer = document.getElementById('feed');
    const loadingEl = document.getElementById('loading');
    const emptyStateEl = document.getElementById('empty-state');
    const protocolFilter = document.getElementById('protocol-filter');
    const statusFilter = document.getElementById('status-filter');
    const certaintyFilter = document.getElementById('certainty-filter');
    const searchInput = document.getElementById('search-input');

    let allUpgrades = [];
    let uniqueProtocols = new Set();

    // Fetch data from Supabase REST API
    async function loadData() {
        try {
            // Replace with your actual Supabase URL and anon key when hosting
            const SUPABASE_URL = 'https://fsqjviyyfchoqiioefhk.supabase.co';
            const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZzcWp2aXl5ZmNob3FpaW9lZmhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwNjgwOTIsImV4cCI6MjA4NzY0NDA5Mn0.gI0GAua5hiIHO3ke_sbiZLeDVAjMlTwbtVc42P5m5L8';

            const response = await fetch(`${SUPABASE_URL}/rest/v1/upgrades?select=payload&order=timestamp.desc`, {
                headers: {
                    'apikey': SUPABASE_ANON_KEY,
                    'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
                }
            });

            if (!response.ok) throw new Error('Failed to fetch data from Supabase');
            const data = await response.json();

            // Extract the payload object from the Supabase rows
            const upgrades = data.map(row => row.payload);

            console.log(`Fetched ${upgrades.length} upgrades from Supabase`);
            allUpgrades = upgrades;

            // Extract unique protocols
            upgrades.forEach(u => {
                if (u.project) {
                    uniqueProtocols.add(u.project.toLowerCase());
                }
            });

            populateFilters();
            applyFilters(); // Initial render and sort
        } catch (error) {
            console.error('Error loading upgrades:', error);
            feedContainer.innerHTML = `<div class="empty-state"><p style="color: #ef4444;">Error loading data. Please ensure the python server is running from the root directory.</p></div>`;
        } finally {
            loadingEl.classList.add('hidden');
        }
    }

    // Populate protocol dropdown
    function populateFilters() {
        const sortedProtocols = Array.from(uniqueProtocols).sort();
        sortedProtocols.forEach(protocol => {
            const option = document.createElement('option');
            option.value = protocol;
            // Capitalize first letter
            option.textContent = protocol.charAt(0).toUpperCase() + protocol.slice(1);
            protocolFilter.appendChild(option);
        });
    }

    // Format timestamp
    function formatTimeAgo(dateString) {
        if (!dateString) return 'Unknown Time';

        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHrs = Math.floor(diffMin / 60);
        const diffDays = Math.floor(diffHrs / 24);

        if (diffSec < 60 && diffSec >= 0) return 'Just now';
        if (diffMin < 60 && diffMin >= 0) return `${diffMin}m ago`;
        if (diffHrs < 24 && diffHrs >= 0) return `${diffHrs}h ago`;
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7 && diffDays > 0) return `${diffDays}d ago`;

        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    }

    // formatStatus removed 

    function formatConfidenceLabel(score) {
        if (score == null) return 'Unknown';
        if (score >= 0.95) return 'Confirmed';
        if (score >= 0.7) return 'Imminent/Certain';
        if (score >= 0.4) return 'In Progress';
        if (score >= 0.2) return 'Speculative';
        return 'Irrelevant';
    }

    // Render feed
    function renderFeed(upgrades) {
        feedContainer.innerHTML = '';

        if (upgrades.length === 0) {
            emptyStateEl.classList.remove('hidden');
            return;
        }

        emptyStateEl.classList.add('hidden');

        // Use document fragment for performance
        const fragment = document.createDocumentFragment();

        upgrades.forEach(upgrade => {
            const card = document.createElement('a');
            card.href = upgrade.primary_source || '#';
            card.target = "_blank";
            card.rel = "noopener noreferrer";
            card.className = 'card';

            const timestampStr = formatTimeAgo(upgrade.timestamp);
            const confidenceLabel = formatConfidenceLabel(upgrade.confidence);
            const statusClass = confidenceLabel.toLowerCase().replace(/[\/\s]+/g, '-');
            const reasoning = upgrade.reasoning ? `<div class="card-body">${upgrade.reasoning}</div>` : '';

            let subtypesHtml = '';
            if (upgrade.affected_subtypes && upgrade.affected_subtypes.length > 0) {
                subtypesHtml = '<div class="subtypes-container">';
                subtypesHtml += `<div class="subtypes-header">
                    <div class="subtype-col-code">Sub-Type</div>
                    <div class="subtype-col-impact">Strength</div>
                    <div class="subtype-col-reason">Description</div>
                </div>`;

                upgrade.affected_subtypes.forEach(st => {
                    const impactClass = st.impact_type ? st.impact_type.toLowerCase().trim().replace(/\s+/g, '-') : 'unknown';
                    const confidenceHtml = st.confidence !== undefined
                        ? `<span class="subtype-confidence" title="Agent Confidence: ${st.confidence * 100}%">Strength: ${Math.round(st.confidence * 100)}%</span>`
                        : '';
                    const tokenHtml = st.token_context
                        ? `<span class="subtype-token">${st.token_context}</span>`
                        : '';

                    subtypesHtml += `
                        <div class="subtype-row">
                            <div class="subtype-col-code">
                                <span class="subtype-code">${st.subtype_code}</span>
                            </div>
                            <div class="subtype-col-impact">
                                <div class="impact-metrics-container">
                                    <span class="subtype-impact impact-${impactClass}">${st.impact_type}</span>
                                    ${confidenceHtml}
                                </div>
                            </div>
                            <div class="subtype-col-reason">
                                <div class="subtype-reason">${st.reason}</div>
                                ${tokenHtml ? `<div class="subtype-token-wrapper">${tokenHtml}</div>` : ''}
                            </div>
                        </div>
                    `;
                });
                subtypesHtml += '</div>';
            }

            card.innerHTML = `
                <div class="card-header">
                    <div class="protocol-pill-container">
                        <div class="protocol-logo"></div>
                        <span class="protocol-pill">${upgrade.project}</span>
                    </div>
                    <span class="timestamp">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        ${timestampStr}
                    </span>
                </div>
                <h2 class="card-title">${upgrade.headline}</h2>
                ${subtypesHtml}
                ${reasoning}
                <div class="card-meta">
                    <span class="status-badge status-${statusClass}">${confidenceLabel}</span>
                </div>
            `;

            fragment.appendChild(card);
        });

        feedContainer.appendChild(fragment);
    }

    // Filter logic
    function applyFilters() {
        const protocol = protocolFilter.value;
        const status = statusFilter.value;
        const minCertaintyStr = certaintyFilter.value;
        const minCertainty = minCertaintyStr === 'all' ? 0 : parseFloat(minCertaintyStr);
        const query = searchInput.value.toLowerCase();

        let filtered = [...allUpgrades];

        // Sort by timestamp descending
        filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        // Filter
        filtered = filtered.filter(u => {
            const p = u.project || '';
            const matchProtocol = protocol === 'all' || p.toLowerCase() === protocol;
            const h = u.headline || '';
            const r = u.reasoning || '';
            const matchQuery = query === '' || h.toLowerCase().includes(query) || r.toLowerCase().includes(query);

            // Match Status
            let matchStatus = true;
            if (status !== 'all') {
                const confScore = u.confidence !== undefined ? u.confidence : 0;
                if (status === 'confirmed') matchStatus = confScore >= 0.95;
                else if (status === 'imminent') matchStatus = confScore >= 0.7 && confScore < 0.95;
                else if (status === 'in-progress') matchStatus = confScore >= 0.4 && confScore < 0.7;
                else if (status === 'speculative') matchStatus = confScore >= 0.2 && confScore < 0.4;
            }

            // Match Functionality Certainty
            let matchCertainty = true;
            if (minCertainty > 0) {
                if (!u.affected_subtypes || u.affected_subtypes.length === 0) {
                    matchCertainty = false;
                } else {
                    // Check if *any* subtype meets the certainty threshold
                    matchCertainty = u.affected_subtypes.some(st => (st.confidence !== undefined ? st.confidence : 0) >= minCertainty);
                }
            }

            return matchProtocol && matchQuery && matchStatus && matchCertainty;
        });

        renderFeed(filtered);
    }

    protocolFilter.addEventListener('change', applyFilters);
    statusFilter.addEventListener('change', applyFilters);
    certaintyFilter.addEventListener('change', applyFilters);
    searchInput.addEventListener('input', applyFilters);

    // Initial load
    loadData();
});
