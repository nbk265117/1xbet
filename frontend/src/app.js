// Configuration
const API_URL = 'http://localhost:8000';
const CORRECT_PIN = '1991';

// État de l'application
let state = {
    isAuthenticated: false,
    currentDate: new Date().toISOString().split('T')[0],
    predictions: [],
    combos: [],
    markets: [],
    activeTab: 'predictions',
    dataSource: 'polymarket' // 'polymarket' ou 'api-football'
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

        const container = document.querySelector('.pin-container');
        container.style.animation = 'shake 0.5s';
        setTimeout(() => container.style.animation = '', 500);
    }
}

// ==================== Initialisation ====================

function initApp() {
    datePicker.value = state.currentDate;

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

    // Charger les données Polymarket
    loadData();
}

function logout() {
    state.isAuthenticated = false;
    currentPin = '';
    updatePinDisplay();
    mainScreen.classList.remove('active');
    loginScreen.classList.add('active');
}

// ==================== Chargement des données Polymarket ====================

async function loadData() {
    await Promise.all([
        loadPolymarketPredictions(),
        loadPolymarketCombos(),
    ]);
}

async function loadPolymarketPredictions() {
    const container = document.getElementById('predictions-list');
    container.innerHTML = '<div class="loading">Chargement des marchés Polymarket...</div>';

    try {
        const response = await fetch(`${API_URL}/api/polymarket/predictions`);

        if (!response.ok) {
            throw new Error('Erreur serveur');
        }

        const data = await response.json();
        state.predictions = data.predictions || [];
        state.markets = state.predictions;
        renderPredictions();
    } catch (error) {
        console.error('Erreur:', error);
        // Données de démonstration si l'API n'est pas disponible
        state.predictions = generateDemoPolymarketData();
        state.markets = state.predictions;
        renderPredictions();
    }
}

async function loadPolymarketCombos() {
    const container = document.getElementById('combos-list');
    container.innerHTML = '<div class="loading">Chargement des combinés...</div>';

    try {
        const response = await fetch(`${API_URL}/api/polymarket/combos`);

        if (!response.ok) {
            throw new Error('Erreur serveur');
        }

        const data = await response.json();
        state.combos = data.combos || [];
        renderCombos();
    } catch (error) {
        console.error('Erreur:', error);
        state.combos = generateDemoPolymarketCombos();
        renderCombos();
    }
}

// ==================== Rendu Polymarket ====================

function renderPredictions() {
    const container = document.getElementById('predictions-list');
    const confidenceFilter = document.getElementById('confidence-filter').value;

    let filtered = state.predictions;

    if (confidenceFilter !== 'all') {
        filtered = filtered.filter(p => p.confidence === confidenceFilter);
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="loading">
                <p>Aucun marché sportif disponible sur Polymarket.</p>
                <p style="margin-top: 10px; font-size: 14px; color: var(--text-secondary);">
                    Les marchés sportifs sont rares sur Polymarket. Consultez directement
                    <a href="https://polymarket.com" target="_blank" style="color: var(--primary);">polymarket.com</a>
                </p>
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map((market, index) => `
        <div class="prediction-card" onclick="showMarketDetail('${market.id || index}')">
            <div class="match-header">
                <span class="league-badge">Polymarket</span>
                <span class="match-time">${market.volume_formatted || '$0'} volume</span>
            </div>

            <div class="market-question">
                <h3 style="font-size: 16px; margin-bottom: 12px; line-height: 1.4;">
                    ${market.question || 'Question non disponible'}
                </h3>
            </div>

            <div class="teams" style="margin-bottom: 16px;">
                <div class="team">
                    <div class="team-name" style="font-size: 14px;">${market.home_team || 'Option A'}</div>
                </div>
                <div class="vs">VS</div>
                <div class="team">
                    <div class="team-name" style="font-size: 14px;">${market.away_team || 'Option B'}</div>
                </div>
            </div>

            <div class="prediction-result">
                <div class="prediction-row">
                    <span class="prediction-label">Recommandation</span>
                    <span class="prediction-value">${market.recommended_bet || 'N/A'}</span>
                </div>
                <div class="prediction-row">
                    <span class="prediction-label">Probabilité</span>
                    <span class="prediction-value">${(market.best_probability || 50).toFixed(1)}%</span>
                </div>
                ${market.probabilities ? `
                    <div class="probabilities">
                        ${Object.entries(market.probabilities).slice(0, 3).map(([outcome, prob]) => `
                            <div class="prob-item">
                                <span class="prob-label">${outcome.substring(0, 10)}</span>
                                <span class="prob-value">${prob.toFixed(1)}%</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                <span class="confidence-badge confidence-${market.confidence || 'medium'}">
                    ${getConfidenceLabel(market.confidence || 'medium')}
                </span>
                <a href="${market.polymarket_url || '#'}" target="_blank"
                   onclick="event.stopPropagation();"
                   style="color: var(--primary); font-size: 13px; text-decoration: none;">
                    Voir sur Polymarket →
                </a>
            </div>
        </div>
    `).join('');
}

function renderCombos() {
    const container = document.getElementById('combos-list');

    if (state.combos.length === 0) {
        container.innerHTML = `
            <div class="loading">
                <p>Pas assez de marchés pour générer des combinés.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.combos.map(combo => `
        <div class="combo-card">
            <div class="combo-header ${combo.risk_level || 'moderate'}">
                <div class="combo-info">
                    <div class="combo-title">${combo.description || 'Combiné'}</div>
                </div>
                <div class="combo-stats">
                    <div class="combo-prob">${(combo.total_probability || 0).toFixed(1)}%</div>
                    <div class="combo-expected">Probabilité totale</div>
                </div>
            </div>
            <div class="combo-matches">
                ${(combo.matches || []).map(match => `
                    <div class="combo-match">
                        <div style="flex: 1;">
                            <div class="combo-match-teams" style="font-size: 13px; margin-bottom: 4px;">
                                ${match.question || match.teams || 'Match'}
                            </div>
                            <div style="font-size: 12px; color: var(--text-secondary);">
                                Prob: ${(match.probability || 50).toFixed(1)}%
                            </div>
                        </div>
                        <span class="combo-match-bet">${match.bet || match.prediction || 'Pari'}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function renderMatches() {
    const container = document.getElementById('matches-list');

    if (state.markets.length === 0) {
        container.innerHTML = '<div class="loading">Aucun marché disponible.</div>';
        return;
    }

    container.innerHTML = state.markets.map((market, index) => `
        <div class="match-item" onclick="showMarketDetail('${market.id || index}')">
            <div class="match-info">
                <span class="match-league">Polymarket</span>
                <span class="match-teams-inline">${market.question || 'Question'}</span>
            </div>
            <span class="match-datetime">${market.volume_formatted || ''}</span>
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

    // Charger les données du tab si nécessaire
    if (tabName === 'matches') {
        renderMatches();
    }
}

// ==================== Modal ====================

function showMarketDetail(marketId) {
    modal.classList.add('active');

    const market = state.predictions.find(m => m.id === marketId) ||
                   state.predictions[parseInt(marketId)] ||
                   state.predictions[0];

    if (!market) {
        modalBody.innerHTML = '<div class="loading">Marché non trouvé</div>';
        return;
    }

    modalBody.innerHTML = `
        <div class="match-detail">
            <div class="detail-header" style="margin-bottom: 20px;">
                <span class="league-badge">Polymarket</span>
            </div>

            <h2 style="font-size: 20px; margin-bottom: 20px; line-height: 1.4;">
                ${market.question || 'Question'}
            </h2>

            ${market.description ? `
                <p style="color: var(--text-secondary); margin-bottom: 20px; font-size: 14px;">
                    ${market.description}
                </p>
            ` : ''}

            <div class="prediction-result">
                <h3 style="margin-bottom: 12px;">Probabilités du marché</h3>
                ${market.probabilities ? `
                    <div class="probabilities" style="flex-wrap: wrap;">
                        ${Object.entries(market.probabilities).map(([outcome, prob]) => `
                            <div class="prob-item" style="min-width: 100px; margin: 4px;">
                                <span class="prob-label">${outcome}</span>
                                <span class="prob-value">${prob.toFixed(1)}%</span>
                            </div>
                        `).join('')}
                    </div>
                ` : '<p>Pas de données de probabilité</p>'}
            </div>

            <div style="margin-top: 20px; padding: 16px; background: var(--bg-card-hover); border-radius: 12px;">
                <h3 style="margin-bottom: 12px;">Informations du marché</h3>
                <div style="display: grid; gap: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--text-secondary);">Volume</span>
                        <span>${market.volume_formatted || 'N/A'}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--text-secondary);">Liquidité</span>
                        <span>${market.liquidity ? '$' + parseFloat(market.liquidity).toLocaleString() : 'N/A'}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--text-secondary);">Date de fin</span>
                        <span>${market.end_date ? new Date(market.end_date).toLocaleDateString('fr-FR') : 'N/A'}</span>
                    </div>
                </div>
            </div>

            <div style="margin-top: 20px;">
                <a href="${market.polymarket_url || 'https://polymarket.com'}"
                   target="_blank"
                   class="btn-primary"
                   style="display: block; text-align: center; padding: 16px; background: var(--primary);
                          color: white; border-radius: 12px; text-decoration: none; font-weight: 600;">
                    Parier sur Polymarket →
                </a>
            </div>
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
        'very_high': 'Haute liquidité',
        'high': 'Bonne liquidité',
        'medium': 'Liquidité moyenne',
        'low': 'Faible liquidité'
    };
    return labels[confidence] || confidence;
}

// ==================== Données de démonstration Polymarket ====================

function generateDemoPolymarketData() {
    return [
        {
            id: "demo_1",
            question: "Will Manchester City win the Premier League 2025-26?",
            description: "Market resolves YES if Manchester City wins the Premier League title for the 2025-26 season.",
            home_team: "Manchester City",
            away_team: "Other Teams",
            outcomes: ["Yes", "No"],
            probabilities: { "Yes": 45.5, "No": 54.5 },
            volume: 125000,
            volume_formatted: "$125,000",
            liquidity: 45000,
            recommended_bet: "Yes",
            best_probability: 45.5,
            confidence: "very_high",
            polymarket_url: "https://polymarket.com",
            end_date: "2026-05-30",
        },
        {
            id: "demo_2",
            question: "Will Real Madrid win Champions League 2025-26?",
            description: "Market resolves YES if Real Madrid wins the UEFA Champions League.",
            home_team: "Real Madrid",
            away_team: "Other Teams",
            outcomes: ["Yes", "No"],
            probabilities: { "Yes": 28.3, "No": 71.7 },
            volume: 89000,
            volume_formatted: "$89,000",
            liquidity: 32000,
            recommended_bet: "No",
            best_probability: 71.7,
            confidence: "high",
            polymarket_url: "https://polymarket.com",
            end_date: "2026-06-15",
        },
        {
            id: "demo_3",
            question: "Will France win the 2026 World Cup?",
            description: "Market resolves YES if France wins the FIFA World Cup 2026.",
            home_team: "France",
            away_team: "Other Nations",
            outcomes: ["Yes", "No"],
            probabilities: { "Yes": 18.5, "No": 81.5 },
            volume: 250000,
            volume_formatted: "$250,000",
            liquidity: 78000,
            recommended_bet: "No",
            best_probability: 81.5,
            confidence: "very_high",
            polymarket_url: "https://polymarket.com",
            end_date: "2026-07-19",
        },
        {
            id: "demo_4",
            question: "Will Liverpool finish in Top 4 Premier League?",
            description: "Market resolves YES if Liverpool finishes in the top 4 positions.",
            home_team: "Liverpool",
            away_team: "Others",
            outcomes: ["Yes", "No"],
            probabilities: { "Yes": 72.0, "No": 28.0 },
            volume: 67000,
            volume_formatted: "$67,000",
            liquidity: 25000,
            recommended_bet: "Yes",
            best_probability: 72.0,
            confidence: "high",
            polymarket_url: "https://polymarket.com",
            end_date: "2026-05-30",
        },
        {
            id: "demo_5",
            question: "Will PSG win Ligue 1 2025-26?",
            description: "Paris Saint-Germain to win the French Ligue 1 championship.",
            home_team: "PSG",
            away_team: "Other Teams",
            outcomes: ["Yes", "No"],
            probabilities: { "Yes": 65.8, "No": 34.2 },
            volume: 45000,
            volume_formatted: "$45,000",
            liquidity: 18000,
            recommended_bet: "Yes",
            best_probability: 65.8,
            confidence: "medium",
            polymarket_url: "https://polymarket.com",
            end_date: "2026-05-25",
        },
    ];
}

function generateDemoPolymarketCombos() {
    const predictions = generateDemoPolymarketData();

    return [
        {
            id: "safe_combo",
            description: "Combiné Sécurisé - 2 marchés haute probabilité",
            risk_level: "safe",
            total_probability: 51.84,
            matches: [
                {
                    question: "Will Liverpool finish in Top 4?",
                    bet: "Yes (72%)",
                    probability: 72.0,
                },
                {
                    question: "Will PSG win Ligue 1?",
                    bet: "Yes (65.8%)",
                    probability: 65.8,
                },
            ],
        },
        {
            id: "moderate_combo",
            description: "Combiné Équilibré - 3 marchés",
            risk_level: "moderate",
            total_probability: 21.2,
            matches: [
                {
                    question: "Liverpool Top 4?",
                    bet: "Yes",
                    probability: 72.0,
                },
                {
                    question: "PSG champion Ligue 1?",
                    bet: "Yes",
                    probability: 65.8,
                },
                {
                    question: "Man City Premier League?",
                    bet: "Yes",
                    probability: 45.5,
                },
            ],
        },
        {
            id: "risky_combo",
            description: "Combiné Ambitieux - Gros gains potentiels",
            risk_level: "risky",
            total_probability: 3.9,
            matches: [
                {
                    question: "Liverpool Top 4?",
                    bet: "Yes",
                    probability: 72.0,
                },
                {
                    question: "Real Madrid Champions League?",
                    bet: "Yes",
                    probability: 28.3,
                },
                {
                    question: "France World Cup 2026?",
                    bet: "Yes",
                    probability: 18.5,
                },
            ],
        },
    ];
}

// ==================== Démarrage ====================

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
window.showMarketDetail = showMarketDetail;
