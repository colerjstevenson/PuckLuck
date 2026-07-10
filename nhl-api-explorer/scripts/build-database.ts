import * as fs from 'fs';
import * as path from 'path';
import { randomUUID } from 'crypto';
import initSqlJs, { Database as SqlJsDatabase, SqlJsStatic } from 'sql.js';

const DB_SCHEMA_VERSION = '1';

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
    avgToi: season.avgToi || '',
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

interface Player {
  id: string;
  name: string;
  headshot: string;
  position: string;
  positionGroup: string;
  heightInInches: number;
  weightInPounds: number;
  birthCountry: string;
  birthDate: string;
  teamsPlayedFor: string[];
  rookieSeason: string;
  lastSeason: string;
  draftYear: string;
  draftRound: string;
  draftPick: string;
  active: boolean;
  careerStats: any;
  awards: string[];
  inHHOF: boolean;
  cups: number;
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
      season: string;
      value: number;
    };
    shots: {
      season: string;
      value: number;
    };
    timeOnIce: {
      season: string;
      value: string;
    };
  };
}

interface CanonicalDatabase {
  db: SqlJsDatabase;
  upsertPlayer: (payload: {
    playerId: string;
    name: string;
    position: string;
    lastSeason: string;
    updatedAt: string;
    rawJson: string;
    compactJson: string;
  }) => void;
  setMeta: (key: string, value: string) => void;
}

interface ErrorSummary {
  missingCache: number;
  processingError: number;
}

function parseToiToSeconds(avgToi: string): number {
  if (typeof avgToi !== 'string' || !avgToi.includes(':')) {
    return 0;
  }

  const [minutes, seconds] = avgToi.split(':').map((value) => parseInt(value, 10));
  if (!Number.isFinite(minutes) || !Number.isFinite(seconds)) {
    return 0;
  }

  return (minutes * 60) + seconds;
}

function getPositionGroup(position: string): string {
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

function determineActive(lastSeason: string): boolean {
  const currentYear = new Date().getFullYear();
  const lastSeasonYear = parseInt(lastSeason || '0', 10);
  return lastSeasonYear >= currentYear - 1;
}

function ensureDirectory(dir: string): void {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function createCanonicalDatabase(sql: SqlJsStatic): CanonicalDatabase {
  const db = new sql.Database();
  db.run(`
    CREATE TABLE IF NOT EXISTS players_raw (
      player_id TEXT PRIMARY KEY,
      name TEXT,
      position TEXT,
      last_season TEXT,
      updated_at TEXT NOT NULL,
      raw_json TEXT NOT NULL,
      compact_json TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_players_raw_position ON players_raw(position);
    CREATE INDEX IF NOT EXISTS idx_players_raw_last_season ON players_raw(last_season);

    CREATE TABLE IF NOT EXISTS pipeline_meta (
      meta_key TEXT PRIMARY KEY,
      meta_value TEXT NOT NULL
    );
  `);

  const upsertPlayer = (payload: {
    playerId: string;
    name: string;
    position: string;
    lastSeason: string;
    updatedAt: string;
    rawJson: string;
    compactJson: string;
  }) => {
    db.run(
      `
      INSERT INTO players_raw (
        player_id,
        name,
        position,
        last_season,
        updated_at,
        raw_json,
        compact_json
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(player_id) DO UPDATE SET
        name = excluded.name,
        position = excluded.position,
        last_season = excluded.last_season,
        updated_at = excluded.updated_at,
        raw_json = excluded.raw_json,
        compact_json = excluded.compact_json;
      `,
      [
        payload.playerId,
        payload.name,
        payload.position,
        payload.lastSeason,
        payload.updatedAt,
        payload.rawJson,
        payload.compactJson,
      ]
    );
  };

  const setMeta = (key: string, value: string) => {
    db.run(
      `
      INSERT INTO pipeline_meta (meta_key, meta_value)
      VALUES (?, ?)
      ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value;
      `,
      [key, value]
    );
  };

  return { db, upsertPlayer, setMeta };
}

function queryCount(db: SqlJsDatabase, query: string): number {
  const result = db.exec(query);
  if (!result.length || !result[0].values.length) {
    return 0;
  }

  const value = result[0].values[0][0];
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

async function buildDatabase() {
  let canonicalDb: SqlJsDatabase | null = null;

  try {
    console.log('Building player database...');

    const backendDataDir = path.join(__dirname, '..', '..', 'backend', 'data');
    const compactDataFile = path.join(backendDataDir, 'players_compact.json');
    const rawDbFile = path.join(backendDataDir, 'players_raw.db');
    const pipelineRunId = randomUUID();
    const startedAt = new Date().toISOString();
    const sql = await initSqlJs();
    const canonical = createCanonicalDatabase(sql);
    canonicalDb = canonical.db;
    canonical.setMeta('schema_version', DB_SCHEMA_VERSION);
    canonical.setMeta('build_started_at', startedAt);
    canonical.setMeta('run_id', pipelineRunId);
    
    // Read trophies data
    const trophiesPath = path.join(__dirname, '..', 'cache', 'trophies', 'trophies.json');
    let trophiesData: Record<string, any> = {};
    if (fs.existsSync(trophiesPath)) {
      trophiesData = JSON.parse(fs.readFileSync(trophiesPath, 'utf8'));
      console.log('Loaded trophies data');
    } else {
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
    
    const processedPlayers: Player[] = [];
    const errors: string[] = [];
    const errorSummary: ErrorSummary = {
      missingCache: 0,
      processingError: 0,
    };
    let skippedPlayers = 0;
    
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
          skippedPlayers += 1;
          errorSummary.missingCache += 1;
          continue;
        }
        
        const landingData = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
        const seasonTotals = normalizeSeasonTotals(landingData.seasonTotals);
        const awards = normalizeAwards(landingData.awards);
        const firstName = getLocalizedValue(landingData.firstName) || 'Unknown';
        const lastName = getLocalizedValue(landingData.lastName) || 'Unknown';
        const position = landingData.position || 'Unknown';
        
        // Extract teams played for
        const teams = new Set<string>();
        if (seasonTotals) {
          seasonTotals.forEach((season: any) => {
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
            .filter((s: any) => s.gameTypeId === 2) // Regular season
            .map((s: any) => parseInt(s.season, 10))
            .sort((a: number, b: number) => a - b);
          
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
          Object.values(trophyData).forEach((winners: any) => {
            if (Array.isArray(winners)) {
              const playerWonTrophy = winners.some((winner: any) => winner.id.toString() === playerIdStr);
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
          shootingPctg: 0,
          timeOnIce: ''
        };
        const seasonHighs = {
          plusMinus: {
            season: '',
            value: 0,
          },
          shots: {
            season: '',
            value: 0,
          },
          timeOnIce: {
            season: '',
            value: '',
          },
        };
        let topToiSeconds = 0;
        
        if (seasonTotals && Array.isArray(seasonTotals)) {
          seasonTotals.forEach((season: any) => {
            // Only process NHL regular seasons
            if (season.leagueAbbrev === 'NHL' && season.gameTypeId === 2) {
              // Update career highs
              if (season.goals > careerHighs.goals) careerHighs.goals = season.goals || 0;
              if (season.assists > careerHighs.assists) careerHighs.assists = season.assists || 0;
              if (season.points > careerHighs.points) careerHighs.points = season.points || 0;
              if (season.plusMinus > careerHighs.plusMinus) careerHighs.plusMinus = season.plusMinus || 0;
              if (season.pim > careerHighs.pim) careerHighs.pim = season.pim || 0;
              if (season.gamesPlayed > careerHighs.gamesPlayed) careerHighs.gamesPlayed = season.gamesPlayed || 0;
              if (season.shots > careerHighs.shots) careerHighs.shots = season.shots || 0;
              if (season.shootingPctg > careerHighs.shootingPctg) careerHighs.shootingPctg = season.shootingPctg || 0;

              if ((season.plusMinus || 0) > seasonHighs.plusMinus.value) {
                seasonHighs.plusMinus.value = season.plusMinus || 0;
                seasonHighs.plusMinus.season = String(season.season || '');
              }

              if ((season.shots || 0) > seasonHighs.shots.value) {
                seasonHighs.shots.value = season.shots || 0;
                seasonHighs.shots.season = String(season.season || '');
              }

              const seasonToiSeconds = parseToiToSeconds(season.avgToi || '');
              if (seasonToiSeconds > topToiSeconds) {
                topToiSeconds = seasonToiSeconds;
                seasonHighs.timeOnIce.value = season.avgToi || '';
                seasonHighs.timeOnIce.season = String(season.season || '');
              }
            }
          });
        }

        careerHighs.timeOnIce = seasonHighs.timeOnIce.value;
        
        const processedPlayer: Player = {
          id: playerId.toString(),
          name: `${firstName} ${lastName}`,
          headshot: landingData.headshot || player.headshot || '',
          position,
          positionGroup: getPositionGroup(position),
          heightInInches: Number(landingData.heightInInches) || 0,
          weightInPounds: Number(landingData.weightInPounds) || 0,
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
          cups: 0, // Would need additional data sources
          sweaterNumber: landingData.sweaterNumber || 0,
          careerHighs,
          seasonHighs
        };
        
        processedPlayers.push(processedPlayer);
        canonical.upsertPlayer({
          playerId: processedPlayer.id,
          name: processedPlayer.name,
          position: processedPlayer.position,
          lastSeason: processedPlayer.lastSeason,
          updatedAt: new Date().toISOString(),
          rawJson: JSON.stringify(landingData),
          compactJson: JSON.stringify(processedPlayer),
        });
        
        if (i % 1000 === 0 && i > 0) {
          console.log(`Processed ${i} players...`);
        }
      } catch (error: any) {
        errors.push(`Error processing player ${playerId}: ${error.message}`);
        errorSummary.processingError += 1;
      }
    }

    ensureDirectory(backendDataDir);
    fs.writeFileSync(compactDataFile, JSON.stringify(processedPlayers, null, 2));
    console.log(`Compact data saved to: ${compactDataFile}`);

    // Keep legacy explorer output for inspection/debug.
    const publicDir = path.join(__dirname, '..', 'public', 'data');
    ensureDirectory(publicDir);

    const databaseFile = path.join(publicDir, 'players.json');
    fs.writeFileSync(databaseFile, JSON.stringify(processedPlayers, null, 2));
    console.log(`Explorer debug copy saved to: ${databaseFile}`);
    console.log(`Total players processed: ${processedPlayers.length}`);

    const dbRowCount = queryCount(canonicalDb, 'SELECT COUNT(*) FROM players_raw');
    const compactRowCount = processedPlayers.length;

    if (dbRowCount !== compactRowCount) {
      throw new Error(`Parity check failed: DB rows (${dbRowCount}) do not match compact rows (${compactRowCount})`);
    }

    canonical.setMeta('build_finished_at', new Date().toISOString());
    canonical.setMeta('input_total', String(allPlayersData.data.length));
    canonical.setMeta('processed_total', String(processedPlayers.length));
    canonical.setMeta('db_row_total', String(dbRowCount));
    canonical.setMeta('compact_row_total', String(compactRowCount));
    canonical.setMeta('skipped_total', String(skippedPlayers));
    canonical.setMeta('error_total', String(errors.length));
    canonical.setMeta('error_missing_cache', String(errorSummary.missingCache));
    canonical.setMeta('error_processing', String(errorSummary.processingError));

    ensureDirectory(path.dirname(rawDbFile));
    fs.writeFileSync(rawDbFile, Buffer.from(canonicalDb.export()));

    console.log(`Raw canonical DB saved to: ${rawDbFile}`);
    console.log(`DB rows written: ${dbRowCount}`);
    console.log(`Compact rows written: ${compactRowCount}`);
    console.log(`Skipped players (no cache): ${skippedPlayers}`);
    
    if (errors.length > 0) {
      console.log(`Errors encountered: ${errors.length}`);
      const errorsFile = path.join(__dirname, '..', 'output', 'errors.txt');
      fs.writeFileSync(errorsFile, errors.join('\n'));
      console.log(`Errors saved to: ${errorsFile}`);
    }
    
    // Display summary statistics
    console.log('\n--- DATABASE SUMMARY ---');
    console.log(`Run ID: ${pipelineRunId}`);
    console.log(`Input players: ${allPlayersData.data.length}`);
    console.log(`Total players: ${processedPlayers.length}`);
    console.log(`DB parity: PASS (${dbRowCount} == ${compactRowCount})`);
    console.log('\n--- ERROR CATEGORIES ---');
    console.log(`Missing cache: ${errorSummary.missingCache}`);
    console.log(`Processing errors: ${errorSummary.processingError}`);
    
    const positionGroups = processedPlayers.reduce((acc: Record<string, number>, player) => {
      acc[player.positionGroup] = (acc[player.positionGroup] || 0) + 1;
      return acc;
    }, {});
    
    console.log('\n--- POSITION GROUPS ---');
    Object.entries(positionGroups).forEach(([group, count]) => {
      console.log(`${group}: ${count}`);
    });
    
    const countries = processedPlayers.reduce((acc: Record<string, number>, player) => {
      acc[player.birthCountry] = (acc[player.birthCountry] || 0) + 1;
      return acc;
    }, {});
    
    const topCountries = Object.entries(countries)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5);
    
    console.log('\n--- TOP COUNTRIES ---');
    topCountries.forEach(([country, count]) => {
      console.log(`${country}: ${count}`);
    });
    
    // Show Hall of Fame statistics
    const hhofCount = processedPlayers.filter(player => player.inHHOF).length;
    console.log(`\n--- HALL OF FAME ---`);
    console.log(`Players in HHOF: ${hhofCount}`);
    
  } catch (error: any) {
    console.error('Error building database:', error.message);
    process.exitCode = 1;
  } finally {
    if (canonicalDb) {
      canonicalDb.close();
    }
  }
}

buildDatabase();
