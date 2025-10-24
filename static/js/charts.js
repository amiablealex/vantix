/**
 * Vantix Dashboard - Charts
 * Chart.js implementations for data visualization
 */

// Initialize Cumulative Points Chart
function initializeCumulativePointsChart() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeamsPoints);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/cumulative-points?${queryString}`)
        .then(response => response.json())
        .then(data => {
            renderCumulativePointsChart(data.teams);
            renderTeamPills('teamPillsPoints', 'points');
        })
        .catch(error => {
            console.error('Error loading cumulative points:', error);
        });
}

// Render Cumulative Points Chart
function renderCumulativePointsChart(teamsData) {
    const ctx = document.getElementById('cumulativePointsChart');
    
    // Destroy existing chart if it exists
    if (VantixDashboard.charts.points) {
        VantixDashboard.charts.points.destroy();
    }
    
    // Prepare datasets
    const datasets = teamsData.map((team, index) => {
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
    
    // Create chart
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
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    titleColor: '#3A3A3A',
                    bodyColor: '#3A3A3A',
                    borderColor: '#E8DCC4',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    boxWidth: 12,
                    boxHeight: 12,
                    boxPadding: 4,
                    titleFont: {
                        family: "'Inter', sans-serif",
                        size: 13,
                        weight: '600'
                    },
                    bodyFont: {
                        family: "'Inter', sans-serif",
                        size: 12
                    },
                    callbacks: {
                        title: function(context) {
                            return 'Gameweek ' + context[0].parsed.x;
                        },
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y + ' pts';
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Gameweek',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 12,
                            weight: '600'
                        },
                        color: '#6B6B6B'
                    },
                    grid: {
                        color: '#F5F2EB',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6B6B6B',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 11
                        },
                        stepSize: 1
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Cumulative Points',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 12,
                            weight: '600'
                        },
                        color: '#6B6B6B'
                    },
                    grid: {
                        color: '#F5F2EB',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6B6B6B',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 11
                        }
                    }
                }
            }
        }
    });
}

// Initialize League Position Chart
function initializeLeaguePositionChart() {
    const selectedTeams = Array.from(VantixDashboard.selectedTeamsPosition);
    const queryString = selectedTeams.map(id => `teams=${id}`).join('&');
    
    fetch(`/api/league-positions?${queryString}`)
        .then(response => response.json())
        .then(data => {
            renderLeaguePositionChart(data.teams);
            renderTeamPills('teamPillsPosition', 'position');
        })
        .catch(error => {
            console.error('Error loading league positions:', error);
        });
}

// Render League Position Chart
function renderLeaguePositionChart(teamsData) {
    const ctx = document.getElementById('leaguePositionChart');
    
    // Destroy existing chart if it exists
    if (VantixDashboard.charts.position) {
        VantixDashboard.charts.position.destroy();
    }
    
    // Prepare datasets
    const datasets = teamsData.map((team, index) => {
        const teamInfo = VantixDashboard.teams.find(t => t.team_name === team.team_name);
        const teamIndex = VantixDashboard.teams.indexOf(teamInfo);
        const color = getTeamColor(teamIndex);
        
        // Add chip markers as point styles
        const pointStyles = team.data.map(point => {
            const chipAtGW = team.chips.find(c => c.gameweek === point.x);
            return chipAtGW ? 'star' : 'circle';
        });
        
        const pointRadii = team.data.map(point => {
            const chipAtGW = team.chips.find(c => c.gameweek === point.x);
            return chipAtGW ? 8 : 0;
        });
        
        return {
            label: team.team_name,
            data: team.data,
            borderColor: color,
            backgroundColor: color,
            borderWidth: 3,
            tension: 0.3,
            pointStyle: pointStyles,
            pointRadius: pointRadii,
            pointHoverRadius: 8,
            pointBackgroundColor: color,
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2
        };
    });
    
    // Create chart
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
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    titleColor: '#3A3A3A',
                    bodyColor: '#3A3A3A',
                    borderColor: '#E8DCC4',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    boxWidth: 12,
                    boxHeight: 12,
                    boxPadding: 4,
                    titleFont: {
                        family: "'Inter', sans-serif",
                        size: 13,
                        weight: '600'
                    },
                    bodyFont: {
                        family: "'Inter', sans-serif",
                        size: 12
                    },
                    callbacks: {
                        title: function(context) {
                            return 'Gameweek ' + context[0].parsed.x;
                        },
                        label: function(context) {
                            const team = teamsData[context.datasetIndex];
                            const chipAtGW = team.chips.find(c => c.gameweek === context.parsed.x);
                            let label = context.dataset.label + ': Position ' + context.parsed.y;
                            
                            if (chipAtGW) {
                                label += ' ★ ' + chipAtGW.chip;
                            }
                            
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Gameweek',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 12,
                            weight: '600'
                        },
                        color: '#6B6B6B'
                    },
                    grid: {
                        color: '#F5F2EB',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6B6B6B',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 11
                        },
                        stepSize: 1
                    }
                },
                y: {
                    reverse: true, // Lower position number is better
                    title: {
                        display: true,
                        text: 'League Position',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 12,
                            weight: '600'
                        },
                        color: '#6B6B6B'
                    },
                    grid: {
                        color: '#F5F2EB',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6B6B6B',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 11
                        },
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Render team selection pills
function renderTeamPills(containerId, chartType) {
    const container = document.getElementById(containerId);
    const selectedSet = chartType === 'points' ? 
        VantixDashboard.selectedTeamsPoints : 
        VantixDashboard.selectedTeamsPosition;
    
    container.innerHTML = VantixDashboard.teams.map((team, index) => {
        const color = getTeamColor(index);
        const isSelected = selectedSet.has(team.entry_id);
        
        return `
            <div class="team-pill ${isSelected ? 'selected' : ''}" 
                 data-team-id="${team.entry_id}"
                 data-chart-type="${chartType}">
                <span class="team-pill-color" style="background-color: ${color}"></span>
                <span class="team-pill-name">${team.team_name}</span>
            </div>
        `;
    }).join('');
}
