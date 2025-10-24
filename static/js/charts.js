/**
 * Vantix Dashboard - Charts
 * CLEAN VERSION - NO renderTeamPills function
 */

// Initialize Cumulative Points Chart
function initializeCumulativePointsChart() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    console.log('Loading cumulative points for teams:', selectedTeams);
    
    fetch(`/api/cumulative-points?${queryString}`)
        .then(response => response.json())
        .then(data => {
            renderCumulativePointsChart(data.teams);
        })
        .catch(error => {
            console.error('Error loading cumulative points:', error);
        });
}

// Render Cumulative Points Chart
function renderCumulativePointsChart(teamsData) {
    const ctx = document.getElementById('cumulativePointsChart');
    
    if (VantixDashboard.charts.points) {
        VantixDashboard.charts.points.destroy();
    }
    
    const datasets = teamsData.map((team) => {
        const teamInfo = VantixDashboard.teams.find(t => t.team_name === team.team_name);
        const teamIndex = VantixDashboard.teams.indexOf(teamInfo);
        const color = getTeamColor(teamIndex);
        
        return {
            label: team.team_name,
            data: team.data,
            borderColor: color,
            backgroundColor: color + '20',
            borderWidth: 3,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: color,
            pointHoverBorderColor: '#FFFFFF',
            pointHoverBorderWidth: 2
        };
    });
    
    VantixDashboard.charts.points = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    titleColor: '#3A3A3A',
                    bodyColor: '#3A3A3A',
                    borderColor: '#E8DCC4',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        title: (context) => 'Gameweek ' + context[0].parsed.x,
                        label: (context) => context.dataset.label + ': ' + context.parsed.y + ' pts'
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Gameweek' },
                    grid: { color: '#F5F2EB' },
                    ticks: { stepSize: 1 }
                },
                y: {
                    title: { display: true, text: 'Cumulative Points' },
                    grid: { color: '#F5F2EB' }
                }
            }
        }
    });
    
    console.log('Cumulative points chart rendered');
}

// Initialize League Position Chart
function initializeLeaguePositionChart() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    console.log('Loading league positions for teams:', selectedTeams);
    
    fetch(`/api/league-positions?${queryString}`)
        .then(response => response.json())
        .then(data => {
            renderLeaguePositionChart(data.teams);
        })
        .catch(error => {
            console.error('Error loading league positions:', error);
        });
}

// Render League Position Chart with DARK VISIBLE chip markers
function renderLeaguePositionChart(teamsData) {
    const ctx = document.getElementById('leaguePositionChart');
    
    if (VantixDashboard.charts.position) {
        VantixDashboard.charts.position.destroy();
    }
    
    if (!teamsData || teamsData.length === 0) {
        console.warn('No position data to display');
        return;
    }
    
    const datasets = teamsData.map((team) => {
        const teamInfo = VantixDashboard.teams.find(t => t.team_name === team.team_name);
        const teamIndex = VantixDashboard.teams.indexOf(teamInfo);
        const color = getTeamColor(teamIndex);
        
        const pointStyles = team.data.map(point => {
            return team.chips.find(c => c.gameweek === point.x) ? 'star' : 'circle';
        });
        
        const pointRadii = team.data.map(point => {
            return team.chips.find(c => c.gameweek === point.x) ? 12 : 0;
        });
        
        // SOLID BLACK for chip markers
        const chipColor = '#000000';
        
        return {
            label: team.team_name,
            data: team.data,
            borderColor: color,
            backgroundColor: chipColor,
            borderWidth: 3,
            tension: 0.3,
            pointStyle: pointStyles,
            pointRadius: pointRadii,
            pointHoverRadius: 14,
            pointBackgroundColor: chipColor,
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 4
        };
    });
    
    VantixDashboard.charts.position = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    titleColor: '#3A3A3A',
                    bodyColor: '#3A3A3A',
                    borderColor: '#E8DCC4',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        title: (context) => 'Gameweek ' + context[0].parsed.x,
                        label: (context) => {
                            const team = teamsData[context.datasetIndex];
                            const chipAtGW = team.chips.find(c => c.gameweek === context.parsed.x);
                            let label = context.dataset.label + ': Position ' + context.parsed.y;
                            if (chipAtGW) label += ' ★ ' + chipAtGW.chip;
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Gameweek' },
                    grid: { color: '#F5F2EB' },
                    ticks: { stepSize: 1 }
                },
                y: {
                    reverse: true,
                    title: { display: true, text: 'League Position' },
                    grid: { color: '#F5F2EB' },
                    ticks: { stepSize: 1 }
                }
            }
        }
    });
    
    console.log('League position chart rendered');
}

// Initialize Form Chart
function initializeFormChart() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    console.log('Loading form chart for teams:', selectedTeams);
    
    fetch(`/api/form-chart?${queryString}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Form data received:', data);
            if (!data.teams || data.teams.length === 0) {
                const container = document.getElementById('formChart').parentElement;
                container.innerHTML = '<p style="text-align: center; color: #9B9B9B; padding: 40px;">No form data available yet.</p><canvas id="formChart"></canvas>';
                return;
            }
            renderFormChart(data.teams);
        })
        .catch(error => {
            console.error('Form chart error:', error);
            const container = document.getElementById('formChart').parentElement;
            container.innerHTML = '<p style="text-align: center; color: #9B9B9B; padding: 40px;">Unable to load form data.</p><canvas id="formChart"></canvas>';
        });
}

// Render Form Chart
function renderFormChart(teamsData) {
    const ctx = document.getElementById('formChart');
    
    if (!ctx) {
        console.error('Form chart canvas missing');
        return;
    }
    
    if (VantixDashboard.charts.form) {
        VantixDashboard.charts.form.destroy();
    }
    
    const datasets = teamsData.map((team) => {
        const teamInfo = VantixDashboard.teams.find(t => t.team_name === team.team_name);
        const teamIndex = VantixDashboard.teams.indexOf(teamInfo);
        const color = getTeamColor(teamIndex);
        
        return {
            label: team.team_name,
            data: team.data,
            borderColor: color,
            backgroundColor: color + '40',
            borderWidth: 2,
            tension: 0.4,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: color,
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            fill: true
        };
    });
    
    VantixDashboard.charts.form = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    titleColor: '#3A3A3A',
                    bodyColor: '#3A3A3A',
                    borderColor: '#E8DCC4',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        title: (context) => 'Gameweek ' + context[0].parsed.x,
                        label: (context) => context.dataset.label + ': ' + context.parsed.y + ' pts'
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Gameweek' },
                    grid: { color: '#F5F2EB' },
                    ticks: { stepSize: 1 }
                },
                y: {
                    title: { display: true, text: 'Points' },
                    grid: { color: '#F5F2EB' }
                }
            }
        }
    });
    
    console.log('Form chart rendered successfully');
}

// Initialize Points Distribution Chart
function initializeDistributionChart() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeams);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    console.log('Loading distribution for teams:', selectedTeams);
    
    fetch(`/api/points-distribution?${queryString}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Distribution data received:', data);
            if (!data.labels || data.labels.length === 0) {
                const container = document.getElementById('distributionChart').parentElement;
                container.innerHTML = '<p style="text-align: center; color: #9B9B9B; padding: 40px;">No distribution data available.</p><canvas id="distributionChart"></canvas>';
                return;
            }
            renderDistributionChart(data);
        })
        .catch(error => {
            console.error('Distribution error:', error);
            const container = document.getElementById('distributionChart').parentElement;
            container.innerHTML = '<p style="text-align: center; color: #9B9B9B; padding: 40px;">Unable to load distribution.</p><canvas id="distributionChart"></canvas>';
        });
}

// Render Points Distribution Chart
function renderDistributionChart(data) {
    const ctx = document.getElementById('distributionChart');
    
    if (!ctx) {
        console.error('Distribution chart canvas missing');
        return;
    }
    
    if (VantixDashboard.charts.distribution) {
        VantixDashboard.charts.distribution.destroy();
    }
    
    VantixDashboard.charts.distribution = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Gameweek Count',
                data: data.counts,
                backgroundColor: '#A8DADC',
                borderColor: '#8AC4C6',
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    titleColor: '#3A3A3A',
                    bodyColor: '#3A3A3A',
                    borderColor: '#E8DCC4',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: (context) => context.parsed.y + ' gameweeks'
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Points Range' },
                    grid: { display: false }
                },
                y: {
                    title: { display: true, text: 'Number of Gameweeks' },
                    grid: { color: '#F5F2EB' },
                    ticks: { stepSize: 1 }
                }
            }
        }
    });
    
    console.log('Distribution chart rendered successfully');
}
