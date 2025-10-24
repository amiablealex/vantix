/**
 * Vantix Dashboard - Filters
 * Team selection and filtering logic with fixed event handling
 */

// Setup event listeners after DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Wait for charts to initialize
    setTimeout(() => {
        setupFilterEventListeners();
    }, 500);
});

// Setup all filter event listeners using event delegation
function setupFilterEventListeners() {
    // Use event delegation for dynamically created elements
    document.addEventListener('click', function(e) {
        // Handle team pill clicks
        if (e.target.closest('.team-pill')) {
            const pill = e.target.closest('.team-pill');
            const chartType = pill.dataset.chartType;
            handleTeamPillClick(pill, chartType);
            return;
        }
        
        // Handle select/deselect buttons
        if (e.target.closest('.btn-text')) {
            const button = e.target.closest('.btn-text');
            const action = button.dataset.action;
            const chartType = button.dataset.chart;
            
            if (action === 'selectAll') {
                selectAllTeams(chartType);
            } else if (action === 'deselectAll') {
                deselectAllTeams(chartType);
            }
            return;
        }
    });
}

// Handle team pill click
function handleTeamPillClick(pill, chartType) {
    const teamId = parseInt(pill.dataset.teamId);
    
    let selectedSet;
    let updateFunction;
    
    switch(chartType) {
        case 'points':
            selectedSet = VantixDashboard.selectedTeamsPoints;
            updateFunction = () => {
                initializeCumulativePointsChart();
                updateTransfers();
            };
            break;
        case 'position':
            selectedSet = VantixDashboard.selectedTeamsPosition;
            updateFunction = initializeLeaguePositionChart;
            break;
        case 'form':
            selectedSet = VantixDashboard.selectedTeamsForm;
            updateFunction = initializeFormChart;
            break;
        default:
            return;
    }
    
    // Toggle selection
    if (selectedSet.has(teamId)) {
        selectedSet.delete(teamId);
        pill.classList.remove('selected');
    } else {
        selectedSet.add(teamId);
        pill.classList.add('selected');
    }
    
    // Update chart
    updateFunction();
}

// Select all teams
function selectAllTeams(chartType) {
    let selectedSet;
    let containerId;
    let updateFunction;
    
    switch(chartType) {
        case 'points':
            selectedSet = VantixDashboard.selectedTeamsPoints;
            containerId = 'teamPillsPoints';
            updateFunction = () => {
                initializeCumulativePointsChart();
                updateTransfers();
            };
            break;
        case 'position':
            selectedSet = VantixDashboard.selectedTeamsPosition;
            containerId = 'teamPillsPosition';
            updateFunction = initializeLeaguePositionChart;
            break;
        case 'form':
            selectedSet = VantixDashboard.selectedTeamsForm;
            containerId = 'teamPillsForm';
            updateFunction = initializeFormChart;
            break;
        default:
            return;
    }
    
    // Add all teams to selection
    VantixDashboard.teams.forEach(team => {
        selectedSet.add(team.entry_id);
    });
    
    // Update pills
    const pills = document.querySelectorAll(`#${containerId} .team-pill`);
    pills.forEach(pill => pill.classList.add('selected'));
    
    // Update chart
    updateFunction();
}

// Deselect all teams
function deselectAllTeams(chartType) {
    let selectedSet;
    let containerId;
    let updateFunction;
    
    switch(chartType) {
        case 'points':
            selectedSet = VantixDashboard.selectedTeamsPoints;
            containerId = 'teamPillsPoints';
            updateFunction = () => {
                initializeCumulativePointsChart();
                updateTransfers();
            };
            break;
        case 'position':
            selectedSet = VantixDashboard.selectedTeamsPosition;
            containerId = 'teamPillsPosition';
            updateFunction = initializeLeaguePositionChart;
            break;
        case 'form':
            selectedSet = VantixDashboard.selectedTeamsForm;
            containerId = 'teamPillsForm';
            updateFunction = initializeFormChart;
            break;
        default:
            return;
    }
    
    // Clear selection
    selectedSet.clear();
    
    // Update pills
    const pills = document.querySelectorAll(`#${containerId} .team-pill`);
    pills.forEach(pill => pill.classList.remove('selected'));
    
    // Update chart
    updateFunction();
}
