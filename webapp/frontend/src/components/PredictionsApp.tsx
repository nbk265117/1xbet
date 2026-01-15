import { useState } from 'react';

interface Prediction {
  id: number;
  time: string;
  league: string;
  home: string;
  away: string;
  home_pct: string;
  draw_pct: string;
  away_pct: string;
  prediction: string;
  prediction_text: string;
  over_under: string;
  confidence: number;
  advice: string;
}

interface PredictionResponse {
  date: string;
  total_matches: number;
  predictions: Prediction[];
}

const API_URL = import.meta.env.PUBLIC_API_URL || '';

export default function PredictionsApp() {
  const today = new Date().toISOString().split('T')[0];
  const [selectedDate, setSelectedDate] = useState<string>(today);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalMatches, setTotalMatches] = useState(0);

  const fetchPredictions = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/predictions/${selectedDate}`);

      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des prédictions');
      }

      const data: PredictionResponse = await response.json();
      setPredictions(data.predictions);
      setTotalMatches(data.total_matches);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Une erreur est survenue');
      setPredictions([]);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceStars = (confidence: number): string => {
    return '★'.repeat(confidence) + '☆'.repeat(4 - confidence);
  };

  const getPredictionClass = (prediction: string): string => {
    if (prediction === '1') return 'pred-home';
    if (prediction === '2') return 'pred-away';
    if (prediction === 'X') return 'pred-draw';
    if (prediction === '1X') return 'pred-home-draw';
    if (prediction === 'X2') return 'pred-draw-away';
    return '';
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Football Predictions</h1>
        <p>Analyse et prédictions des matchs de football</p>
      </header>

      <div className="search-section">
        <div className="date-picker-container">
          <label htmlFor="date-input">Sélectionner une date:</label>
          <input
            type="date"
            id="date-input"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="date-input"
          />
        </div>
        <button
          onClick={fetchPredictions}
          disabled={loading}
          className="submit-btn"
        >
          {loading ? 'Chargement...' : 'Analyser les matchs'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {predictions.length > 0 && (
        <div className="results-section">
          <h2>
            TABLEAU RÉCAPITULATIF - {selectedDate}
          </h2>
          <p className="match-count">{totalMatches} matchs analysés</p>

          <div className="table-container">
            <table className="predictions-table">
              <thead>
                <tr>
                  <th>Heure</th>
                  <th>Compétition</th>
                  <th>Match</th>
                  <th>1X2 %</th>
                  <th>Prédiction</th>
                  <th>Over/Under</th>
                  <th>Confiance</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((pred) => (
                  <tr key={pred.id}>
                    <td className="time-cell">{pred.time}</td>
                    <td className="league-cell">{pred.league}</td>
                    <td className="match-cell">
                      <span className="home-team">{pred.home}</span>
                      <span className="vs">vs</span>
                      <span className="away-team">{pred.away}</span>
                    </td>
                    <td className="percent-cell">
                      {pred.home_pct.replace('%', '')}-{pred.draw_pct.replace('%', '')}-{pred.away_pct.replace('%', '')}
                    </td>
                    <td className={`prediction-cell ${getPredictionClass(pred.prediction)}`}>
                      <strong>{pred.prediction}</strong>
                    </td>
                    <td className="over-under-cell">{pred.over_under}</td>
                    <td className="confidence-cell">
                      <span className="stars">{getConfidenceStars(pred.confidence)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="legend">
            <h3>Légende</h3>
            <div className="legend-items">
              <span className="legend-item"><strong>1</strong> = Victoire Domicile</span>
              <span className="legend-item"><strong>2</strong> = Victoire Extérieur</span>
              <span className="legend-item"><strong>X</strong> = Match Nul</span>
              <span className="legend-item"><strong>1X</strong> = Double Chance Dom/Nul</span>
              <span className="legend-item"><strong>X2</strong> = Double Chance Nul/Ext</span>
            </div>
          </div>

          <div className="top-picks">
            <h3>TOP PICKS (Haute Confiance)</h3>
            <div className="picks-grid">
              {predictions
                .filter(p => p.confidence >= 3)
                .slice(0, 5)
                .map((pred) => (
                  <div key={pred.id} className="pick-card">
                    <div className="pick-league">{pred.league}</div>
                    <div className="pick-match">{pred.home} vs {pred.away}</div>
                    <div className="pick-prediction">
                      <span className={getPredictionClass(pred.prediction)}>{pred.prediction}</span>
                      <span className="pick-ou">{pred.over_under}</span>
                    </div>
                    <div className="pick-confidence">{getConfidenceStars(pred.confidence)}</div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {!loading && predictions.length === 0 && !error && (
        <div className="empty-state">
          <p>Sélectionnez une date et cliquez sur "Analyser les matchs" pour voir les prédictions.</p>
        </div>
      )}
    </div>
  );
}
