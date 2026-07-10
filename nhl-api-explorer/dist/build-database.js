"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
function getLocalizedValue(value) {
    if (typeof value === 'string') {
        return value;
    }
    return value?.default || '';
}
function normalizeAwards(awards) {
    if (!Array.isArray(awards)) {
        return [];
    }
    return awards
        .map((award) => {
        if (typeof award === 'string') {
            return award;
        }
        return award?.trophy?.default || 'Unknown Award';
    })
        .filter(Boolean);
}
function normalizeSeasonTotals(seasonTotals) {
    if (!Array.isArray(seasonTotals)) {
        return [];
    }
    return seasonTotals.map((season) => ({
        season: season.season,
        teamAbbrev: season.teamAbbrev,
        teamName: getLocalizedValue(season.teamName),
        teamCommonName: getLocalizedValue(season.teamCommonName),
        gameTypeId: season.gameTypeId,
        leagueAbbrev: season.leagueAbbrev,
        goals: season.goals || 0,
        assists: season.assists || 0,
        points: season.points || 0,
        plusMinus: season.plusMinus || 0,
        pim: season.pim || 0,
        gamesPlayed: season.gamesPlayed || 0,
        shots: season.shots || 0,
        shootingPctg: season.shootingPctg || 0,
    }));
}
function getPositionGroup(position) {
    switch (position) {
        case 'C':
        case 'LW':
        case 'RW':
            return 'Forward';
        case 'D':
            return 'Defense';
        case 'G':
            return 'Goalie';
        default:
            return 'Unknown';
    }
}
function determineActive(lastSeason) {
    const currentYear = new Date().getFullYear();
    const lastSeasonYear = parseInt(lastSeason || '0', 10);
    return lastSeasonYear >= currentYear - 1;
}
async function buildDatabase() {
    try {
        console.log('Building player database...');
        // Read trophies data
        const trophiesPath = path.join(__dirname, '..', 'cache', 'trophies', 'trophies.json');
        let trophiesData = {};
        if (fs.existsSync(trophiesPath)) {
            trophiesData = JSON.parse(fs.readFileSync(trophiesPath, 'utf8'));
            console.log('Loaded trophies data');
        }
        else {
            console.log('Trophies data not found, using API awards data only');
        }
        // Read all players data
        const rawDir = path.join(__dirname, '..', 'output', 'raw');
        const allPlayersFile = path.join(rawDir, 'all-players.json');
        if (!fs.existsSync(allPlayersFile)) {
            console.error('All players data not found. Run download-players first.');
            return;
        }
        const allPlayersData = JSON.parse(fs.readFileSync(allPlayersFile, 'utf8'));
        console.log(`Processing ${allPlayersData.data.length} players...`);
        const processedPlayers = [];
        const errors = [];
        // Process each player
        for (let i = 0; i < allPlayersData.data.length; i++) {
            const player = allPlayersData.data[i];
            const playerId = player.playerId;
            try {
                // Check if we have cached landing data
                const cacheFile = path.join(__dirname, '..', 'cache', 'players', `${playerId}.json`);
                if (!fs.existsSync(cacheFile)) {
                    // For testing, we'll skip players without cached data
                    // In a full implementation, we would fetch the data
                    if (i < 10) { // Only show message for first 10 players
                        console.log(`No cached data for player ${playerId}, skipping...`);
                    }
                    continue;
                }
                const landingData = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
                const seasonTotals = normalizeSeasonTotals(landingData.seasonTotals);
                const awards = normalizeAwards(landingData.awards);
                const firstName = getLocalizedValue(landingData.firstName) || 'Unknown';
                const lastName = getLocalizedValue(landingData.lastName) || 'Unknown';
                const position = landingData.position || 'Unknown';
                // Extract teams played for
                const teams = new Set();
                if (seasonTotals) {
                    seasonTotals.forEach((season) => {
                        const teamName = season.teamName || season.teamCommonName || season.teamAbbrev;
                        if (teamName) {
                            teams.add(teamName);
                        }
                    });
                }
                // Determine rookie and last season
                let rookieSeason = '';
                let lastSeason = '';
                if (seasonTotals && seasonTotals.length > 0) {
                    const seasons = seasonTotals
                        .filter((s) => s.gameTypeId === 2) // Regular season
                        .map((s) => parseInt(s.season, 10))
                        .sort((a, b) => a - b);
                    if (seasons.length > 0) {
                        rookieSeason = seasons[0].toString();
                        lastSeason = seasons[seasons.length - 1].toString();
                    }
                }
                // Extract draft information correctly from draftDetails
                const draftYear = landingData.draftDetails?.year || '';
                const draftRound = landingData.draftDetails?.round || '';
                const draftPick = landingData.draftDetails?.pickInRound || '';
                // Extract awards information from API
                // Add awards from trophies data
                const playerIdStr = playerId.toString();
                Object.entries(trophiesData).forEach(([trophyName, trophyData]) => {
                    Object.values(trophyData).forEach((winners) => {
                        if (Array.isArray(winners)) {
                            const playerWonTrophy = winners.some((winner) => winner.id.toString() === playerIdStr);
                            if (playerWonTrophy && !awards.includes(trophyName)) {
                                awards.push(trophyName);
                            }
                        }
                    });
                });
                // Extract Hall of Fame status
                const inHHOF = landingData.inHHOF === 1 || landingData.inHHOF === true;
                // Extract career highs from season totals
                const careerHighs = {
                    goals: 0,
                    assists: 0,
                    points: 0,
                    plusMinus: 0,
                    pim: 0,
                    gamesPlayed: 0,
                    shots: 0,
                    shootingPctg: 0
                };
                if (seasonTotals && Array.isArray(seasonTotals)) {
                    seasonTotals.forEach((season) => {
                        // Only process NHL regular seasons
                        if (season.leagueAbbrev === 'NHL' && season.gameTypeId === 2) {
                            // Update career highs
                            if (season.goals > careerHighs.goals)
                                careerHighs.goals = season.goals || 0;
                            if (season.assists > careerHighs.assists)
                                careerHighs.assists = season.assists || 0;
                            if (season.points > careerHighs.points)
                                careerHighs.points = season.points || 0;
                            if (season.plusMinus > careerHighs.plusMinus)
                                careerHighs.plusMinus = season.plusMinus || 0;
                            if (season.pim > careerHighs.pim)
                                careerHighs.pim = season.pim || 0;
                            if (season.gamesPlayed > careerHighs.gamesPlayed)
                                careerHighs.gamesPlayed = season.gamesPlayed || 0;
                            if (season.shots > careerHighs.shots)
                                careerHighs.shots = season.shots || 0;
                            if (season.shootingPctg > careerHighs.shootingPctg)
                                careerHighs.shootingPctg = season.shootingPctg || 0;
                        }
                    });
                }
                const processedPlayer = {
                    id: playerId.toString(),
                    name: `${firstName} ${lastName}`,
                    headshot: landingData.headshot || player.headshot || '',
                    position,
                    positionGroup: getPositionGroup(position),
                    birthCountry: landingData.birthCountry || '',
                    birthDate: landingData.birthDate || '',
                    teamsPlayedFor: Array.from(teams),
                    rookieSeason,
                    lastSeason,
                    draftYear: draftYear.toString(),
                    draftRound: draftRound.toString(),
                    draftPick: draftPick.toString(),
                    active: determineActive(lastSeason),
                    careerStats: landingData.careerTotals || {},
                    awards: awards,
                    inHHOF: inHHOF,
                    cups: 0,
                    sweaterNumber: landingData.sweaterNumber || 0,
                    careerHighs
                };
                processedPlayers.push(processedPlayer);
                if (i % 1000 === 0 && i > 0) {
                    console.log(`Processed ${i} players...`);
                }
            }
            catch (error) {
                errors.push(`Error processing player ${playerId}: ${error.message}`);
            }
        }
        // Save the database
        const publicDir = path.join(__dirname, '..', 'public', 'data');
        if (!fs.existsSync(publicDir)) {
            fs.mkdirSync(publicDir, { recursive: true });
        }
        const databaseFile = path.join(publicDir, 'players.json');
        fs.writeFileSync(databaseFile, JSON.stringify(processedPlayers, null, 2));
        console.log(`Database saved to: ${databaseFile}`);
        console.log(`Total players processed: ${processedPlayers.length}`);
        if (errors.length > 0) {
            console.log(`Errors encountered: ${errors.length}`);
            const errorsFile = path.join(__dirname, '..', 'output', 'errors.txt');
            fs.writeFileSync(errorsFile, errors.join('\n'));
            console.log(`Errors saved to: ${errorsFile}`);
        }
        // Display summary statistics
        console.log('\n--- DATABASE SUMMARY ---');
        console.log(`Total players: ${processedPlayers.length}`);
        const positionGroups = processedPlayers.reduce((acc, player) => {
            acc[player.positionGroup] = (acc[player.positionGroup] || 0) + 1;
            return acc;
        }, {});
        console.log('\n--- POSITION GROUPS ---');
        Object.entries(positionGroups).forEach(([group, count]) => {
            console.log(`${group}: ${count}`);
        });
        const countries = processedPlayers.reduce((acc, player) => {
            acc[player.birthCountry] = (acc[player.birthCountry] || 0) + 1;
            return acc;
        }, {});
        const topCountries = Object.entries(countries)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5);
        console.log('\n--- TOP COUNTRIES ---');
        topCountries.forEach(([country, count]) => {
            console.log(`${country}: ${count}`);
        });
        // Show Hall of Fame statistics
        const hhofCount = processedPlayers.filter(player => player.inHHOF).length;
        console.log(`\n--- HALL OF FAME ---`);
        console.log(`Players in HHOF: ${hhofCount}`);
    }
    catch (error) {
        console.error('Error building database:', error.message);
    }
}
buildDatabase();
