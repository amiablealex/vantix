/**
 * Vantix Dashboard - Filters
 * Team selection and filtering logic
 */

// Setup event listeners after DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for charts to initialize
    setTimeout(() => {
        setupTeamPillListeners();
        setupSelectAllButtons();
    }, 500);
});

// Setup team pill click listeners
function setupTeamPillListeners() {
    // Cumulative points pills
    const pointsPills = document.querySelectorAll('#teamPillsPoints .team-pill');
    pointsPills.forEach(pill => {
        pill.addEventListener('click', function() {
            handleTeamPillClick(this, 'points');
        });
    });
    
    // League position pills
    const positionPills = document.querySelectorAll('#teamPillsPosition .team-pill');
    positionPills.forEach(pill => {
        pill.addEventListener('click', function() {
            handleTeamPillClick(this, 'position');
        });
    });
}

// Handle team pill click
function handleTeamPillClick(pill, chartType) {
    const teamId = parseInt(pill.dataset.teamId);
    const selectedSet = chartType === 'points' ? 
        VantixDashboard.selectedTeamsPoints : 
        VantixDashboard.selectedTeamsPosition;
    
    // Toggle selection
    if (selectedSet.has(teamId)) {
        selectedSet.delete(teamId);
        pill.classList.remove('selected');
    } else {
        selectedSet.add(teamId);
        pill.classList.add('selected');
    }
    
    // Update chart
    if (chartType === 'points') {
        initializeCumulativePointsChart();
        updateTransfers(); // Update transfers when points chart selection changes
    } else {
        initializeLeaguePositionChart();
    }
}

// Setup select/deselect all buttons
function setupSelectAllButtons() {
    // Points chart buttons
    document.getElementById('selectAllTeams').addEventListener('click', function() {
        selectAllTeams('points');
    });
    
    document.getElementById('deselectAllTeams').addEventListener('click', function() {
        deselectAllTeams('points');
    });
    
    // Position chart buttons
    document.getElementById('selectAllTeamsPosition').addEventListener('click', function() {
        selectAllTeams('position');
    });
    
    document.getElementById('deselectAllTeamsPosition').addEventListener('click', function() {
        deselectAllTeams('position');
    });
}

// Select all teams
function selectAllTeams(chartType) {
    const selectedSet = chartType === 'points' ? 
        VantixDashboard.selectedTeamsPoints : 
        VantixDashboard.selectedTeamsPosition;
    
    // Add all teams to selection
    VantixDashboard.teams.forEach(team => {
        selectedSet.add(team.entry_id);
    });
    
    // Update pills
    const containerId = chartType === 'points' ? 'teamPillsPoints' : 'teamPillsPosition';
    const pills = document.querySelectorAll(`#${containerId} .team-pill`);
    pills.forEach(pill => pill.classList.add('selected'));
    
    // Update chart
    if (chartType === 'points') {
        initializeCumulativePointsChart();
        updateTransfers();
    } else {
        initializeLeaguePositionChart();
    }
}

// Deselect all teams
function deselectAllTeams(chartType) {
    const selectedSet = chartType === 'points' ? 
        VantixDashboard.selectedTeamsPoints : 
        VantixDashboard.selectedTeamsPosition;
    
    // Clear selection
    selectedSet.clear();
    
    // Update pills
    const containerId = chartType === 'points' ? 'teamPillsPoints' : 'teamPillsPosition';
    const pills = document.querySelectorAll(`#${containerId} .team-pill`);
    pills.forEach(pill => pill.classList.remove('selected'));
    
    // Update chart
    if (chartType === 'points') {
        initializeCumulativePointsChart();
        updateTransfers();
    } else {
        initializeLeaguePositionChart();
    }
}
