/**
 * Vantix Dashboard - Main JavaScript
 * Master filter coordination and data loading
 */

// Global state
window.VantixDashboard = {
    teams: [],
    selectedTeams: new Set(), // Single master selection
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
            
            // Update everything
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
    initializeAllCharts();
    initializeTransfers();
    initializeAnalytics();
}

// Load and display stats
function initializeStats() {
    fetch('/api/stats')
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
    
    fetch(`/api/recent-transfers?${queryString}`)
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
        if (transfer.count === 0) {
            return `
                <div class="transfer-item">
                    <div class="transfer-team">${transfer.team_name}</div>
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
                    <div class="transfer-team">${transfer.team_name}</div>
                    <div class="transfer-details">${transferDetails}</div>
                </div>
            `;
        }
    }).join('');
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
    
    fetch(`/api/team-comparison?${queryString}`)
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

// Display team comparison
function displayComparison(teams) {
    const container = document.getElementById('comparisonGrid');
    
    if (!teams || teams.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No teams selected</p>';
        return;
    }
    
    container.innerHTML = teams.map(team => `
        <div class="comparison-card">
            <div class="comparison-team-name">${team.team_name}</div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Total Points</span>
                <span class="comparison-stat-value">${team.total_points}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Avg Per GW</span>
                <span class="comparison-stat-value">${team.avg_points}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Highest GW</span>
                <span class="comparison-stat-value">${team.highest_gw}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Lowest GW</span>
                <span class="comparison-stat-value">${team.lowest_gw}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Total Transfers</span>
                <span class="comparison-stat-value">${team.total_transfers}</span>
            </div>
            <div class="comparison-stat-row">
                <span class="comparison-stat-label">Chips Used</span>
                <span class="comparison-stat-value">${team.chips_used}</span>
            </div>
        </div>
    `).join('');
}

// Initialize biggest movers
function initializeBiggestMovers() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    console.log('Initializing biggest movers with teams:', selectedTeams);
    
    fetch(`/api/biggest-movers?${queryString}`)
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
        
        fetch('/api/refresh', { method: 'POST' })
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
