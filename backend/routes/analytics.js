const express = require('express');
const { logEvent, getOnboardingFunnelStats, getDropOffAnalytics } = require('../services/analyticsService');
const { requireAuth } = require('../middleware/auth');

const router = express.Router();

router.post('/events', async (req, res) => {
  try {
    const {
      eventName,
      eventCategory,
      sessionId,
      deviceId,
      platform,
      appVersion,
      eventData,
    } = req.body || {};

    if (!eventName) {
      return res.status(400).json({ error: 'eventName is required' });
    }

    const userId = req.user?.sub || null;

    await logEvent({
      eventName,
      eventCategory: eventCategory || 'onboarding',
      userId,
      sessionId,
      deviceId,
      platform,
      appVersion,
      eventData,
    });

    return res.json({ ok: true });
  } catch (e) {
    console.error('Analytics event error:', e);
    return res.status(500).json({ error: e.message });
  }
});

router.get('/onboarding/funnel', requireAuth, async (req, res) => {
  try {
    const { startDate, endDate } = req.query;
    const stats = await getOnboardingFunnelStats(startDate, endDate);
    return res.json(stats);
  } catch (e) {
    console.error('Funnel stats error:', e);
    return res.status(500).json({ error: e.message });
  }
});

router.get('/onboarding/dropoff', requireAuth, async (req, res) => {
  try {
    const { startDate, endDate } = req.query;
    const stats = await getDropOffAnalytics(startDate, endDate);
    return res.json(stats);
  } catch (e) {
    console.error('Drop-off stats error:', e);
    return res.status(500).json({ error: e.message });
  }
});

module.exports = router;
