// Configuration
const API_URL = 'http://localhost:8000';
const CORRECT_PIN = '1991';

// État de l'application
let state = {
    isAuthenticated: false,
    currentDate: new Date().toISOString().split('T')[0],
    predictions: [],
    combos: [],
    matches: [],
    activeTab: 'predictions'
};

// Éléments DOM
const loginScreen = document.getElementById('login-screen');
const mainScreen = document.getElementById('main-screen');
const pinDots = document.querySelectorAll('.pin-dot');
const pinError = document.getElementById('pin-error');
const datePicker = document.getElementById('date-picker');
const modal = document.getElementById('match-modal');
const modalBody = document.getElementById('modal-body');

let currentPin = '';

// ==================== Authentification ====================

function initPinKeypad() {
    const keys = document.querySelectorAll('.pin-key');

    keys.forEach(key => {
        key.addEventListener('click', () => {
            const keyValue = key.dataset.key;
            handlePinInput(keyValue);
        });
    });

    // Support clavier
    document.addEventListener('keydown', (e) => {
        if (!state.isAuthenticated) {
            if (e.key >= '0' && e.key <= '9') {
                handlePinInput(e.key);
            } else if (e.key === 'Backspace') {
                handlePinInput('clear');
            } else if (e.key === 'Enter') {
                handlePinInput('enter');
            }
        }
    });
}

function handlePinInput(key) {
    if (key === 'clear') {
        currentPin = '';
        updatePinDisplay();
        pinError.textContent = '';
    } else if (key === 'enter') {
        verifyPin();
    } else if (currentPin.length < 4) {
        currentPin += key;
        updatePinDisplay();

        if (currentPin.length === 4) {
            setTimeout(verifyPin, 200);
        }
    }
}

function updatePinDisplay() {
    pinDots.forEach((dot, index) => {
        dot.classList.toggle('filled', index < currentPin.length);
    });
}

async function verifyPin() {
    if (currentPin === CORRECT_PIN) {
        state.isAuthenticated = true;
        loginScreen.classList.remove('active');
        mainScreen.classList.add('active');
        initApp();
    } else {
        pinError.textContent = 'PIN incorrect. Réessayez.';
        currentPin = '';
        updatePinDisplay();

        // Effet de tremblement
        const container = document.querySelector('.pin-container');
        container.style.animation = 'shake 0.5s';
        setTimeout(() => container.style.animation = '', 500);
    }
}

// ==================== Initialisation ====================

function initApp() {
    // Définir la date du jour
    datePicker.value = state.currentDate;

    // Event listeners
    datePicker.addEventListener('change', (e) => {
        state.currentDate = e.target.value;
        loadData();
    });

    document.getElementById('logout-btn').addEventListener('click', logout);

    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Modal
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Filtres
    document.getElementById('confidence-filter').addEventListener('change', renderPredictions);
    document.getElementById('league-filter').addEventListener('change', renderPredictions);

    // Charger les données
    loadData();
}

function logout() {
    state.isAuthenticated = false;
    currentPin = '';
    updatePinDisplay();
    mainScreen.classList.remove('active');
    loginScreen.classList.add('active');
}

// ==================== Chargement des données ====================

async function loadData() {
    await Promise.all([
        loadPredictions(),
        loadCombos(),
        loadMatches()
    ]);
}

async function loadPredictions() {
    const container = document.getElementById('predictions-list');
    container.innerHTML = '<div class="loading">Chargement des prédictions...</div>';

    try {
        const response = await fetch(`${API_URL}/api/predictions/${state.currentDate}`);

        if (!response.ok) {
            throw new Error('Erreur serveur');
        }

        state.predictions = await response.json();
        updateLeagueFilter();
        renderPredictions();
    } catch (error) {
        console.error('Erreur:', error);
        // Données de démonstration si l'API n'est pas disponible
        state.predictions = generateDemoData();
        updateLeagueFilter();
        renderPredictions();
    }
}

async function loadCombos() {
    const container = document.getElementById('combos-list');
    container.innerHTML = '<div class="loading">Chargement des combinés...</div>';

    try {
        const response = await fetch(`${API_URL}/api/best-combos/${state.currentDate}`);

        if (!response.ok) {
            throw new Error('Erreur serveur');
        }

        state.combos = await response.json();
        renderCombos();
    } catch (error) {
        console.error('Erreur:', error);
        state.combos = generateDemoCombos();
        renderCombos();
    }
}

async function loadMatches() {
    const container = document.getElementById('matches-list');
    container.innerHTML = '<div class="loading">Chargement des matchs...</div>';

    try {
        const response = await fetch(`${API_URL}/api/matches/${state.currentDate}`);

        if (!response.ok) {
            throw new Error('Erreur serveur');
        }

        state.matches = await response.json();
        renderMatches();
    } catch (error) {
        console.error('Erreur:', error);
        state.matches = state.predictions.map(p => p.match);
        renderMatches();
    }
}

// ==================== Rendu ====================

function renderPredictions() {
    const container = document.getElementById('predictions-list');
    const confidenceFilter = document.getElementById('confidence-filter').value;
    const leagueFilter = document.getElementById('league-filter').value;

    let filtered = state.predictions;

    if (confidenceFilter !== 'all') {
        filtered = filtered.filter(p => p.confidence === confidenceFilter);
    }

    if (leagueFilter !== 'all') {
        filtered = filtered.filter(p => p.match.league_name === leagueFilter);
    }

    if (filtered.length === 0) {
        container.innerHTML = '<div class="loading">Aucune prédiction disponible pour cette date.</div>';
        return;
    }

    container.innerHTML = filtered.map(prediction => `
        <div class="prediction-card" onclick="showMatchDetail(${prediction.match_id}, '${state.currentDate}')">
            <div class="match-header">
                <span class="league-badge">${prediction.match.league_name}</span>
                <span class="match-time">${formatTime(prediction.match.date)}</span>
            </div>

            <div class="teams">
                <div class="team">
                    <img src="${prediction.match.home_team.logo || 'https://via.placeholder.com/48'}"
                         alt="${prediction.match.home_team.name}"
                         class="team-logo"
                         onerror="this.src='https://via.placeholder.com/48'">
                    <div class="team-name">${prediction.match.home_team.name}</div>
                </div>
                <div class="vs">VS</div>
                <div class="team">
                    <img src="${prediction.match.away_team.logo || 'https://via.placeholder.com/48'}"
                         alt="${prediction.match.away_team.name}"
                         class="team-logo"
                         onerror="this.src='https://via.placeholder.com/48'">
                    <div class="team-name">${prediction.match.away_team.name}</div>
                </div>
            </div>

            <div class="prediction-result">
                <div class="prediction-row">
                    <span class="prediction-label">Prédiction</span>
                    <span class="prediction-value">${prediction.recommended_bet}</span>
                </div>
                <div class="probabilities">
                    <div class="prob-item">
                        <span class="prob-label">1</span>
                        <span class="prob-value">${prediction.home_win_probability}%</span>
                    </div>
                    <div class="prob-item">
                        <span class="prob-label">X</span>
                        <span class="prob-value">${prediction.draw_probability}%</span>
                    </div>
                    <div class="prob-item">
                        <span class="prob-label">2</span>
                        <span class="prob-value">${prediction.away_win_probability}%</span>
                    </div>
                </div>
            </div>

            <span class="confidence-badge confidence-${prediction.confidence}">
                Confiance: ${getConfidenceLabel(prediction.confidence)}
            </span>
        </div>
    `).join('');
}

function renderCombos() {
    const container = document.getElementById('combos-list');

    if (state.combos.length === 0) {
        container.innerHTML = '<div class="loading">Aucun combiné disponible pour cette date.</div>';
        return;
    }

    container.innerHTML = state.combos.map(combo => `
        <div class="combo-card">
            <div class="combo-header ${combo.risk_level}">
                <div class="combo-info">
                    <div class="combo-title">${combo.description}</div>
                </div>
                <div class="combo-stats">
                    <div class="combo-prob">${combo.total_probability.toFixed(1)}%</div>
                    <div class="combo-expected">Valeur: ${combo.expected_value.toFixed(0)}</div>
                </div>
            </div>
            <div class="combo-matches">
                ${combo.matches.map(match => `
                    <div class="combo-match">
                        <span class="combo-match-teams">${match.teams}</span>
                        <span class="combo-match-bet">${match.prediction}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function renderMatches() {
    const container = document.getElementById('matches-list');

    if (state.matches.length === 0) {
        container.innerHTML = '<div class="loading">Aucun match prévu pour cette date.</div>';
        return;
    }

    container.innerHTML = state.matches.map(match => `
        <div class="match-item" onclick="showMatchDetail(${match.id}, '${state.currentDate}')">
            <div class="match-info">
                <span class="match-league">${match.league_name}</span>
                <span class="match-teams-inline">
                    ${match.home_team.name} vs ${match.away_team.name}
                </span>
            </div>
            <span class="match-datetime">${formatDateTime(match.date)}</span>
        </div>
    `).join('');
}

// ==================== Navigation ====================

function switchTab(tabName) {
    state.activeTab = tabName;

    // Mettre à jour les boutons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Mettre à jour le contenu
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
}

// ==================== Modal ====================

async function showMatchDetail(matchId, date) {
    modal.classList.add('active');
    modalBody.innerHTML = '<div class="loading">Chargement...</div>';

    try {
        const response = await fetch(`${API_URL}/api/match/${matchId}/analysis?date_str=${date}`);

        if (!response.ok) {
            throw new Error('Erreur');
        }

        const data = await response.json();
        renderMatchDetail(data);
    } catch (error) {
        // Utiliser les données locales
        const prediction = state.predictions.find(p => p.match_id === matchId);
        if (prediction) {
            renderMatchDetail({
                match: prediction.match,
                prediction: prediction,
                analysis: {
                    head_to_head: { total_matches: 0 },
                    home_team_form: [],
                    away_team_form: [],
                    home_injuries: [],
                    away_injuries: []
                }
            });
        } else {
            modalBody.innerHTML = '<div class="loading">Détails non disponibles</div>';
        }
    }
}

function renderMatchDetail(data) {
    const { match, prediction, analysis } = data;

    modalBody.innerHTML = `
        <div class="match-detail">
            <div class="detail-header">
                <span class="league-badge">${match.league_name}</span>
                <span class="match-time">${formatDateTime(match.date)}</span>
            </div>

            <div class="teams" style="margin: 24px 0;">
                <div class="team">
                    <img src="${match.home_team.logo || 'https://via.placeholder.com/64'}"
                         alt="${match.home_team.name}"
                         class="team-logo" style="width: 64px; height: 64px;"
                         onerror="this.src='https://via.placeholder.com/64'">
                    <div class="team-name">${match.home_team.name}</div>
                </div>
                <div class="vs">VS</div>
                <div class="team">
                    <img src="${match.away_team.logo || 'https://via.placeholder.com/64'}"
                         alt="${match.away_team.name}"
                         class="team-logo" style="width: 64px; height: 64px;"
                         onerror="this.src='https://via.placeholder.com/64'">
                    <div class="team-name">${match.away_team.name}</div>
                </div>
            </div>

            ${prediction ? `
                <div class="prediction-result">
                    <h3 style="margin-bottom: 12px;">Prédiction</h3>
                    <div class="prediction-row">
                        <span class="prediction-label">Recommandation</span>
                        <span class="prediction-value">${prediction.recommended_bet}</span>
                    </div>
                    <div class="probabilities">
                        <div class="prob-item">
                            <span class="prob-label">1</span>
                            <span class="prob-value">${prediction.home_win_probability}%</span>
                        </div>
                        <div class="prob-item">
                            <span class="prob-label">X</span>
                            <span class="prob-value">${prediction.draw_probability}%</span>
                        </div>
                        <div class="prob-item">
                            <span class="prob-label">2</span>
                            <span class="prob-value">${prediction.away_win_probability}%</span>
                        </div>
                    </div>
                    <p style="margin-top: 12px; color: var(--text-secondary);">
                        ${prediction.analysis_summary}
                    </p>
                    ${prediction.factors && prediction.factors.length > 0 ? `
                        <div style="margin-top: 16px;">
                            <h4 style="margin-bottom: 8px; color: var(--text-secondary);">Facteurs d'analyse</h4>
                            ${prediction.factors.map(f => `<div style="padding: 4px 0;">${f}</div>`).join('')}
                        </div>
                    ` : ''}
                </div>
            ` : ''}

            ${analysis && analysis.head_to_head && analysis.head_to_head.total_matches > 0 ? `
                <div style="margin-top: 20px; padding: 16px; background: var(--bg-card-hover); border-radius: 12px;">
                    <h3 style="margin-bottom: 12px;">Historique des confrontations</h3>
                    <div style="display: flex; justify-content: space-around; text-align: center;">
                        <div>
                            <div style="font-size: 24px; font-weight: bold;">${analysis.head_to_head.home_wins}</div>
                            <div style="color: var(--text-secondary); font-size: 12px;">Victoires ${match.home_team.name}</div>
                        </div>
                        <div>
                            <div style="font-size: 24px; font-weight: bold;">${analysis.head_to_head.draws}</div>
                            <div style="color: var(--text-secondary); font-size: 12px;">Nuls</div>
                        </div>
                        <div>
                            <div style="font-size: 24px; font-weight: bold;">${analysis.head_to_head.away_wins}</div>
                            <div style="color: var(--text-secondary); font-size: 12px;">Victoires ${match.away_team.name}</div>
                        </div>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function closeModal() {
    modal.classList.remove('active');
}

// ==================== Utilitaires ====================

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getConfidenceLabel(confidence) {
    const labels = {
        'very_high': 'Très haute',
        'high': 'Haute',
        'medium': 'Moyenne',
        'low': 'Basse'
    };
    return labels[confidence] || confidence;
}

function updateLeagueFilter() {
    const filter = document.getElementById('league-filter');
    const leagues = [...new Set(state.predictions.map(p => p.match.league_name))];

    filter.innerHTML = '<option value="all">Toutes les ligues</option>' +
        leagues.map(league => `<option value="${league}">${league}</option>`).join('');
}

// ==================== Données de démonstration ====================

function generateDemoData() {
    const teams = [
        { id: 1, name: 'Manchester City', logo: 'https://media.api-sports.io/football/teams/50.png' },
        { id: 2, name: 'Liverpool', logo: 'https://media.api-sports.io/football/teams/40.png' },
        { id: 3, name: 'Arsenal', logo: 'https://media.api-sports.io/football/teams/42.png' },
        { id: 4, name: 'Chelsea', logo: 'https://media.api-sports.io/football/teams/49.png' },
        { id: 5, name: 'Real Madrid', logo: 'https://media.api-sports.io/football/teams/541.png' },
        { id: 6, name: 'Barcelona', logo: 'https://media.api-sports.io/football/teams/529.png' },
        { id: 7, name: 'PSG', logo: 'https://media.api-sports.io/football/teams/85.png' },
        { id: 8, name: 'Bayern Munich', logo: 'https://media.api-sports.io/football/teams/157.png' },
    ];

    const leagues = ['Premier League', 'La Liga', 'Ligue 1', 'Bundesliga'];
    const predictions = [];

    for (let i = 0; i < 6; i++) {
        const homeTeam = teams[i % teams.length];
        const awayTeam = teams[(i + 1) % teams.length];
        const league = leagues[i % leagues.length];

        const homeProb = 30 + Math.random() * 40;
        const awayProb = 20 + Math.random() * 30;
        const drawProb = 100 - homeProb - awayProb;

        let predictedOutcome, recommendedBet;
        if (homeProb > awayProb && homeProb > drawProb) {
            predictedOutcome = 'home';
            recommendedBet = `Victoire ${homeTeam.name}`;
        } else if (awayProb > homeProb && awayProb > drawProb) {
            predictedOutcome = 'away';
            recommendedBet = `Victoire ${awayTeam.name}`;
        } else {
            predictedOutcome = 'draw';
            recommendedBet = 'Match nul';
        }

        const confidences = ['very_high', 'high', 'medium', 'low'];
        const confidence = confidences[Math.floor(Math.random() * 3)];

        predictions.push({
            match_id: i + 1,
            match: {
                id: i + 1,
                league_id: 39,
                league_name: league,
                league_country: 'England',
                date: new Date(state.currentDate + 'T' + (14 + i) + ':00:00').toISOString(),
                home_team: homeTeam,
                away_team: awayTeam,
                venue: 'Stade',
                status: 'scheduled'
            },
            predicted_outcome: predictedOutcome,
            home_win_probability: Math.round(homeProb * 10) / 10,
            draw_probability: Math.round(drawProb * 10) / 10,
            away_win_probability: Math.round(awayProb * 10) / 10,
            confidence: confidence,
            recommended_bet: recommendedBet,
            analysis_summary: `Analyse basée sur la forme récente et l'historique des confrontations.`,
            factors: [
                `${homeTeam.name} en bonne forme`,
                `Avantage domicile significatif`,
                `Historique favorable`
            ]
        });
    }

    return predictions;
}

function generateDemoCombos() {
    if (state.predictions.length < 2) return [];

    const combos = [];

    // Combo sécurisé
    const safePredictions = state.predictions
        .filter(p => p.confidence === 'very_high' || p.confidence === 'high')
        .slice(0, 2);

    if (safePredictions.length >= 2) {
        combos.push({
            id: 'safe1',
            matches: safePredictions.map(p => ({
                match_id: p.match_id,
                teams: `${p.match.home_team.name} vs ${p.match.away_team.name}`,
                prediction: p.recommended_bet,
                confidence: p.confidence,
                probability: Math.max(p.home_win_probability, p.away_win_probability, p.draw_probability)
            })),
            total_probability: 35.5,
            risk_level: 'safe',
            expected_value: 88.75,
            description: 'Combiné sécurisé - 2 matchs haute confiance'
        });
    }

    // Combo modéré
    const moderatePredictions = state.predictions.slice(0, 3);
    combos.push({
        id: 'mod1',
        matches: moderatePredictions.map(p => ({
            match_id: p.match_id,
            teams: `${p.match.home_team.name} vs ${p.match.away_team.name}`,
            prediction: p.recommended_bet,
            confidence: p.confidence,
            probability: Math.max(p.home_win_probability, p.away_win_probability, p.draw_probability)
        })),
        total_probability: 18.2,
        risk_level: 'moderate',
        expected_value: 91.0,
        description: 'Combiné équilibré - 3 matchs'
    });

    // Combo risqué
    const riskyPredictions = state.predictions.slice(0, 5);
    if (riskyPredictions.length >= 4) {
        combos.push({
            id: 'risky1',
            matches: riskyPredictions.map(p => ({
                match_id: p.match_id,
                teams: `${p.match.home_team.name} vs ${p.match.away_team.name}`,
                prediction: p.recommended_bet,
                confidence: p.confidence,
                probability: Math.max(p.home_win_probability, p.away_win_probability, p.draw_probability)
            })),
            total_probability: 5.8,
            risk_level: 'risky',
            expected_value: 87.0,
            description: 'Combiné ambitieux - 5 matchs pour gros gains'
        });
    }

    return combos;
}

// ==================== Démarrage ====================

// Ajouter le style pour l'animation de tremblement
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-10px); }
        75% { transform: translateX(10px); }
    }
`;
document.head.appendChild(style);

// Initialiser le clavier PIN
initPinKeypad();

// Exposer les fonctions globales
window.showMatchDetail = showMatchDetail;
