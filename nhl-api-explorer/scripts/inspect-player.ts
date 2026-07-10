import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';

interface PlayerData {
  id: string;
  fullName: string;
  headshot: string;
  position: string;
  birthCountry: string;
  birthDate: string;
  draftYear: number;
  draftRound: number;
  draftPick: number;
  careerStats: any;
  teamsPlayedFor: string[];
  awards: string[];
  inHHOF: boolean;
  sweaterNumber: number;
  careerHighs: {
    goals: number;
    assists: number;
    points: number;
    plusMinus: number;
    pim: number;
    gamesPlayed: number;
    shots: number;
    shootingPctg: number;
    timeOnIce: string;
  };
  seasonHighs: {
    plusMinus: {
      seasonId: number;
      value: number;
    };
    shots: {
      seasonId: number;
      value: number;
    };
    timeOnIce: {
      seasonId: number;
      value: string;
    };
  };
  seasons: any[];
}

function parseToiToSeconds(avgToi: string): number {
  if (!avgToi || typeof avgToi !== 'string' || !avgToi.includes(':')) {
    return 0;
  }

  const [minutes, seconds] = avgToi.split(':').map((value) => parseInt(value, 10));
  if (!Number.isFinite(minutes) || !Number.isFinite(seconds)) {
    return 0;
  }

  return (minutes * 60) + seconds;
}

async function inspectPlayer(playerId: string) {
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
    
    const response = await axios.get(landingUrl);
    const rawData = response.data;
    
    // Save raw data
    const outputFile = path.join(outputDir, `${playerId}.json`);
    fs.writeFileSync(outputFile, JSON.stringify(rawData, null, 2));
    console.log(`Raw data saved to: ${outputFile}`);
    
    // Extract awards information
    const awards: string[] = [];
    if (rawData.awards && Array.isArray(rawData.awards)) {
      rawData.awards.forEach((award: any) => {
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
    
    const seasons: any[] = [];
    const seasonHighs = {
      plusMinus: {
        seasonId: 0,
        value: 0,
      },
      shots: {
        seasonId: 0,
        value: 0,
      },
      timeOnIce: {
        seasonId: 0,
        value: '',
      },
    };
    let topToiSeconds = 0;
    
    if (rawData.seasonTotals && Array.isArray(rawData.seasonTotals)) {
      rawData.seasonTotals.forEach((season: any) => {
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
          if (season.goals > careerHighs.goals) careerHighs.goals = season.goals;
          if (season.assists > careerHighs.assists) careerHighs.assists = season.assists;
          if (season.points > careerHighs.points) careerHighs.points = season.points;
          if (season.plusMinus > careerHighs.plusMinus) careerHighs.plusMinus = season.plusMinus;
          if (season.pim > careerHighs.pim) careerHighs.pim = season.pim;
          if (season.gamesPlayed > careerHighs.gamesPlayed) careerHighs.gamesPlayed = season.gamesPlayed;
          if (season.shots > careerHighs.shots) careerHighs.shots = season.shots;
          if (season.shootingPctg > careerHighs.shootingPctg) careerHighs.shootingPctg = season.shootingPctg;

          if ((season.plusMinus || 0) > seasonHighs.plusMinus.value) {
            seasonHighs.plusMinus.value = season.plusMinus || 0;
            seasonHighs.plusMinus.seasonId = season.season || 0;
          }

          if ((season.shots || 0) > seasonHighs.shots.value) {
            seasonHighs.shots.value = season.shots || 0;
            seasonHighs.shots.seasonId = season.season || 0;
          }

          const seasonToiSeconds = parseToiToSeconds(season.avgToi || '');
          if (seasonToiSeconds > topToiSeconds) {
            topToiSeconds = seasonToiSeconds;
            seasonHighs.timeOnIce.value = season.avgToi || '';
            seasonHighs.timeOnIce.seasonId = season.season || 0;
          }
        }
      });
    }

    careerHighs.timeOnIce = seasonHighs.timeOnIce.value;
    
    // Process data into our model
    const playerData: PlayerData = {
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
      seasonHighs,
      seasons
    };
    
    // Extract teams played for
    if (rawData.seasonTotals) {
      const teams = new Set<string>();
      rawData.seasonTotals.forEach((season: any) => {
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
      console.log(`Plus/Minus: ${playerData.careerHighs.plusMinus}`);
      console.log(`Shots: ${playerData.careerHighs.shots}`);
      console.log(`TOI: ${playerData.careerHighs.timeOnIce || 'N/A'}`);
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
    
  } catch (error: any) {
    console.error('Error inspecting player:', error.message);
  }
}

// Get player ID from command line arguments
const playerId = process.argv[2] || '8478402'; // Default to Connor McDavid
inspectPlayer(playerId);
