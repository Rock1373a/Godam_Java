const express = require('express');
const { promisify } = require('util');
const crypto = require('crypto');

const db = require('../db');
const { requireAuth, requireWebAccess } = require('../middleware/auth');

const router = express.Router();
const dbAll = promisify(db.all.bind(db));
const dbGet = promisify(db.get.bind(db));
const dbRun = promisify(db.run.bind(db));

function generateReferralCode(customerNumber, companyName) {
  const prefix = (companyName || customerNumber || 'REF')
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, 4);
  const suffix = crypto.randomBytes(3).toString('hex').toUpperCase();
  return `${prefix}-${suffix}`;
}

router.get('/code/:customer_id', async (req, res) => {
  try {
    const customerId = Number(req.params.customer_id);
    if (!customerId) return res.status(400).json({ error: 'customer_id required' });

    let customer = await dbGet(
      `SELECT id, customer_number, company_name, referral_code FROM customers WHERE id = ?`,
      [customerId]
    );
    if (!customer) return res.status(404).json({ error: 'Customer not found' });

    if (!customer.referral_code) {
      const newCode = generateReferralCode(customer.customer_number, customer.company_name);
      await dbRun(`UPDATE customers SET referral_code = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`, [
        newCode,
        customerId,
      ]);
      customer = await dbGet(`SELECT id, customer_number, company_name, referral_code FROM customers WHERE id = ?`, [
        customerId,
      ]);
    }

    res.json({
      customer_id: customer.id,
      customer_number: customer.customer_number,
      company_name: customer.company_name,
      referral_code: customer.referral_code,
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

router.post('/apply', async (req, res) => {
  try {
    const { referral_code, new_customer_id } = req.body || {};
    if (!referral_code || !new_customer_id) {
      return res.status(400).json({ error: 'referral_code and new_customer_id are required' });
    }

    const newCustomer = await dbGet(`SELECT id, referral_code, referred_by_customer_id FROM customers WHERE id = ?`, [
      new_customer_id,
    ]);
    if (!newCustomer) return res.status(404).json({ error: 'New customer not found' });

    if (newCustomer.referred_by_customer_id) {
      return res.status(400).json({ error: 'Customer already has a referrer' });
    }

    const referrer = await dbGet(
      `SELECT id, customer_number, company_name, referral_code FROM customers WHERE referral_code = ?`,
      [referral_code]
    );
    if (!referrer) return res.status(404).json({ error: 'Invalid referral code' });

    if (referrer.id === new_customer_id) {
      return res.status(400).json({ error: 'Cannot refer yourself' });
    }

    await dbRun(
      `INSERT INTO customer_referrals (referrer_customer_id, referred_customer_id, referral_code_used, status, created_at)
       VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)`,
      [referrer.id, new_customer_id, referral_code]
    );

    await dbRun(`UPDATE customers SET referred_by_customer_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`, [
      referrer.id,
      new_customer_id,
    ]);

    res.status(201).json({
      success: true,
      referral: {
        referrer_id: referrer.id,
        referrer_name: referrer.company_name,
        referred_customer_id: new_customer_id,
        referral_code_used: referral_code,
        status: 'pending',
      },
    });
  } catch (e) {
    if (String(e.message).includes('UNIQUE')) {
      return res.status(400).json({ error: 'Customer already referred' });
    }
    res.status(500).json({ error: e.message });
  }
});

router.get('/status/:customer_id', async (req, res) => {
  try {
    const customerId = Number(req.params.customer_id);
    if (!customerId) return res.status(400).json({ error: 'customer_id required' });

    const referralsMade = await dbAll(
      `SELECT cr.*, c.company_name as referred_company_name, c.customer_number as referred_customer_number
       FROM customer_referrals cr
       JOIN customers c ON c.id = cr.referred_customer_id
       WHERE cr.referrer_customer_id = ?
       ORDER BY cr.created_at DESC`,
      [customerId]
    );

    const referralReceived = await dbGet(
      `SELECT cr.*, c.company_name as referrer_company_name, c.customer_number as referrer_customer_number
       FROM customer_referrals cr
       JOIN customers c ON c.id = cr.referrer_customer_id
       WHERE cr.referred_customer_id = ?`,
      [customerId]
    );

    const rewards = await dbAll(
      `SELECT * FROM referral_rewards WHERE customer_id = ? ORDER BY created_at DESC`,
      [customerId]
    );

    const totalRewardsEarned = rewards
      .filter((r) => r.status !== 'expired')
      .reduce((sum, r) => sum + (r.reward_amount || 0), 0);

    res.json({
      referrals_made: referralsMade || [],
      referral_received: referralReceived || null,
      rewards: rewards || [],
      total_rewards_earned: totalRewardsEarned,
      referrals_count: (referralsMade || []).length,
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

router.post('/reward', async (req, res) => {
  try {
    const { referral_id, customer_id, reward_amount, description } = req.body || {};
    if (!customer_id || !reward_amount) {
      return res.status(400).json({ error: 'customer_id and reward_amount are required' });
    }

    const reward = await dbRun(
      `INSERT INTO referral_rewards (customer_id, referral_id, reward_amount, description, status, created_at)
       VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)`,
      [customer_id, referral_id || null, reward_amount, description || 'Referral reward']
    );

    const created = await dbGet(`SELECT * FROM referral_rewards WHERE id = ?`, [reward.lastID]);
    res.status(201).json(created);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

router.post('/reward/:reward_id/issue', async (req, res) => {
  try {
    const rewardId = Number(req.params.reward_id);
    await dbRun(
      `UPDATE referral_rewards SET status = 'issued', issued_at = CURRENT_TIMESTAMP WHERE id = ?`,
      [rewardId]
    );
    const updated = await dbGet(`SELECT * FROM referral_rewards WHERE id = ?`, [rewardId]);
    if (!updated) return res.status(404).json({ error: 'Reward not found' });
    res.json(updated);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

router.post('/reward/:reward_id/redeem', async (req, res) => {
  try {
    const rewardId = Number(req.params.reward_id);
    await dbRun(
      `UPDATE referral_rewards SET status = 'redeemed', redeemed_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'issued'`,
      [rewardId]
    );
    const updated = await dbGet(`SELECT * FROM referral_rewards WHERE id = ?`, [rewardId]);
    if (!updated) return res.status(404).json({ error: 'Reward not found or not issued' });
    res.json(updated);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

router.get('/validate/:code', async (req, res) => {
  try {
    const code = String(req.params.code || '').trim();
    if (!code) return res.status(400).json({ error: 'Code required' });

    const referrer = await dbGet(
      `SELECT id, customer_number, company_name, referral_code FROM customers WHERE referral_code = ?`,
      [code]
    );

    if (!referrer) {
      return res.json({ valid: false, error: 'Invalid referral code' });
    }

    res.json({
      valid: true,
      referrer: {
        id: referrer.id,
        customer_number: referrer.customer_number,
        company_name: referrer.company_name,
      },
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

router.get('/stats', async (req, res) => {
  try {
    const totalReferrals = await dbGet(`SELECT COUNT(*) as count FROM customer_referrals`);
    const pendingReferrals = await dbGet(`SELECT COUNT(*) as count FROM customer_referrals WHERE status = 'pending'`);
    const qualifiedReferrals = await dbGet(
      `SELECT COUNT(*) as count FROM customer_referrals WHERE status = 'qualified'`
    );
    const rewardedReferrals = await dbGet(
      `SELECT COUNT(*) as count FROM customer_referrals WHERE status = 'rewarded'`
    );
    const totalRewardsIssued = await dbGet(
      `SELECT COALESCE(SUM(reward_amount), 0) as total FROM referral_rewards WHERE status IN ('issued', 'redeemed')`
    );
    const topReferrers = await dbAll(
      `SELECT c.id, c.customer_number, c.company_name, COUNT(cr.id) as referral_count
       FROM customers c
       JOIN customer_referrals cr ON cr.referrer_customer_id = c.id
       GROUP BY c.id
       ORDER BY referral_count DESC
       LIMIT 10`
    );

    res.json({
      total_referrals: totalReferrals?.count || 0,
      pending_referrals: pendingReferrals?.count || 0,
      qualified_referrals: qualifiedReferrals?.count || 0,
      rewarded_referrals: rewardedReferrals?.count || 0,
      total_rewards_issued: totalRewardsIssued?.total || 0,
      top_referrers: topReferrers || [],
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

module.exports = router;
