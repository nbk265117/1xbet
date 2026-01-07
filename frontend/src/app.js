// Configuration
const API_URL = 'http://localhost:8000';
const CORRECT_PIN = '1991';

// État de l'application
let state = {
    isAuthenticated: false,
    predictions: [],
    combos: [],
    activeTab: 'predictions',
    selectedDate: new Date().toISOString().split('T')[0]
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

        const container = document.querySelector('.pin-container');
        container.style.animation = 'shake 0.5s';
        setTimeout(() => container.style.animation = '', 500);
    }
}

// ==================== Initialisation ====================

function initApp() {
    datePicker.value = state.selectedDate;

    document.getElementById('logout-btn').addEventListener('click', logout);

    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    document.querySelector('.modal-close').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    document.getElementById('confidence-filter').addEventListener('change', renderPredictions);
    document.getElementById('league-filter').addEventListener('change', renderPredictions);

    // Écouter le changement de date
    datePicker.addEventListener('change', (e) => {
        state.selectedDate = e.target.value;
        loadData();
    });

    loadData();
}

function logout() {
    state.isAuthenticated = false;
    currentPin = '';
    updatePinDisplay();
    mainScreen.classList.remove('active');
    loginScreen.classList.add('active');
}

// ==================== Chargement des données (API-Football + Odds API) ====================

async function loadData() {
    await Promise.all([
        loadPredictions(),
        loadCombos(),
    ]);
}

async function loadPredictions() {
    const container = document.getElementById('predictions-list');
    container.innerHTML = '<div class="loading">Chargement des matchs...</div>';

    try {
        const response = await fetch(`${API_URL}/api/polymarket/predictions`);

        if (!response.ok) throw new Error('Erreur serveur');

        const data = await response.json();
        state.predictions = data.predictions || [];
        updateLeagueFilter();
        renderPredictions();
    } catch (error) {
        console.error('Erreur:', error);
        container.innerHTML = '<div class="loading">Erreur de chargement. Vérifiez que le backend est lancé.</div>';
    }
}

async function loadCombos() {
    const container = document.getElementById('combos-list');
    container.innerHTML = '<div class="loading">Chargement des combinés...</div>';

    try {
        const response = await fetch(`${API_URL}/api/polymarket/combos`);

        if (!response.ok) throw new Error('Erreur serveur');

        const data = await response.json();
        state.combos = data.combos || [];
        renderCombos();
    } catch (error) {
        console.error('Erreur:', error);
        container.innerHTML = '<div class="loading">Erreur de chargement.</div>';
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
        filtered = filtered.filter(p => p.league === leagueFilter);
    }

    if (filtered.length === 0) {
        container.innerHTML = '<div class="loading">Aucun match trouvé pour cette date.</div>';
        return;
    }

    container.innerHTML = filtered.map((match, index) => `
        <div class="prediction-card" onclick="showMatchDetail('${match.id}')">
            <div class="match-header">
                <span class="league-badge">${match.league || 'Football'}</span>
                <span class="match-time">${formatMatchTime(match.match_date)}</span>
            </div>

            <div class="teams">
                <div class="team">
                    <img src="${match.home_logo || 'https://via.placeholder.com/48'}"
                         alt="${match.home_team}"
                         class="team-logo"
                         onerror="this.src='https://via.placeholder.com/48?text=${match.home_team?.charAt(0) || 'H'}'">
                    <div class="team-name">${match.home_team}</div>
                </div>
                <div class="exact-score">${match.exact_score || '?-?'}</div>
                <div class="team">
                    <img src="${match.away_logo || 'https://via.placeholder.com/48'}"
                         alt="${match.away_team}"
                         class="team-logo"
                         onerror="this.src='https://via.placeholder.com/48?text=${match.away_team?.charAt(0) || 'A'}'">
                    <div class="team-name">${match.away_team}</div>
                </div>
            </div>

            <div class="winner-display">
                <span class="winner-label">Gagnant:</span>
                <span class="winner-value ${match.winner === 'Nul' ? 'draw' : 'win'}">${match.winner || match.recommended_bet}</span>
            </div>

            <div class="prediction-result">
                <div class="odds-display">
                    <div class="odd-item ${match.predicted_outcome === 'home' ? 'highlight' : ''}">
                        <span class="odd-label">1</span>
                        <span class="odd-value">${match.odds?.['1']?.toFixed(2) || '-'}</span>
                        <span class="odd-prob">${match.probabilities?.['1']?.toFixed(0) || 0}%</span>
                    </div>
                    <div class="odd-item ${match.predicted_outcome === 'draw' ? 'highlight' : ''}">
                        <span class="odd-label">X</span>
                        <span class="odd-value">${match.odds?.['X']?.toFixed(2) || '-'}</span>
                        <span class="odd-prob">${match.probabilities?.['X']?.toFixed(0) || 0}%</span>
                    </div>
                    <div class="odd-item ${match.predicted_outcome === 'away' ? 'highlight' : ''}">
                        <span class="odd-label">2</span>
                        <span class="odd-value">${match.odds?.['2']?.toFixed(2) || '-'}</span>
                        <span class="odd-prob">${match.probabilities?.['2']?.toFixed(0) || 0}%</span>
                    </div>
                </div>
            </div>

            <span class="confidence-badge confidence-${match.confidence}">
                ${getConfidenceLabel(match.confidence)}
            </span>
        </div>
    `).join('');
}

function renderCombos() {
    const container = document.getElementById('combos-list');

    if (state.combos.length === 0) {
        container.innerHTML = '<div class="loading">Aucun combiné disponible.</div>';
        return;
    }

    container.innerHTML = state.combos.map(combo => `
        <div class="combo-card">
            <div class="combo-header ${combo.risk_level || 'moderate'}">
                <div class="combo-info">
                    <div class="combo-title">${combo.description}</div>
                    <div class="combo-type">${combo.matches?.length || 0} matchs</div>
                </div>
                <div class="combo-stats">
                    <div class="combo-odds">Cote: ${combo.total_odds?.toFixed(2) || '-'}</div>
                    <div class="combo-return">${combo.potential_return || ''}</div>
                </div>
            </div>
            <div class="combo-matches">
                ${(combo.matches || []).map(match => `
                    <div class="combo-match">
                        <div class="combo-match-info">
                            <div class="combo-match-teams">${match.teams || match.question}</div>
                            <div class="combo-match-league">${match.league || ''}</div>
                        </div>
                        <div class="combo-match-odds">
                            <span class="combo-match-bet">${match.bet}</span>
                            <span class="combo-match-odd">@${match.odds?.toFixed(2) || '-'}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function renderMatches() {
    const container = document.getElementById('matches-list');

    if (state.predictions.length === 0) {
        container.innerHTML = '<div class="loading">Aucun match disponible.</div>';
        return;
    }

    container.innerHTML = state.predictions.map(match => `
        <div class="match-item" onclick="showMatchDetail('${match.id}')">
            <div class="match-info">
                <span class="match-league">${match.league}</span>
                <span class="match-teams-inline">${match.home_team} vs ${match.away_team}</span>
            </div>
            <div class="match-odds-inline">
                <span class="odd-inline">${match.odds?.['1']?.toFixed(2) || '-'}</span>
                <span class="odd-inline">${match.odds?.['X']?.toFixed(2) || '-'}</span>
                <span class="odd-inline">${match.odds?.['2']?.toFixed(2) || '-'}</span>
            </div>
        </div>
    `).join('');
}

// ==================== Navigation ====================

function switchTab(tabName) {
    state.activeTab = tabName;

    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });

    if (tabName === 'matches') {
        renderMatches();
    }
}

// ==================== Modal ====================

function showMatchDetail(matchId) {
    modal.classList.add('active');

    const match = state.predictions.find(m => m.id === matchId);

    if (!match) {
        modalBody.innerHTML = '<div class="loading">Match non trouvé</div>';
        return;
    }

    modalBody.innerHTML = `
        <div class="match-detail">
            <div class="detail-header">
                <span class="league-badge">${match.league}</span>
                <span class="match-time">${formatMatchTime(match.match_date)}</span>
            </div>

            <div class="teams" style="margin: 24px 0;">
                <div class="team">
                    <img src="${match.home_logo || 'https://via.placeholder.com/64'}"
                         alt="${match.home_team}"
                         class="team-logo" style="width: 64px; height: 64px;"
                         onerror="this.src='https://via.placeholder.com/64'">
                    <div class="team-name">${match.home_team}</div>
                </div>
                <div class="vs">VS</div>
                <div class="team">
                    <img src="${match.away_logo || 'https://via.placeholder.com/64'}"
                         alt="${match.away_team}"
                         class="team-logo" style="width: 64px; height: 64px;"
                         onerror="this.src='https://via.placeholder.com/64'">
                    <div class="team-name">${match.away_team}</div>
                </div>
            </div>

            <div class="prediction-result">
                <h3 style="margin-bottom: 12px;">Prédiction 1xbet</h3>
                <div class="prediction-row">
                    <span class="prediction-label">Recommandation</span>
                    <span class="prediction-value" style="color: var(--success);">${match.recommended_bet}</span>
                </div>
                <div class="odds-display" style="margin-top: 16px;">
                    <div class="odd-item ${match.predicted_outcome === 'home' ? 'highlight' : ''}">
                        <span class="odd-label">1 (${match.home_team})</span>
                        <span class="odd-value">${match.odds?.['1']?.toFixed(2) || '-'}</span>
                        <span class="odd-prob">${match.probabilities?.['1']?.toFixed(0)}%</span>
                    </div>
                    <div class="odd-item ${match.predicted_outcome === 'draw' ? 'highlight' : ''}">
                        <span class="odd-label">X (Nul)</span>
                        <span class="odd-value">${match.odds?.['X']?.toFixed(2) || '-'}</span>
                        <span class="odd-prob">${match.probabilities?.['X']?.toFixed(0)}%</span>
                    </div>
                    <div class="odd-item ${match.predicted_outcome === 'away' ? 'highlight' : ''}">
                        <span class="odd-label">2 (${match.away_team})</span>
                        <span class="odd-value">${match.odds?.['2']?.toFixed(2) || '-'}</span>
                        <span class="odd-prob">${match.probabilities?.['2']?.toFixed(0)}%</span>
                    </div>
                </div>
            </div>

            ${match.factors && match.factors.length > 0 ? `
                <div style="margin-top: 20px; padding: 16px; background: var(--bg-card-hover); border-radius: 12px;">
                    <h3 style="margin-bottom: 12px;">Facteurs d'analyse</h3>
                    ${match.factors.map(f => `
                        <div style="padding: 8px 0; border-bottom: 1px solid var(--border);">
                            ✓ ${f}
                        </div>
                    `).join('')}
                </div>
            ` : ''}

            <div style="margin-top: 20px; display: flex; gap: 12px;">
                <span class="confidence-badge confidence-${match.confidence}" style="flex: 1; text-align: center; padding: 12px;">
                    ${getConfidenceLabel(match.confidence)}
                </span>
            </div>
        </div>
    `;
}

function closeModal() {
    modal.classList.remove('active');
}

// ==================== Utilitaires ====================

function formatMatchTime(dateString) {
    if (!dateString) return '';
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
        'very_high': 'Confiance Très Haute',
        'high': 'Confiance Haute',
        'medium': 'Confiance Moyenne',
        'low': 'Confiance Basse'
    };
    return labels[confidence] || confidence;
}

function updateLeagueFilter() {
    const filter = document.getElementById('league-filter');
    const leagues = [...new Set(state.predictions.map(p => p.league).filter(Boolean))];

    filter.innerHTML = '<option value="all">Toutes les ligues</option>' +
        leagues.map(league => `<option value="${league}">${league}</option>`).join('');
}

// ==================== Styles supplémentaires ====================

const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-10px); }
        75% { transform: translateX(10px); }
    }

    .odds-display {
        display: flex;
        gap: 8px;
        margin-top: 12px;
    }

    .odd-item {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 10px 8px;
        background: var(--bg-card-hover);
        border-radius: 8px;
        transition: all 0.2s;
    }

    .odd-item.highlight {
        background: var(--primary) !important;
        color: white !important;
    }

    .odd-item.highlight .odd-label,
    .odd-item.highlight .odd-value,
    .odd-item.highlight .odd-prob {
        color: white !important;
    }

    .odd-label {
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 4px;
    }

    .odd-value {
        font-size: 18px;
        font-weight: 700;
        color: var(--primary);
    }

    .odd-prob {
        font-size: 11px;
        color: var(--text-secondary);
        margin-top: 2px;
    }

    .combo-stats {
        text-align: right;
    }

    .combo-odds {
        font-size: 20px;
        font-weight: 700;
        color: var(--success);
    }

    .combo-return {
        font-size: 12px;
        color: var(--text-secondary);
        margin-top: 4px;
    }

    .combo-match {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid var(--border);
    }

    .combo-match:last-child {
        border-bottom: none;
    }

    .combo-match-info {
        flex: 1;
    }

    .combo-match-teams {
        font-weight: 500;
        margin-bottom: 4px;
    }

    .combo-match-league {
        font-size: 12px;
        color: var(--text-secondary);
    }

    .combo-match-odds {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 4px;
    }

    .combo-match-bet {
        background: var(--primary);
        color: white;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }

    .combo-match-odd {
        font-size: 14px;
        font-weight: 600;
        color: var(--success);
    }

    .combo-type {
        font-size: 12px;
        opacity: 0.8;
        margin-top: 4px;
    }

    .match-odds-inline {
        display: flex;
        gap: 8px;
    }

    .odd-inline {
        background: var(--bg-card-hover);
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
    }

    .prob-item.highlight {
        background: var(--primary) !important;
        color: white !important;
    }

    .prob-item.highlight .prob-label,
    .prob-item.highlight .prob-value {
        color: white !important;
    }
`;
document.head.appendChild(style);

// ==================== Démarrage ====================

initPinKeypad();

window.showMatchDetail = showMatchDetail;
