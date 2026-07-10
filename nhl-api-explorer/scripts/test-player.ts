import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';

function getLocalizedValue(value: any): string {
  if (typeof value === 'string') {
    return value;
  }

  return value?.default || '';
}

function normalizeAwards(awards: any): string[] {
  if (!Array.isArray(awards)) {
    return [];
  }

  return awards
    .map((award: any) => {
      if (typeof award === 'string') {
        return award;
      }

      return award?.trophy?.default || 'Unknown Award';
    })
    .filter(Boolean);
}

function normalizeSeasonTotals(seasonTotals: any): any[] {
  if (!Array.isArray(seasonTotals)) {
    return [];
  }

  return seasonTotals.map((season: any) => ({
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

function normalizePlayerData(playerData: any) {
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

function printTeamsFromSeasonTotals(seasonTotals: any[]) {
  const nhlTeams = new Set<string>();

  seasonTotals.forEach((season: any) => {
    if (season.leagueAbbrev && season.leagueAbbrev !== 'NHL') {
      return;
    }

    const teamName = season.teamName || season.teamCommonName || season.teamAbbrev;
    if (teamName) {
      nhlTeams.add(teamName);
    }
  });

  if (nhlTeams.size === 0) {
    console.log('Teams (from season totals): none found');
    return;
  }

  console.log('Teams (from season totals):', Array.from(nhlTeams).join(', '));
}

async function testPlayer(playerId: string) {
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
        normalizedData.awards.forEach((award: any) => {
          console.log(`- ${award}`);
        });
      }

      printTeamsFromSeasonTotals(normalizedData.seasonTotals);
      
      return;
    }
    
    // Fetch player landing data
    const landingUrl = `https://api-web.nhle.com/v1/player/${playerId}/landing`;
    console.log(`Fetching from: ${landingUrl}`);
    
    const response = await axios.get(landingUrl);
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
      normalizedData.awards.forEach((award: any) => {
        console.log(`- ${award}`);
      });
    }

    printTeamsFromSeasonTotals(normalizedData.seasonTotals);
    
    // Also show the full draft structure for debugging
    if (normalizedData.draftDetails) {
      console.log('Draft Details Structure:', JSON.stringify(normalizedData.draftDetails, null, 2));
    }
    
  } catch (error) {
    console.error('Error fetching player data:', error);
  }
}

// Get player ID from command line arguments
const playerId = process.argv[2] || '8478402'; // Default to Connor McDavid
testPlayer(playerId);
