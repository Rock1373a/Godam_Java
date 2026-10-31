#!/usr/bin/env node
/**
 * Wipe every row in every SQLite table, then ensure exactly one admin user (password from CLI or env).
 *
 * Usage (from backend/):
 *   node scripts/wipe-and-reset-admin.js --yes --password 'YOUR_SECRET'
 *   ADMIN_PASSWORD='YOUR_SECRET' node scripts/wipe-and-reset-admin.js --yes
 *
 * Env: ADMIN_USERNAME (default admin), DB_PATH (default ../warehouse.db relative to backend/)
 *
 * Stop the API first if you see SQLITE_BUSY / database is locked.
 */
const path = require('path');
const { execSync } = require('child_process');

require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

function parseArgs() {
  let yes = false;
  let password = String(process.env.ADMIN_PASSWORD || '').trim();
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--yes') yes = true;
    else if (argv[i] === '--password' && argv[i + 1]) {
      password = String(argv[++i]).trim();
    }
  }
  return { yes, password };
}

const { yes, password } = parseArgs();
if (!yes) {
  console.log('Wipes ALL data from the SQLite DB, then creates/updates the admin user.');
  console.log('Requires --yes and a password (--password … or ADMIN_PASSWORD).');
  console.log('');
  console.log('  cd backend && node scripts/wipe-and-reset-admin.js --yes --password \'…\'');
  process.exit(0);
}

if (!password) {
  console.error('Missing password. Use: --password \'…\' or set ADMIN_PASSWORD in the environment.');
  process.exit(1);
}

const backendDir = path.join(__dirname, '..');
const node = process.execPath;
const wipe = path.join(__dirname, 'wipe-all-data.js');
const ensure = path.join(__dirname, 'ensure-admin.js');

const env = {
  ...process.env,
  ADMIN_PASSWORD: password,
};

console.log('Step 1/2: wiping all tables (including all users)…');
execSync(`${JSON.stringify(node)} ${JSON.stringify(wipe)} --yes`, {
  cwd: backendDir,
  env: { ...process.env },
  stdio: 'inherit',
});

console.log('Step 2/2: creating/updating admin user…');
execSync(`${JSON.stringify(node)} ${JSON.stringify(ensure)}`, {
  cwd: backendDir,
  env,
  stdio: 'inherit',
});

console.log('Done. Log in with ADMIN_USERNAME / the password you supplied.');
