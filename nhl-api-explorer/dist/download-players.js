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
function getLocalizedValue(value) {
    if (typeof value === 'string') {
        return value;
    }
    return value?.default || '';
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
function extractTeamsPlayedFor(seasonTotals) {
    const teams = new Set();
    for (const season of seasonTotals) {
        const teamName = season.teamName || season.teamCommonName || season.teamAbbrev;
        if (!teamName) {
            continue;
        }
        // Keep only NHL teams from season history.
        if (season.leagueAbbrev && season.leagueAbbrev !== 'NHL') {
            continue;
        }
        teams.add(teamName);
    }
    return Array.from(teams);
}
function normalizePlayerRecord(playerId, playerSummary, landingData) {
    const summaryFirstName = getLocalizedValue(playerSummary.skaterFullName?.split(' ')[0]);
    const summaryLastName = getLocalizedValue(playerSummary.skaterFullName?.split(' ').slice(1).join(' '));
    const seasonTotals = normalizeSeasonTotals(landingData.seasonTotals);
    return {
        playerId,
        firstName: getLocalizedValue(landingData.firstName) || summaryFirstName || 'Unknown',
        lastName: getLocalizedValue(landingData.lastName) || summaryLastName || 'Unknown',
        headshot: landingData.headshot || '',
        position: landingData.position || playerSummary.positionCode || 'Unknown',
        birthCountry: landingData.birthCountry || '',
        birthDate: landingData.birthDate || '',
        draftDetails: landingData.draftDetails || {},
        sweaterNumber: landingData.sweaterNumber || 0,
        inHHOF: landingData.inHHOF || 0,
        awards: normalizeAwards(landingData.awards),
        careerTotals: landingData.careerTotals || {},
        seasonTotals,
        teamsPlayedFor: extractTeamsPlayedFor(seasonTotals),
    };
}
function readCachedPlayerRecord(cacheFile) {
    const cachedData = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
    const normalizedSeasonTotals = normalizeSeasonTotals(cachedData.seasonTotals);
    if (typeof cachedData.firstName === 'string' && typeof cachedData.lastName === 'string') {
        const teamsPlayedFor = Array.isArray(cachedData.teamsPlayedFor)
            ? cachedData.teamsPlayedFor.filter((team) => typeof team === 'string' && Boolean(team))
            : extractTeamsPlayedFor(normalizedSeasonTotals);
        return {
            ...cachedData,
            seasonTotals: normalizedSeasonTotals,
            teamsPlayedFor,
        };
    }
    return {
        playerId: cachedData.playerId,
        firstName: getLocalizedValue(cachedData.firstName),
        lastName: getLocalizedValue(cachedData.lastName),
        headshot: cachedData.headshot || '',
        position: cachedData.position || 'Unknown',
        birthCountry: cachedData.birthCountry || '',
        birthDate: cachedData.birthDate || '',
        draftDetails: cachedData.draftDetails || {},
        sweaterNumber: cachedData.sweaterNumber || 0,
        inHHOF: cachedData.inHHOF || 0,
        awards: normalizeAwards(cachedData.awards),
        careerTotals: cachedData.careerTotals || {},
        seasonTotals: normalizedSeasonTotals,
        teamsPlayedFor: extractTeamsPlayedFor(normalizedSeasonTotals),
    };
}
function getCurrentSeasonStartYear() {
    const now = new Date();
    return now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
}
function buildSeasonIds(startYear = 1917, endYear = getCurrentSeasonStartYear()) {
    const seasonIds = [];
    for (let year = startYear; year <= endYear; year++) {
        seasonIds.push(`${year}${year + 1}`);
    }
    return seasonIds;
}
async function fetchSeasonPlayerSummaries(seasonId) {
    const headers = { 'User-Agent': 'NHL-API-Explorer/1.0' };
    const skatersUrl = `https://api.nhle.com/stats/rest/en/skater/summary?limit=-1&cayenneExp=seasonId=${seasonId}`;
    const goaliesUrl = `https://api.nhle.com/stats/rest/en/goalie/summary?limit=-1&cayenneExp=seasonId=${seasonId}`;
    const [skatersResponse, goaliesResponse] = await Promise.all([
        axios_1.default.get(skatersUrl, { timeout: 30000, headers }),
        axios_1.default.get(goaliesUrl, { timeout: 30000, headers }),
    ]);
    const skatersData = skatersResponse.data?.data ?? [];
    const goaliesData = goaliesResponse.data?.data ?? [];
    const normalizedGoalies = goaliesData.map((g) => ({
        ...g,
        skaterFullName: g.goalieFullName,
        positionCode: 'G',
    }));
    return [...skatersData, ...normalizedGoalies];
}
async function downloadAllPlayers() {
    try {
        console.log('Downloading all NHL players...');
        // Create output directory if it doesn't exist
        const outputDir = path.join(__dirname, '..', 'output', 'raw');
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }
        const cacheDir = path.join(__dirname, '..', 'cache', 'players');
        if (!fs.existsSync(cacheDir)) {
            fs.mkdirSync(cacheDir, { recursive: true });
        }
        // Build an all-time player index from seasonal summary data.
        const seasonIds = buildSeasonIds();
        const playersById = new Map();
        let seasonRecordCount = 0;
        console.log(`Fetching player lists across ${seasonIds.length} seasons...`);
        for (const seasonId of seasonIds) {
            try {
                const seasonPlayers = await fetchSeasonPlayerSummaries(seasonId);
                seasonRecordCount += seasonPlayers.length;
                for (const player of seasonPlayers) {
                    if (player.playerId) {
                        playersById.set(player.playerId, player);
                    }
                }
                console.log(`Collected ${seasonPlayers.length} player records for season ${seasonId}`);
            }
            catch (error) {
                console.error(`Error fetching player summaries for season ${seasonId}:`, error.message);
            }
        }
        const allPlayers = Array.from(playersById.values());
        if (allPlayers.length > 0) {
            console.log(`Found ${allPlayers.length} unique players from ${seasonIds.length} seasons (${seasonRecordCount} season records total)`);
            // Save the stats data
            const statsFile = path.join(outputDir, 'all-players-stats.json');
            fs.writeFileSync(statsFile, JSON.stringify({ data: allPlayers }, null, 2));
            console.log(`Stats data saved to: ${statsFile}`);
            let processedCount = 0;
            let errorCount = 0;
            let nextIndex = 0;
            const concurrencyLimit = 8;
            const workerCount = Math.min(concurrencyLimit, allPlayers.length);
            const playersByIndex = new Array(allPlayers.length);
            console.log(`Starting to process ${allPlayers.length} players...`);
            async function processPlayer(index) {
                const player = allPlayers[index];
                try {
                    const playerId = player.playerId;
                    if (!playerId) {
                        console.log(`Skipping player with no ID at index ${index}`);
                        return;
                    }
                    const cacheFile = path.join(cacheDir, `${playerId}.json`);
                    if (fs.existsSync(cacheFile)) {
                        const cachedPlayer = readCachedPlayerRecord(cacheFile);
                        const teamsPlayedFor = cachedPlayer.teamsPlayedFor.length > 0
                            ? cachedPlayer.teamsPlayedFor
                            : [player.teamAbbrevs?.split(',')[0] || 'Unknown'].filter((team) => team !== 'Unknown');
                        playersByIndex[index] = {
                            playerId: cachedPlayer.playerId,
                            firstName: cachedPlayer.firstName,
                            lastName: cachedPlayer.lastName,
                            headshot: cachedPlayer.headshot,
                            positionCode: cachedPlayer.position,
                            currentTeam: player.teamAbbrevs?.split(',')[0] || 'Unknown',
                            teamsPlayedFor,
                            birthCountry: cachedPlayer.birthCountry,
                            birthDate: cachedPlayer.birthDate,
                            draftDetails: cachedPlayer.draftDetails,
                            sweaterNumber: cachedPlayer.sweaterNumber,
                            inHHOF: cachedPlayer.inHHOF,
                        };
                        processedCount++;
                        console.log(`[${index + 1}/${allPlayers.length}] Reused cached player ${playerId} (${cachedPlayer.firstName} ${cachedPlayer.lastName})`);
                        return;
                    }
                    const landingUrl = `https://api-web.nhle.com/v1/player/${playerId}/landing`;
                    console.log(`[${index + 1}/${allPlayers.length}] Fetching landing data for player ${playerId} (${player.skaterFullName})`);
                    const landingResponse = await axios_1.default.get(landingUrl, {
                        timeout: 10000,
                        headers: {
                            'User-Agent': 'NHL-API-Explorer/1.0'
                        }
                    });
                    if (landingResponse.status === 200 && landingResponse.data) {
                        const cachedPlayer = normalizePlayerRecord(playerId, player, landingResponse.data);
                        playersByIndex[index] = {
                            playerId: cachedPlayer.playerId,
                            firstName: cachedPlayer.firstName,
                            lastName: cachedPlayer.lastName,
                            headshot: cachedPlayer.headshot,
                            positionCode: cachedPlayer.position,
                            currentTeam: player.teamAbbrevs?.split(',')[0] || 'Unknown',
                            teamsPlayedFor: cachedPlayer.teamsPlayedFor,
                            birthCountry: cachedPlayer.birthCountry,
                            birthDate: cachedPlayer.birthDate,
                            draftDetails: cachedPlayer.draftDetails,
                            sweaterNumber: cachedPlayer.sweaterNumber,
                            inHHOF: cachedPlayer.inHHOF,
                        };
                        fs.writeFileSync(cacheFile, JSON.stringify(cachedPlayer, null, 2));
                        processedCount++;
                        console.log(`Successfully processed player ${playerId} (${processedCount} completed)`);
                    }
                    else {
                        console.log(`Failed to fetch data for player ${playerId}: Status ${landingResponse.status}`);
                        errorCount++;
                    }
                }
                catch (error) {
                    console.error(`Error fetching data for player ${player.playerId || 'unknown'}:`, error.message);
                    errorCount++;
                }
            }
            await Promise.all(Array.from({ length: workerCount }, async () => {
                while (true) {
                    const index = nextIndex++;
                    if (index >= allPlayers.length) {
                        break;
                    }
                    await processPlayer(index);
                }
            }));
            const processedPlayers = playersByIndex.filter((player) => Boolean(player));
            // Save our compiled player data
            const outputFile = path.join(outputDir, 'all-players.json');
            fs.writeFileSync(outputFile, JSON.stringify({ data: processedPlayers }, null, 2));
            console.log(`Compiled player data saved to: ${outputFile}`);
            console.log(`Successfully processed ${processedPlayers.length} players with ${errorCount} errors`);
            // Display summary
            console.log('\n--- SUMMARY ---');
            console.log(`Total players processed: ${processedPlayers.length}`);
            console.log(`Errors encountered: ${errorCount}`);
            // Count by position
            const positionCounts = {};
            processedPlayers.forEach((player) => {
                const position = player.positionCode || 'Unknown';
                positionCounts[position] = (positionCounts[position] || 0) + 1;
            });
            console.log('\n--- POSITION COUNTS ---');
            Object.entries(positionCounts).forEach(([position, count]) => {
                console.log(`${position}: ${count}`);
            });
            return;
        }
        else {
            console.log('No players found from historical season summaries');
        }
    }
    catch (error) {
        console.error('Error downloading players:', error.message);
        if (error.response) {
            console.error('Response status:', error.response.status);
            console.error('Response data:', JSON.stringify(error.response.data, null, 2));
        }
        console.error('Full error:', error);
    }
}
downloadAllPlayers();
