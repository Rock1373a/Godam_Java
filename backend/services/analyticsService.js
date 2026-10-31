const { promisify } = require('util');
const db = require('../db');

async function logEvent({
  eventName,
  eventCategory = 'onboarding',
  userId = null,
  sessionId = null,
  deviceId = null,
  platform = null,
  appVersion = null,
  eventData = null,
}) {
  const run = promisify(db.run.bind(db));
  await run(
    `INSERT INTO analytics_events 
     (event_name, event_category, user_id, session_id, device_id, platform, app_version, event_data_json, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`,
    [
      eventName,
      eventCategory,
      userId,
      sessionId,
      deviceId,
      platform,
      appVersion,
      eventData ? JSON.stringify(eventData) : null,
    ]
  );
}

async function getEventsBySession(sessionId, limit = 100) {
  const all = promisify(db.all.bind(db));
  return all(
    `SELECT * FROM analytics_events WHERE session_id = ? ORDER BY created_at DESC LIMIT ?`,
    [sessionId, limit]
  );
}

async function getEventsByDevice(deviceId, limit = 100) {
  const all = promisify(db.all.bind(db));
  return all(
    `SELECT * FROM analytics_events WHERE device_id = ? ORDER BY created_at DESC LIMIT ?`,
    [deviceId, limit]
  );
}

async function getOnboardingFunnelStats(startDate = null, endDate = null) {
  const all = promisify(db.all.bind(db));
  const dateFilter = startDate && endDate 
    ? `AND created_at BETWEEN ? AND ?` 
    : '';
  const params = startDate && endDate ? [startDate, endDate] : [];
  
  const events = await all(
    `SELECT event_name, COUNT(*) as count, COUNT(DISTINCT session_id) as unique_sessions
     FROM analytics_events 
     WHERE event_category = 'onboarding' ${dateFilter}
     GROUP BY event_name
     ORDER BY count DESC`,
    params
  );
  
  return events;
}

async function getDropOffAnalytics(startDate = null, endDate = null) {
  const all = promisify(db.all.bind(db));
  const dateFilter = startDate && endDate 
    ? `AND created_at BETWEEN ? AND ?` 
    : '';
  const params = startDate && endDate ? [startDate, endDate] : [];

  const appLaunchCount = await all(
    `SELECT COUNT(DISTINCT session_id) as count FROM analytics_events 
     WHERE event_name = 'app_launched' ${dateFilter}`,
    params
  );

  const configSavedCount = await all(
    `SELECT COUNT(DISTINCT session_id) as count FROM analytics_events 
     WHERE event_name = 'backend_url_configured' ${dateFilter}`,
    params
  );

  const loginViewCount = await all(
    `SELECT COUNT(DISTINCT session_id) as count FROM analytics_events 
     WHERE event_name = 'login_screen_viewed' ${dateFilter}`,
    params
  );

  const loginSuccessCount = await all(
    `SELECT COUNT(DISTINCT session_id) as count FROM analytics_events 
     WHERE event_name = 'login_success' ${dateFilter}`,
    params
  );

  const firstActionCount = await all(
    `SELECT COUNT(DISTINCT session_id) as count FROM analytics_events 
     WHERE event_name = 'first_action_success' ${dateFilter}`,
    params
  );

  return {
    appLaunched: appLaunchCount[0]?.count || 0,
    backendUrlConfigured: configSavedCount[0]?.count || 0,
    loginScreenViewed: loginViewCount[0]?.count || 0,
    loginSuccess: loginSuccessCount[0]?.count || 0,
    firstActionSuccess: firstActionCount[0]?.count || 0,
  };
}

module.exports = {
  logEvent,
  getEventsBySession,
  getEventsByDevice,
  getOnboardingFunnelStats,
  getDropOffAnalytics,
};
