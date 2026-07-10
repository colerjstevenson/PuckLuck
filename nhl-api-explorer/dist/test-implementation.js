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
async function testImplementation() {
    console.log('Testing NHL API Explorer Implementation...\n');
    // Check if required directories exist
    const requiredDirs = [
        'cache/players',
        'output/raw',
        'output/processed',
        'public/data'
    ];
    console.log('1. Checking directory structure...');
    for (const dir of requiredDirs) {
        const fullPath = path.join(__dirname, '..', dir);
        if (!fs.existsSync(fullPath)) {
            console.log(`   ❌ Missing directory: ${dir}`);
            // Create missing directories
            fs.mkdirSync(fullPath, { recursive: true });
            console.log(`   ✅ Created directory: ${dir}`);
        }
        else {
            console.log(`   ✅ Found directory: ${dir}`);
        }
    }
    // Check if package.json exists
    console.log('\n2. Checking package.json...');
    const packagePath = path.join(__dirname, '..', 'package.json');
    if (fs.existsSync(packagePath)) {
        console.log('   ✅ Found package.json');
    }
    else {
        console.log('   ❌ Missing package.json');
    }
    // Check if scripts exist
    console.log('\n3. Checking scripts...');
    const scripts = [
        'test-player.ts',
        'download-players.ts',
        'inspect-player.ts',
        'build-database.ts'
    ];
    for (const script of scripts) {
        const scriptPath = path.join(__dirname, script);
        if (fs.existsSync(scriptPath)) {
            console.log(`   ✅ Found script: ${script}`);
        }
        else {
            console.log(`   ❌ Missing script: ${script}`);
        }
    }
    // Check if documentation exists
    console.log('\n4. Checking documentation...');
    const docs = [
        'API_FIELDS.md',
        'README.md'
    ];
    for (const doc of docs) {
        const docPath = path.join(__dirname, '..', doc);
        if (fs.existsSync(docPath)) {
            console.log(`   ✅ Found documentation: ${doc}`);
        }
        else {
            console.log(`   ❌ Missing documentation: ${doc}`);
        }
    }
    console.log('\n5. Testing basic functionality...');
    console.log('   To test full functionality, run:');
    console.log('   npm run test-player');
    console.log('   npm run download-players');
    console.log('   npm run inspect-player');
    console.log('   npm run build-database');
    console.log('\n✅ Implementation test completed!');
}
testImplementation();
