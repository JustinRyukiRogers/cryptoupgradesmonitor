document.addEventListener('DOMContentLoaded', () => {
    const feedContainer = document.getElementById('feed');
    const loadingEl = document.getElementById('loading');
    const emptyStateEl = document.getElementById('empty-state');
    const protocolFilter = document.getElementById('protocol-filter');
    const searchInput = document.getElementById('search-input');

    let allUpgrades = [];
    let uniqueProtocols = new Set();

    // Fetch data
    async function loadData() {
        try {
            // Adding a cache buster for local development to assure fresh data from /data/upgrades.json
            const response = await fetch(`/data/upgrades.json?t=${new Date().getTime()}`);
            if (!response.ok) throw new Error('Failed to fetch data');
            const data = await response.json();

            // Log total fetched
            console.log(`Fetched ${data.length} upgrades`);

            // Populate our list
            allUpgrades = data;

            // Extract unique protocols
            data.forEach(u => {
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

    function formatStatus(status) {
        if (!status) return 'Unknown';
        return status.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }

    function formatType(type) {
        if (!type) return 'Unknown';
        return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
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
            const statusClass = (upgrade.status || 'unknown').toLowerCase();
            const confidence = upgrade.confidence != null ? (upgrade.confidence * 100).toFixed(0) : '0';
            const reasoning = upgrade.reasoning ? `<div class="card-body">${upgrade.reasoning}</div>` : '';

            card.innerHTML = `
                <div class="card-header">
                    <span class="protocol-pill">${upgrade.project}</span>
                    <span class="timestamp">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        ${timestampStr}
                    </span>
                </div>
                <h2 class="card-title">${upgrade.headline}</h2>
                ${reasoning}
                <div class="card-meta">
                    <div class="meta-item">
                        <span class="status-indicator status-${statusClass}"></span>
                        <span>${formatStatus(upgrade.status)}</span>
                    </div>
                    <div class="meta-item" title="Upgrade Type">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>
                        <span>${formatType(upgrade.upgrade_type)}</span>
                    </div>
                    <div class="meta-item" title="Agent Confidence">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                        <span>Conf: ${confidence}%</span>
                    </div>
                </div>
            `;

            fragment.appendChild(card);
        });

        feedContainer.appendChild(fragment);
    }

    // Filter logic
    function applyFilters() {
        const protocol = protocolFilter.value;
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
            return matchProtocol && matchQuery;
        });

        renderFeed(filtered);
    }

    protocolFilter.addEventListener('change', applyFilters);
    searchInput.addEventListener('input', applyFilters);

    // Initial load
    loadData();
});
