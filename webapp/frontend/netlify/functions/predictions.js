const API_KEY = "111a3d8d8abb91aacf250df4ea6f5116";
const BASE_URL = "https://v3.football.api-sports.io";

const PRIORITY_LEAGUES = {
  39: "Premier League",
  140: "La Liga",
  135: "Serie A",
  78: "Bundesliga",
  61: "Ligue 1",
  2: "Champions League",
  3: "Europa League",
  848: "Conference League",
  262: "Liga MX",
  94: "Primeira Liga",
  88: "Eredivisie",
  90: "KNVB Beker",
  144: "Jupiler Pro",
  203: "Super Lig",
  206: "Türkiye Kupası",
  179: "Scottish Prem",
  197: "Super League",
  307: "Saudi Pro League",
  305: "Qatar Stars",
  301: "UAE Pro League",
  330: "Kuwait Premier",
  417: "Bahrain Premier",
  895: "Egypt Cup",
  233: "Egypt Premier",
};

function getConfidence(homePct, awayPct, drawPct) {
  try {
    const home = parseInt(homePct.replace('%', ''));
    const away = parseInt(awayPct.replace('%', ''));
    const draw = parseInt(drawPct.replace('%', ''));
    const maxProb = Math.max(home, away, draw);
    if (maxProb >= 50) return 4;
    if (maxProb >= 45) return 3;
    return 2;
  } catch {
    return 2;
  }
}

function determinePrediction(homePct, awayPct, drawPct, homeName, awayName) {
  try {
    const home = parseInt(homePct.replace('%', ''));
    const away = parseInt(awayPct.replace('%', ''));
    const draw = parseInt(drawPct.replace('%', ''));

    const bigClubs = ["Al Ahly", "Zamalek", "Zamalek SC", "Pyramids FC"];

    if (home >= 45 && away <= 10) {
      return { prediction: "1", text: `${homeName} gagne` };
    } else if (away >= 45 && home <= 10) {
      if (bigClubs.some(club => homeName.includes(club))) {
        return { prediction: "1X", text: `DC ${homeName}` };
      }
      return { prediction: "2", text: `${awayName} gagne` };
    } else if (home >= 35 && draw >= 35) {
      return { prediction: "1X", text: `DC ${homeName}` };
    } else if (away >= 35 && draw >= 35) {
      return { prediction: "X2", text: `DC ${awayName}` };
    } else if (draw >= 40) {
      return { prediction: "X", text: "Match Nul probable" };
    } else {
      if (home > away) {
        return { prediction: "1X", text: `DC ${homeName}` };
      }
      return { prediction: "X2", text: `DC ${awayName}` };
    }
  } catch {
    return { prediction: "X", text: "Match Nul" };
  }
}

function determineOverUnder(goalsHome, goalsAway, advice) {
  try {
    if (goalsHome && goalsAway) {
      if (String(goalsHome).includes("3.5") || String(goalsAway).includes("3.5")) {
        return "Over 2.5";
      } else if (String(goalsHome).includes("2.5") || String(goalsAway).includes("2.5")) {
        return "Under 3.5";
      }
    }
  } catch {}

  if (advice) {
    if (advice.includes("+2.5") || advice.includes("+3.5")) {
      return "Over 2.5";
    } else if (advice.includes("-2.5") || advice.includes("-3.5")) {
      return "Under 2.5";
    }
  }

  return "Under 2.5";
}

function determineBTTS(teams, comparison) {
  try {
    const homeGoalsFor = parseFloat(teams?.home?.league?.goals?.for?.average?.total || 0);
    const awayGoalsFor = parseFloat(teams?.away?.league?.goals?.for?.average?.total || 0);
    const homeGoalsAgainst = parseFloat(teams?.home?.league?.goals?.against?.average?.total || 0);
    const awayGoalsAgainst = parseFloat(teams?.away?.league?.goals?.against?.average?.total || 0);

    // Si les deux équipes marquent en moyenne > 0.8 but et encaissent > 0.8 but
    if (homeGoalsFor > 0.8 && awayGoalsFor > 0.8 && homeGoalsAgainst > 0.8 && awayGoalsAgainst > 0.8) {
      return "Oui";
    }
    // Si une équipe a une défense très solide
    if (homeGoalsAgainst < 0.5 || awayGoalsAgainst < 0.5) {
      return "Non";
    }
    // Défaut basé sur les stats d'attaque
    if (homeGoalsFor > 1 && awayGoalsFor > 1) {
      return "Oui";
    }
    return "Non";
  } catch {
    return "Non";
  }
}

function determineExactScore(prediction, teams, goalsHome, goalsAway) {
  try {
    const homeAvgFor = parseFloat(teams?.home?.league?.goals?.for?.average?.home || 1.2);
    const awayAvgFor = parseFloat(teams?.away?.league?.goals?.for?.average?.away || 0.9);

    // Arrondir les moyennes
    let homeGoals = Math.round(homeAvgFor);
    let awayGoals = Math.round(awayAvgFor);

    // Ajuster selon la prédiction
    if (prediction === "1" || prediction === "1X") {
      homeGoals = Math.max(homeGoals, awayGoals + 1);
    } else if (prediction === "2" || prediction === "X2") {
      awayGoals = Math.max(awayGoals, homeGoals + 1);
    } else if (prediction === "X") {
      awayGoals = homeGoals;
    }

    // Limiter les scores extrêmes
    homeGoals = Math.min(Math.max(homeGoals, 0), 4);
    awayGoals = Math.min(Math.max(awayGoals, 0), 3);

    return `${homeGoals}-${awayGoals}`;
  } catch {
    return "1-1";
  }
}

async function fetchPrediction(fixtureId, fixtureInfo) {
  try {
    const resp = await fetch(`${BASE_URL}/predictions?fixture=${fixtureId}`, {
      headers: { "x-apisports-key": API_KEY }
    });
    const data = await resp.json();
    const pred = data.response?.[0];

    if (!pred) return null;

    const predictions = pred.predictions || {};
    const percent = predictions.percent || {};
    const goals = predictions.goals || {};
    const teams = pred.teams || {};
    const comparison = pred.comparison || {};

    const homePct = percent.home || "33%";
    const drawPct = percent.draw || "33%";
    const awayPct = percent.away || "33%";
    const advice = predictions.advice || "";

    const { prediction, text } = determinePrediction(
      homePct, awayPct, drawPct,
      fixtureInfo.home, fixtureInfo.away
    );

    const overUnder = determineOverUnder(goals.home, goals.away, advice);
    const confidence = getConfidence(homePct, awayPct, drawPct);
    const btts = determineBTTS(teams, comparison);
    const exactScore = determineExactScore(prediction, teams, goals.home, goals.away);

    return {
      id: fixtureId,
      time: fixtureInfo.time,
      league: fixtureInfo.league,
      home: fixtureInfo.home,
      away: fixtureInfo.away,
      home_pct: homePct,
      draw_pct: drawPct,
      away_pct: awayPct,
      prediction,
      prediction_text: text,
      over_under: overUnder,
      btts,
      exact_score: exactScore,
      confidence,
      advice
    };
  } catch (e) {
    console.error(`Error fetching prediction for ${fixtureId}:`, e);
    return null;
  }
}

export const handler = async (event) => {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json"
  };

  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers, body: "" };
  }

  try {
    // Extract date from path: /api/predictions/2026-01-15 -> 2026-01-15
    const pathParts = event.path.split('/');
    const date = pathParts[pathParts.length - 1];

    // Validate date format
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: "Format de date invalide. Utilisez YYYY-MM-DD" })
      };
    }

    // Fetch fixtures for the date
    const fixturesResp = await fetch(`${BASE_URL}/fixtures?date=${date}`, {
      headers: { "x-apisports-key": API_KEY }
    });
    const fixturesData = await fixturesResp.json();
    const fixtures = fixturesData.response || [];

    if (fixtures.length === 0) {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ date, total_matches: 0, predictions: [] })
      };
    }

    // Filter important fixtures
    const importantFixtures = [];
    for (const f of fixtures) {
      const leagueId = f.league.id;
      const leagueName = f.league.name;

      const isPriority = leagueId in PRIORITY_LEAGUES;
      const isImportantName = ["Serie A", "Liga", "Premier", "Bundesliga", "Ligue 1", "Champions", "Europa", "Cup", "Copa", "Coupe"]
        .some(kw => leagueName.includes(kw));

      if (isPriority || isImportantName) {
        importantFixtures.push({
          id: f.fixture.id,
          time: f.fixture.date.substring(11, 16),
          league: leagueName,
          home: f.teams.home.name,
          away: f.teams.away.name
        });
      }
    }

    // Limit to 25 matches to avoid timeout
    const limitedFixtures = importantFixtures.slice(0, 25);

    // Fetch predictions in parallel
    const predictionPromises = limitedFixtures.map(fix => fetchPrediction(fix.id, fix));
    const results = await Promise.all(predictionPromises);

    // Filter valid results and sort by time
    const predictions = results.filter(r => r !== null);
    predictions.sort((a, b) => a.time.localeCompare(b.time));

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        date,
        total_matches: predictions.length,
        predictions
      })
    };
  } catch (error) {
    console.error("Error:", error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: "Erreur serveur" })
    };
  }
};
