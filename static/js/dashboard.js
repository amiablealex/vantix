/**
 * Vantix Dashboard - Main JavaScript
 * Master filter coordination and data loading - NOW FILTERS STATS TOO
 */

// Extract league code from URL for API calls
const pathParts = window.location.pathname.split('/').filter(p => p);
const leagueCode = pathParts.length > 0 ? pathParts[0] : '';

console.log('League code extracted:', leagueCode);

// Global state
window.VantixDashboard = {
    teams: [],
    selectedTeams: new Set(), // Single master selection
    leagueCode: leagueCode,
    colors: [
        '#A8DADC', // Powder blue
        '#F1C6B7', // Dusty pink
        '#B8D4B8', // Sage green
        '#D4B5D4', // Lavender
        '#F4D8A8', // Peach
        '#E8B4C8', // Rose
        '#B8C4D4', // Periwinkle
        '#D4C4A8', // Sand
        '#C8D4B8', // Mint
        '#D4A8B8'  // Mauve
    ],
    charts: {
        points: null,
        position: null,
        form: null,
        distribution: null
    }
};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Vantix Dashboard initializing...');
    
    // Get teams from server data
    if (window.FPL_DATA && window.FPL_DATA.teams) {
        VantixDashboard.teams = window.FPL_DATA.teams;
        
        // Select all teams by default
        VantixDashboard.teams.forEach(team => {
            VantixDashboard.selectedTeams.add(team.entry_id);
        });
        
        // Initialize master filter first
        initializeMasterFilter();
        
        // Initialize components - add delay to ensure DOM is ready
        setTimeout(() => {
            initializeStats();
            initializeAllCharts();
            initializeTransfers();
            initializeAnalytics();
            initializeNewFeatures(); // NEW FEATURES
            setupRefreshButton();
        }, 100);
        
        console.log('Vantix Dashboard initialized successfully!');
    } else {
        console.error('No team data available');
        showError('Failed to load team data');
    }
});

// Initialize master filter
function initializeMasterFilter() {
    const container = document.getElementById('masterTeamPills');
    
    container.innerHTML = VantixDashboard.teams.map((team, index) => {
        const color = getTeamColor(index);
        const isSelected = VantixDashboard.selectedTeams.has(team.entry_id);
        
        return `
            <div class="team-pill ${isSelected ? 'selected' : ''}" 
                 data-team-id="${team.entry_id}">
                <span class="team-pill-color" style="background-color: ${color}"></span>
                <span class="team-pill-name">${team.team_name}</span>
            </div>
        `;
    }).join('');
    
    // Set up event listeners
    setupMasterFilterListeners();
}

// Setup master filter event listeners
function setupMasterFilterListeners() {
    // Team pill clicks
    document.querySelectorAll('#masterTeamPills .team-pill').forEach(pill => {
        pill.addEventListener('click', function() {
            const teamId = parseInt(this.dataset.teamId);
            
            if (VantixDashboard.selectedTeams.has(teamId)) {
                VantixDashboard.selectedTeams.delete(teamId);
                this.classList.remove('selected');
            } else {
                VantixDashboard.selectedTeams.add(teamId);
                this.classList.add('selected');
            }
            
            // Update everything including stats
            updateAllVisualizations();
        });
    });
    
    // Select All button
    document.getElementById('selectAllMaster').addEventListener('click', function() {
        VantixDashboard.teams.forEach(team => {
            VantixDashboard.selectedTeams.add(team.entry_id);
        });
        
        document.querySelectorAll('#masterTeamPills .team-pill').forEach(pill => {
            pill.classList.add('selected');
        });
        
        updateAllVisualizations();
    });
    
    // Deselect All button
    document.getElementById('deselectAllMaster').addEventListener('click', function() {
        VantixDashboard.selectedTeams.clear();
        
        document.querySelectorAll('#masterTeamPills .team-pill').forEach(pill => {
            pill.classList.remove('selected');
        });
        
        updateAllVisualizations();
    });
}

// Update all visualizations when filter changes
function updateAllVisualizations() {
    initializeStats(); // NOW UPDATES STATS TOO
    initializeAllCharts();
    initializeTransfers();
    initializeAnalytics();
    initializeNewFeatures(); // NEW FEATURES
}

// Load and display stats - NOW FILTERED BY SELECTED TEAMS
function initializeStats() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/${leagueCode}/stats?${queryString}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('stat-leader-value').textContent = data.current_leader.points;
            document.getElementById('stat-leader-detail').textContent = data.current_leader.team;
            
            document.getElementById('stat-goals-value').textContent = data.most_goals.goals;
            document.getElementById('stat-goals-detail').textContent = data.most_goals.team;
            
            document.getElementById('stat-cs-value').textContent = data.most_clean_sheets.clean_sheets;
            document.getElementById('stat-cs-detail').textContent = data.most_clean_sheets.team;
            
            document.getElementById('stat-highest-value').textContent = data.highest_gameweek.points;
            document.getElementById('stat-highest-detail').textContent = 
                `${data.highest_gameweek.team} (GW${data.highest_gameweek.gameweek})`;
        })
        .catch(error => {
            console.error('Error loading stats:', error);
        });
}

// Initialize all charts
function initializeAllCharts() {
    initializeCumulativePointsChart();
    initializeLeaguePositionChart();
    initializeFormChart();
    initializeDistributionChart();
}

// Load and display transfers
function initializeTransfers() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/${leagueCode}/recent-transfers?${queryString}`)
        .then(response => response.json())
        .then(data => {
            if (data.gameweek) {
                document.getElementById('transfersGameweek').textContent = `GW ${data.gameweek}`;
            }
            displayTransfers(data.transfers);
        })
        .catch(error => {
            console.error('Error loading transfers:', error);
            document.getElementById('transfersList').innerHTML = 
                '<p class="text-center" style="color: var(--color-text-lighter);">Failed to load transfers</p>';
        });
}

// Display transfers in the UI
function displayTransfers(transfers) {
    const container = document.getElementById('transfersList');
    
    if (transfers.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No teams selected</p>';
        return;
    }
    
    container.innerHTML = transfers.map(transfer => {
        // Determine badge display
        let badge = '';
        
        if (transfer.chip_used) {
            // Chip used - show chip name with special styling
            const chipDisplayName = getChipBadgeText(transfer.chip_used);
            badge = `<span class="transfer-badge transfer-badge-chip">${chipDisplayName}</span>`;
        } else if (transfer.transfer_cost > 0) {
            // Points hit taken
            badge = `<span class="transfer-badge transfer-badge-hit">-${transfer.transfer_cost} pts</span>`;
        }
        
        if (transfer.count === 0) {
            return `
                <div class="transfer-item">
                    <div class="transfer-team">
                        ${transfer.team_name}
                        ${badge}
                    </div>
                    <div class="transfer-details no-transfers">No transfers made this week</div>
                </div>
            `;
        } else {
            const transferDetails = transfer.transfers_out.map((playerOut, index) => {
                const playerIn = transfer.transfers_in[index] || 'Unknown';
                return `
                    <span class="transfer-out">${playerOut}</span>
                    <span class="transfer-arrow">→</span>
                    <span class="transfer-in">${playerIn}</span>
                `;
            }).join('<br>');
            
            return `
                <div class="transfer-item">
                    <div class="transfer-team">
                        ${transfer.team_name}
                        ${badge}
                    </div>
                    <div class="transfer-details">${transferDetails}</div>
                </div>
            `;
        }
    }).join('');
}

// Helper function to get chip badge text
function getChipBadgeText(chipName) {
    const chipLower = chipName.toLowerCase();
    if (chipLower.includes('wildcard') || chipLower === 'wildcard') return 'Wildcard';
    if (chipLower.includes('bench') || chipLower === 'bboost') return 'Bench Boost';
    if (chipLower.includes('captain') || chipLower === '3xc') return 'Triple Captain';
    if (chipLower.includes('free') || chipLower === 'freehit') return 'Free Hit';
    return chipName;
}

// Initialize analytics sections
function initializeAnalytics() {
    initializeComparison();
    initializeBiggestMovers();
}

// Initialize team comparison
function initializeComparison() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    console.log('Initializing comparison with teams:', selectedTeams);
    
    fetch(`/api/${leagueCode}/team-comparison?${queryString}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Comparison data received:', data);
            displayComparison(data.teams);
        })
        .catch(error => {
            console.error('Error loading comparison:', error);
            document.getElementById('comparisonGrid').innerHTML = 
                '<p class="text-center" style="color: var(--color-text-lighter);">Failed to load comparison data</p>';
        });
}

// Display team comparison with min/max highlighting
function displayComparison(teams) {
    const container = document.getElementById('comparisonGrid');
    
    if (!teams || teams.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No teams selected</p>';
        return;
    }
    
    // Calculate min/max for each stat
    const stats = {
        total_points: { values: teams.map(t => t.total_points), higherIsBetter: true },
        avg_points: { values: teams.map(t => t.avg_points), higherIsBetter: true },
        highest_gw: { values: teams.map(t => t.highest_gw), higherIsBetter: true },
        lowest_gw: { values: teams.map(t => t.lowest_gw), higherIsBetter: true },
        total_transfers: { values: teams.map(t => t.total_transfers), higherIsBetter: true },
        hits_taken: { values: teams.map(t => t.hits_taken), higherIsBetter: false },
        chips_used: { values: teams.map(t => t.chips_used), higherIsBetter: false }
    };
    
    // Helper function to get highlight class
    function getHighlightClass(value, statKey) {
        const stat = stats[statKey];
        const max = Math.max(...stat.values);
        const min = Math.min(...stat.values);
        
        if (stat.higherIsBetter) {
            if (value === max) return 'highlight-best';
            if (value === min) return 'highlight-worst';
        } else {
            if (value === min) return 'highlight-best';
            if (value === max) return 'highlight-worst';
        }
        return '';
    }
    
    container.innerHTML = teams.map(team => `
        <div class="comparison-card">
            <div class="comparison-team-name">${team.team_name}</div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Total Points</span>
                <span class="comparison-stat-value ${getHighlightClass(team.total_points, 'total_points')}">${team.total_points}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Avg Per GW</span>
                <span class="comparison-stat-value ${getHighlightClass(team.avg_points, 'avg_points')}">${team.avg_points}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Highest GW</span>
                <span class="comparison-stat-value ${getHighlightClass(team.highest_gw, 'highest_gw')}">${team.highest_gw}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Lowest GW</span>
                <span class="comparison-stat-value ${getHighlightClass(team.lowest_gw, 'lowest_gw')}">${team.lowest_gw}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Total Transfers</span>
                <span class="comparison-stat-value ${getHighlightClass(team.total_transfers, 'total_transfers')}">${team.total_transfers}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Hits Taken</span>
                <span class="comparison-stat-value ${getHighlightClass(team.hits_taken, 'hits_taken')}">
                    ${team.hits_taken}${team.hits_taken > 0 ? ` (-${team.hits_taken * 4} pts)` : ''}
                </span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Chips Used</span>
                <span class="comparison-stat-value ${getHighlightClass(team.chips_used, 'chips_used')}">${team.chips_used}</span>
            </div>
        </div>
    `).join('');
}

// Initialize biggest movers
function initializeBiggestMovers() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    console.log('Initializing biggest movers with teams:', selectedTeams);
    
    fetch(`/api/${leagueCode}/biggest-movers?${queryString}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Movers data received:', data);
            displayBiggestMovers(data);
        })
        .catch(error => {
            console.error('Error loading movers:', error);
            document.getElementById('moversGrid').innerHTML = 
                '<p class="text-center" style="color: var(--color-text-lighter);">Failed to load movers data</p>';
        });
}

// Display biggest movers
function displayBiggestMovers(data) {
    const container = document.getElementById('moversGrid');
    
    if (!data || (!data.climbers && !data.fallers)) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No data available</p>';
        return;
    }
    
    const climbersHTML = data.climbers && data.climbers.length > 0 ? data.climbers.map(mover => `
        <div class="mover-item">
            <span class="mover-team">${mover.team_name}</span>
            <span class="mover-change up">↑ ${mover.change}</span>
        </div>
    `).join('') : '<p style="color: var(--color-text-lighter); text-align: center; padding: 20px;">No climbers</p>';
    
    const fallersHTML = data.fallers && data.fallers.length > 0 ? data.fallers.map(mover => `
        <div class="mover-item">
            <span class="mover-team">${mover.team_name}</span>
            <span class="mover-change down">↓ ${mover.change}</span>
        </div>
    `).join('') : '<p style="color: var(--color-text-lighter); text-align: center; padding: 20px;">No fallers</p>';
    
    container.innerHTML = `
        <div class="movers-column">
            <div class="movers-column-title">📈 Biggest Climbers</div>
            <div class="movers-list">${climbersHTML}</div>
        </div>
        <div class="movers-column">
            <div class="movers-column-title">📉 Biggest Fallers</div>
            <div class="movers-list">${fallersHTML}</div>
        </div>
    `;
}

// Setup refresh button
function setupRefreshButton() {
    const refreshButton = document.getElementById('refreshButton');
    
    refreshButton.addEventListener('click', function() {
        refreshButton.style.transform = 'rotate(360deg)';
        refreshButton.style.transition = 'transform 0.5s ease';
        
        fetch(`/api/${leagueCode}/refresh`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                } else {
                    alert('Refresh failed: ' + data.message);
                    refreshButton.style.transform = 'rotate(0deg)';
                }
            })
            .catch(error => {
                console.error('Error refreshing data:', error);
                alert('Failed to refresh data. Please try again.');
                refreshButton.style.transform = 'rotate(0deg)';
            });
    });
}

// Initialize all new features
function initializeNewFeatures() {
    initializeWeeklyHeatmap();
    initializeHeadToHead();
    initializeDifferentials();
    initializePodium();
}

// Initialize Weekly Performance Heatmap
function initializeWeeklyHeatmap() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/${leagueCode}/weekly-performance?${queryString}`)
        .then(response => response.json())
        .then(data => {
            renderWeeklyHeatmap(data.teams);
        })
        .catch(error => {
            console.error('Error loading weekly heatmap:', error);
        });
}

// Render Weekly Performance Heatmap
function renderWeeklyHeatmap(teams) {
    const container = document.getElementById('weeklyHeatmap');
    
    if (!teams || teams.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No data available</p>';
        return;
    }
    
    // Get all unique gameweeks
    const allGameweeks = [...new Set(teams.flatMap(team => 
        team.gameweeks.map(gw => gw.gameweek)
    ))].sort((a, b) => a - b);
    
    // Create heatmap HTML
    let html = '<div class="heatmap-grid">';
    
    // Header row
    html += '<div class="heatmap-row heatmap-header">';
    html += '<div class="heatmap-cell heatmap-label">Team</div>';
    allGameweeks.forEach(gw => {
        html += `<div class="heatmap-cell heatmap-gw">GW${gw}</div>`;
    });
    html += '</div>';
    
    // Data rows
    teams.forEach(team => {
        html += '<div class="heatmap-row">';
        html += `<div class="heatmap-cell heatmap-label">${team.team_name}</div>`;
        
        allGameweeks.forEach(gw => {
            const gwData = team.gameweeks.find(g => g.gameweek === gw);
            const points = gwData ? gwData.points : 0;
            
            // Color intensity based on points
            let intensity = '';
            if (points >= 80) intensity = 'very-high';
            else if (points >= 60) intensity = 'high';
            else if (points >= 45) intensity = 'medium';
            else if (points >= 30) intensity = 'low';
            else intensity = 'very-low';
            
            html += `<div class="heatmap-cell heatmap-value ${intensity}" title="${team.team_name} GW${gw}: ${points} pts">${points}</div>`;
        });
        
        html += '</div>';
    });
    
    html += '</div>';
    
    container.innerHTML = html;
}

// Initialize Head-to-Head
function initializeHeadToHead() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/${leagueCode}/head-to-head?${queryString}`)
        .then(response => response.json())
        .then(data => {
            displayHeadToHead(data.teams);
        })
        .catch(error => {
            console.error('Error loading head-to-head:', error);
        });
}

// Display Head-to-Head
function displayHeadToHead(teams) {
    const container = document.getElementById('headToHeadTable');
    
    if (!teams || teams.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">Select at least 2 teams</p>';
        return;
    }
    
    let html = `
        <table class="h2h-table">
            <thead>
                <tr>
                    <th>Team</th>
                    <th>Wins</th>
                    <th>Draws</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    teams.forEach((team, index) => {
        const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '';
        html += `
            <tr>
                <td class="h2h-team">${medal} ${team.team_name}</td>
                <td class="h2h-wins">${team.wins}</td>
                <td class="h2h-draws">${team.draws}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Initialize Differentials
function initializeDifferentials() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/${leagueCode}/differentials?${queryString}`)
        .then(response => response.json())
        .then(data => {
            displayDifferentials(data.teams);
        })
        .catch(error => {
            console.error('Error loading differentials:', error);
        });
}

// Display Differentials - True Unique Players Only, ALL shown
function displayDifferentials(teams) {
    const container = document.getElementById('differentialsGrid');
    
    if (!teams || teams.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No teams selected</p>';
        return;
    }
    
    container.innerHTML = teams.map(team => {
        // Clean up player names (remove any percentages if they exist)
        const cleanPlayers = team.recent_differentials.map(p => p.replace(/\s*\(\d+%\)\s*$/, '').trim());
        
        return `
        <div class="differential-card">
            <div class="differential-team-name">${team.team_name}</div>
            <div class="differential-count">
                <span class="differential-number">${team.differential_count}</span>
                <span class="differential-label">Unique Players</span>
            </div>
            ${cleanPlayers.length > 0 ? `
            <div class="differential-players">
                ${cleanPlayers.map(player => 
                    `<span class="differential-player">${player}</span>`
                ).join('')}
            </div>
            ` : '<div class="differential-note">No unique players among selected teams</div>'}
        </div>
        `;
    }).join('');
}

// Initialize Podium
function initializePodium() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/${leagueCode}/podium?${queryString}`)
        .then(response => response.json())
        .then(data => {
            displayPodium(data.podium);
        })
        .catch(error => {
            console.error('Error loading podium:', error);
        });
}

// Display Podium - Table Format
function displayPodium(podium) {
    const container = document.getElementById('podiumDisplay');
    
    if (!podium || podium.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">Not enough data</p>';
        return;
    }
    
    const medals = ['🥇', '🥈', '🥉'];
    
    let html = `
        <table class="podium-table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Team</th>
                    <th style="text-align: center;">Points</th>
                    <th style="text-align: center;">Form</th>
                    <th style="text-align: center;">Gap</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    podium.forEach((team, index) => {
        html += `
            <tr>
                <td class="podium-rank">${medals[index]}</td>
                <td class="podium-team">${team.team_name}</td>
                <td class="podium-points">${team.total_points}</td>
                <td class="podium-form">${team.recent_form}</td>
                <td class="podium-gap">${team.gap > 0 ? `-${team.gap}` : '-'}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Show error message
function showError(message) {
    const container = document.querySelector('.app-container');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.innerHTML = `<h3>Error</h3><p>${message}</p>`;
    container.insertBefore(errorDiv, container.firstChild);
}

// Utility: Get color for team
function getTeamColor(index) {
    return VantixDashboard.colors[index % VantixDashboard.colors.length];
}
