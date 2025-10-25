/**
 * Vantix Dashboard - Main JavaScript
 * Master filter coordination and data loading - NOW FILTERS STATS TOO
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
        distribution: null,
        sources: null
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
    
    fetch(`/api/stats?${queryString}`)
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
                <span class="comparison-stat-label">Hits Taken</span>
                <span class="comparison-stat-value">${team.hits_taken}</span>
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

// Initialize all new features
function initializeNewFeatures() {
    initializeWeeklyHeatmap();
    initializeCaptainHeatmap();
    initializeHeadToHead();
    initializePointsSources();
    initializeDifferentials();
    initializePodium();
}

// Initialize Weekly Performance Heatmap
function initializeWeeklyHeatmap() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/weekly-performance?${queryString}`)
        .then(response => response.json())
        .then(data => {
            renderHeatmap(data.teams, 'weeklyHeatmap', 'Total Points');
        })
        .catch(error => {
            console.error('Error loading weekly heatmap:', error);
        });
}

// Initialize Captain Heatmap
function initializeCaptainHeatmap() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/captain-performance?${queryString}`)
        .then(response => response.json())
        .then(data => {
            renderCaptainHeatmap(data.teams);
        })
        .catch(error => {
            console.error('Error loading captain heatmap:', error);
        });
}

// Render generic heatmap (for weekly performance)
function renderHeatmap(teams, containerId, label) {
    const container = document.getElementById(containerId);
    
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

// Render Captain Heatmap (with captain names)
function renderCaptainHeatmap(teams) {
    const container = document.getElementById('captainHeatmap');
    
    if (!teams || teams.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No captain data available - will populate after next data refresh</p>';
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
            const captainName = gwData ? gwData.captain_name : 'Unknown';
            
            // Color intensity based on captain points (different thresholds)
            let intensity = '';
            if (points >= 20) intensity = 'very-high';
            else if (points >= 12) intensity = 'high';
            else if (points >= 8) intensity = 'medium';
            else if (points >= 4) intensity = 'low';
            else intensity = 'very-low';
            
            html += `<div class="heatmap-cell heatmap-value ${intensity}" title="${team.team_name} GW${gw}: ${captainName} - ${points} pts">${points}</div>`;
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
    
    fetch(`/api/head-to-head?${queryString}`)
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

// Initialize Points Sources
function initializePointsSources() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/points-sources?${queryString}`)
        .then(response => response.json())
        .then(data => {
            renderPointsSources(data.teams);
        })
        .catch(error => {
            console.error('Error loading points sources:', error);
        });
}

// Render Points Sources Chart
function renderPointsSources(teams) {
    const ctx = document.getElementById('pointsSourcesChart');
    
    if (!ctx) {
        console.error('Points sources chart canvas missing');
        return;
    }
    
    if (VantixDashboard.charts.sources) {
        VantixDashboard.charts.sources.destroy();
    }
    
    if (!teams || teams.length === 0) {
        ctx.parentElement.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No data available</p><canvas id="pointsSourcesChart"></canvas>';
        return;
    }
    
    const labels = teams.map(t => t.team_name);
    
    VantixDashboard.charts.sources = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Goalkeepers',
                    data: teams.map(t => t.goalkeeper),
                    backgroundColor: '#A8DADC',
                    borderColor: '#8AC4C6',
                    borderWidth: 1
                },
                {
                    label: 'Defenders',
                    data: teams.map(t => t.defenders),
                    backgroundColor: '#B8D4B8',
                    borderColor: '#9FBE9F',
                    borderWidth: 1
                },
                {
                    label: 'Midfielders',
                    data: teams.map(t => t.midfielders),
                    backgroundColor: '#F1C6B7',
                    borderColor: '#E0B0A0',
                    borderWidth: 1
                },
                {
                    label: 'Forwards',
                    data: teams.map(t => t.forwards),
                    backgroundColor: '#D4B5D4',
                    borderColor: '#C0A0C0',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { display: false }
                },
                y: {
                    stacked: true,
                    title: { display: true, text: 'Points' },
                    grid: { color: '#F5F2EB' }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    titleColor: '#3A3A3A',
                    bodyColor: '#3A3A3A',
                    borderColor: '#E8DCC4',
                    borderWidth: 1,
                    padding: 12
                }
            }
        }
    });
}

// Initialize Differentials
function initializeDifferentials() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/differentials?${queryString}`)
        .then(response => response.json())
        .then(data => {
            displayDifferentials(data.teams);
        })
        .catch(error => {
            console.error('Error loading differentials:', error);
        });
}

// Display Differentials
function displayDifferentials(teams) {
    const container = document.getElementById('differentialsGrid');
    
    if (!teams || teams.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">No teams selected</p>';
        return;
    }
    
    container.innerHTML = teams.map(team => `
        <div class="differential-card">
            <div class="differential-team-name">${team.team_name}</div>
            <div class="differential-count">
                <span class="differential-number">${team.differential_count}</span>
                <span class="differential-label">Unique Players</span>
            </div>
            <div class="differential-players">
                ${team.recent_differentials.slice(0, 3).map(player => 
                    `<span class="differential-player">${player}</span>`
                ).join('')}
            </div>
        </div>
    `).join('');
}

// Initialize Podium
function initializePodium() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/podium?${queryString}`)
        .then(response => response.json())
        .then(data => {
            displayPodium(data.podium);
        })
        .catch(error => {
            console.error('Error loading podium:', error);
        });
}

// Display Podium
function displayPodium(podium) {
    const container = document.getElementById('podiumDisplay');
    
    if (!podium || podium.length === 0) {
        container.innerHTML = '<p class="text-center" style="color: var(--color-text-lighter);">Not enough data</p>';
        return;
    }
    
    const medals = ['🥇', '🥈', '🥉'];
    const positions = ['first', 'second', 'third'];
    
    container.innerHTML = podium.map((team, index) => `
        <div class="podium-card podium-${positions[index]}">
            <div class="podium-medal">${medals[index]}</div>
            <div class="podium-position">#${team.position}</div>
            <div class="podium-team-name">${team.team_name}</div>
            <div class="podium-manager">${team.manager_name}</div>
            <div class="podium-points">${team.total_points} pts</div>
            <div class="podium-form">Form: ${team.recent_form} avg</div>
            ${team.gap > 0 ? `<div class="podium-gap">-${team.gap} behind</div>` : ''}
        </div>
    `).join('');
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
