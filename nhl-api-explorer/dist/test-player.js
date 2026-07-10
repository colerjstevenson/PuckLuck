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
function normalizePlayerData(playerData) {
    return {
        playerId: playerData.playerId,
        firstName: getLocalizedValue(playerData.firstName),
        lastName: getLocalizedValue(playerData.lastName),
        headshot: playerData.headshot || '',
        position: playerData.position || 'Unknown',
        birthCountry: playerData.birthCountry || '',
        birthDate: playerData.birthDate || '',
        draftDetails: playerData.draftDetails || {},
        sweaterNumber: playerData.sweaterNumber || 0,
        inHHOF: playerData.inHHOF || 0,
        awards: normalizeAwards(playerData.awards),
        careerTotals: playerData.careerTotals || {},
        seasonTotals: normalizeSeasonTotals(playerData.seasonTotals),
    };
}
async function testPlayer(playerId) {
    try {
        console.log(`Testing player with ID: ${playerId}`);
        // Create cache directory if it doesn't exist
        const cacheDir = path.join(__dirname, '..', 'cache', 'players');
        if (!fs.existsSync(cacheDir)) {
            fs.mkdirSync(cacheDir, { recursive: true });
        }
        // Check if we have cached data
        const cacheFile = path.join(cacheDir, `${playerId}.json`);
        if (fs.existsSync(cacheFile)) {
            console.log('Using cached data');
            const cachedData = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
            const normalizedData = normalizePlayerData(cachedData);
            // Display only the data we're keeping
            console.log('Name:', `${normalizedData.firstName} ${normalizedData.lastName}`);
            console.log('Position:', normalizedData.position);
            console.log('Birth Country:', normalizedData.birthCountry);
            console.log('Headshot:', normalizedData.headshot || 'N/A');
            // Extract draft data correctly
            const draftYear = normalizedData.draftDetails?.year || 'N/A';
            const draftRound = normalizedData.draftDetails?.round || 'N/A';
            const draftPick = normalizedData.draftDetails?.pickInRound || 'N/A';
            console.log('Draft:', `${draftYear} - Round ${draftRound}, Pick ${draftPick}`);
            // Extract additional data
            console.log('Jersey Number:', normalizedData.sweaterNumber || 'N/A');
            console.log('Hall of Fame:', normalizedData.inHHOF === 1 ? 'Yes' : 'No');
            // Extract awards information
            if (normalizedData.awards.length > 0) {
                console.log('Awards:');
                normalizedData.awards.forEach((award) => {
                    console.log(`- ${award}`);
                });
            }
            return;
        }
        // Fetch player landing data
        const landingUrl = `https://api-web.nhle.com/v1/player/${playerId}/landing`;
        console.log(`Fetching from: ${landingUrl}`);
        const response = await axios_1.default.get(landingUrl);
        const playerData = response.data;
        const normalizedData = normalizePlayerData(playerData);
        // Save to cache
        fs.writeFileSync(cacheFile, JSON.stringify(normalizedData, null, 2));
        console.log(`Data saved to cache: ${cacheFile}`);
        // Display only the data we're keeping
        console.log('Name:', `${normalizedData.firstName} ${normalizedData.lastName}`);
        console.log('Position:', normalizedData.position);
        console.log('Birth Country:', normalizedData.birthCountry);
        console.log('Headshot:', normalizedData.headshot || 'N/A');
        // Extract draft data correctly
        const draftYear = normalizedData.draftDetails?.year || 'N/A';
        const draftRound = normalizedData.draftDetails?.round || 'N/A';
        const draftPick = normalizedData.draftDetails?.pickInRound || 'N/A';
        console.log('Draft:', `${draftYear} - Round ${draftRound}, Pick ${draftPick}`);
        // Extract additional data
        console.log('Jersey Number:', normalizedData.sweaterNumber || 'N/A');
        console.log('Hall of Fame:', normalizedData.inHHOF === 1 ? 'Yes' : 'No');
        // Extract awards information
        if (normalizedData.awards.length > 0) {
            console.log('Awards:');
            normalizedData.awards.forEach((award) => {
                console.log(`- ${award}`);
            });
        }
        // Also show the full draft structure for debugging
        if (normalizedData.draftDetails) {
            console.log('Draft Details Structure:', JSON.stringify(normalizedData.draftDetails, null, 2));
        }
    }
    catch (error) {
        console.error('Error fetching player data:', error);
    }
}
// Get player ID from command line arguments
const playerId = process.argv[2] || '8478402'; // Default to Connor McDavid
testPlayer(playerId);
