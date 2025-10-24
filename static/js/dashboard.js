/**
 * Vantix Dashboard - Main JavaScript
 * Coordinates initialization and data loading
 */

// Global state
window.VantixDashboard = {
    teams: [],
    selectedTeamsPoints: new Set(),
    selectedTeamsPosition: new Set(),
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
        position: null
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
            VantixDashboard.selectedTeamsPoints.add(team.entry_id);
            VantixDashboard.selectedTeamsPosition.add(team.entry_id);
        });
        
        // Initialize components
        initializeStats();
        initializeCharts();
        initializeTransfers();
        setupRefreshButton();
        
        console.log('Vantix Dashboard initialized successfully!');
    } else {
        console.error('No team data available');
        showError('Failed to load team data');
    }
});

// Load and display stats
function initializeStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Current Leader
            document.getElementById('stat-leader-value').textContent = data.current_leader.points;
            document.getElementById('stat-leader-detail').textContent = data.current_leader.team;
            
            // Most Goals
            document.getElementById('stat-goals-value').textContent = data.most_goals.goals;
            document.getElementById('stat-goals-detail').textContent = data.most_goals.team;
            
            // Most Clean Sheets
            document.getElementById('stat-cs-value').textContent = data.most_clean_sheets.clean_sheets;
            document.getElementById('stat-cs-detail').textContent = data.most_clean_sheets.team;
            
            // Highest GW Score
            document.getElementById('stat-highest-value').textContent = data.highest_gameweek.points;
            document.getElementById('stat-highest-detail').textContent = 
                `${data.highest_gameweek.team} (GW${data.highest_gameweek.gameweek})`;
        })
        .catch(error => {
            console.error('Error loading stats:', error);
        });
}

// Initialize charts
function initializeCharts() {
    // Initialize cumulative points chart
    initializeCumulativePointsChart();
    
    // Initialize league position chart
    initializeLeaguePositionChart();
}

// Load and display transfers
function initializeTransfers() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeamsPoints);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/recent-transfers?${queryString}`)
        .then(response => response.json())
        .then(data => {
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
                    // Reload the page after successful refresh
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

// Update transfers when team selection changes
function updateTransfers() {
    initializeTransfers();
}

// Utility: Get color for team
function getTeamColor(index) {
    return VantixDashboard.colors[index % VantixDashboard.colors.length];
}
