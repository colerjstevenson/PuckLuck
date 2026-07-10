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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const axios_1 = __importDefault(require("axios"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
async function inspectPlayer(playerId) {
    try {
        console.log(`Inspecting player with ID: ${playerId}`);
        // Create output directory if it doesn't exist
        const outputDir = path.join(__dirname, '..', 'output', 'raw');
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }
        // Fetch player landing data
        const landingUrl = `https://api-web.nhle.com/v1/player/${playerId}/landing`;
        console.log(`Fetching from: ${landingUrl}`);
        const response = await axios_1.default.get(landingUrl);
        const rawData = response.data;
        // Save raw data
        const outputFile = path.join(outputDir, `${playerId}.json`);
        fs.writeFileSync(outputFile, JSON.stringify(rawData, null, 2));
        console.log(`Raw data saved to: ${outputFile}`);
        // Extract awards information
        const awards = [];
        if (rawData.awards && Array.isArray(rawData.awards)) {
            rawData.awards.forEach((award) => {
                const trophyName = award.trophy?.default || 'Unknown Award';
                awards.push(trophyName);
            });
        }
        // Extract career highs from season totals
        const careerHighs = {
            goals: 0,
            assists: 0,
            points: 0,
            plusMinus: 0,
            pim: 0,
            gamesPlayed: 0,
            shots: 0,
            shootingPctg: 0,
            timeOnIce: ''
        };
        const seasons = [];
        if (rawData.seasonTotals && Array.isArray(rawData.seasonTotals)) {
            rawData.seasonTotals.forEach((season) => {
                // Only process NHL regular seasons
                if (season.leagueAbbrev === 'NHL' && season.gameTypeId === 2) {
                    seasons.push({
                        seasonId: season.season,
                        team: season.teamAbbrev,
                        gamesPlayed: season.gamesPlayed,
                        goals: season.goals,
                        assists: season.assists,
                        points: season.points,
                        plusMinus: season.plusMinus,
                        pim: season.pim,
                        shots: season.shots,
                        shootingPctg: season.shootingPctg,
                        timeOnIce: season.avgToi,
                        powerPlayGoals: season.powerPlayGoals,
                        powerPlayPoints: season.powerPlayPoints,
                        shortHandedGoals: season.shorthandedGoals,
                        shortHandedPoints: season.shorthandedPoints,
                        gameWinningGoals: season.gameWinningGoals,
                        otGoals: season.otGoals
                    });
                    // Update career highs
                    if (season.goals > careerHighs.goals)
                        careerHighs.goals = season.goals;
                    if (season.assists > careerHighs.assists)
                        careerHighs.assists = season.assists;
                    if (season.points > careerHighs.points)
                        careerHighs.points = season.points;
                    if (season.plusMinus > careerHighs.plusMinus)
                        careerHighs.plusMinus = season.plusMinus;
                    if (season.pim > careerHighs.pim)
                        careerHighs.pim = season.pim;
                    if (season.gamesPlayed > careerHighs.gamesPlayed)
                        careerHighs.gamesPlayed = season.gamesPlayed;
                    if (season.shots > careerHighs.shots)
                        careerHighs.shots = season.shots;
                    if (season.shootingPctg > careerHighs.shootingPctg)
                        careerHighs.shootingPctg = season.shootingPctg;
                }
            });
        }
        // Process data into our model
        const playerData = {
            id: rawData.playerId.toString(),
            fullName: `${rawData.firstName.default} ${rawData.lastName.default}`,
            headshot: rawData.headshot || '',
            position: rawData.position,
            birthCountry: rawData.birthCountry || '',
            birthDate: rawData.birthDate || '',
            draftYear: rawData.draftDetails?.year || 0,
            draftRound: rawData.draftDetails?.round || 0,
            draftPick: rawData.draftDetails?.pickInRound || 0,
            careerStats: rawData.careerTotals || {},
            teamsPlayedFor: [],
            awards: awards,
            inHHOF: rawData.inHHOF === 1,
            sweaterNumber: rawData.sweaterNumber || 0,
            careerHighs,
            seasons
        };
        // Extract teams played for
        if (rawData.seasonTotals) {
            const teams = new Set();
            rawData.seasonTotals.forEach((season) => {
                if (season.teamAbbrev) {
                    teams.add(season.teamAbbrev);
                }
            });
            playerData.teamsPlayedFor = Array.from(teams);
        }
        // Display human-readable summary
        console.log('\n--- PLAYER SUMMARY ---');
        console.log(`Player: ${playerData.fullName}`);
        console.log(`Position: ${playerData.position}`);
        console.log(`Country: ${playerData.birthCountry || 'N/A'}`);
        console.log(`Draft: ${playerData.draftYear || 'N/A'} Round ${playerData.draftRound || 'N/A'} Pick ${playerData.draftPick || 'N/A'}`);
        console.log(`Jersey Number: ${playerData.sweaterNumber || 'N/A'}`);
        console.log(`Hall of Fame: ${playerData.inHHOF ? 'Yes' : 'No'}`);
        if (playerData.awards.length > 0) {
            console.log('\n--- AWARDS ---');
            playerData.awards.forEach(award => console.log(`- ${award}`));
        }
        if (playerData.careerHighs) {
            console.log('\n--- CAREER HIGHS ---');
            console.log(`Goals: ${playerData.careerHighs.goals}`);
            console.log(`Assists: ${playerData.careerHighs.assists}`);
            console.log(`Points: ${playerData.careerHighs.points}`);
            console.log(`Games Played: ${playerData.careerHighs.gamesPlayed}`);
        }
        if (playerData.careerStats && playerData.careerStats.regularSeason) {
            const regSeason = playerData.careerStats.regularSeason;
            console.log('\n--- CAREER ---');
            console.log(`Games: ${regSeason.gamesPlayed || 0}`);
            console.log(`Goals: ${regSeason.goals || 0}`);
            console.log(`Points: ${regSeason.points || 0}`);
        }
        if (playerData.teamsPlayedFor.length > 0) {
            console.log(`\n--- TEAMS PLAYED FOR ---`);
            console.log(playerData.teamsPlayedFor.join(', '));
        }
        // Save processed data
        const processedDir = path.join(__dirname, '..', 'output', 'processed');
        if (!fs.existsSync(processedDir)) {
            fs.mkdirSync(processedDir, { recursive: true });
        }
        const processedFile = path.join(processedDir, `${playerId}.json`);
        fs.writeFileSync(processedFile, JSON.stringify(playerData, null, 2));
        console.log(`Processed data saved to: ${processedFile}`);
    }
    catch (error) {
        console.error('Error inspecting player:', error.message);
    }
}
// Get player ID from command line arguments
const playerId = process.argv[2] || '8478402'; // Default to Connor McDavid
inspectPlayer(playerId);
