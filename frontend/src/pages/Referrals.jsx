import { useEffect, useState } from 'react';
import { Gift, Users, Copy, Check, Award, TrendingUp, Clock } from 'lucide-react';
import { referralsApi } from '../services/api';

export default function Referrals() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [referralStatus, setReferralStatus] = useState(null);
  const [referralCode, setReferralCode] = useState(null);
  const [applyForm, setApplyForm] = useState({ referral_code: '', new_customer_id: '' });
  const [applyResult, setApplyResult] = useState(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await referralsApi.stats();
      setStats(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchReferralCode = async () => {
    if (!selectedCustomerId) return;
    try {
      const data = await referralsApi.getCode(selectedCustomerId);
      setReferralCode(data);
    } catch (e) {
      setError(e.message);
    }
  };

  const fetchReferralStatus = async () => {
    if (!selectedCustomerId) return;
    try {
      const data = await referralsApi.status(selectedCustomerId);
      setReferralStatus(data);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    if (selectedCustomerId) {
      fetchReferralCode();
      fetchReferralStatus();
    }
  }, [selectedCustomerId]);

  const handleApplyReferral = async (e) => {
    e.preventDefault();
    if (!applyForm.referral_code || !applyForm.new_customer_id) return;
    try {
      const result = await referralsApi.apply(applyForm);
      setApplyResult(result);
      setApplyForm({ referral_code: '', new_customer_id: '' });
      fetchStats();
    } catch (e) {
      setError(e.message);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Gift className="w-8 h-8 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Referral Program</h1>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <Users className="w-4 h-4" />
            Total Referrals
          </div>
          <div className="text-2xl font-bold text-gray-900">{stats?.total_referrals || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <Clock className="w-4 h-4" />
            Pending
          </div>
          <div className="text-2xl font-bold text-yellow-600">{stats?.pending_referrals || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <Check className="w-4 h-4" />
            Qualified
          </div>
          <div className="text-2xl font-bold text-green-600">{stats?.qualified_referrals || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <Award className="w-4 h-4" />
            Rewards Issued
          </div>
          <div className="text-2xl font-bold text-blue-600">{stats?.total_rewards_issued || 0} SAR</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Gift className="w-5 h-5" />
            Get Referral Code
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Customer ID</label>
              <input
                type="number"
                value={selectedCustomerId}
                onChange={(e) => setSelectedCustomerId(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter customer ID"
              />
            </div>
            {referralCode && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">Your Referral Code</div>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-mono font-bold text-blue-600">
                    {referralCode.referral_code}
                  </span>
                  <button
                    onClick={() => copyToClipboard(referralCode.referral_code)}
                    className="p-1 hover:bg-gray-200 rounded"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4 text-gray-500" />
                    )}
                  </button>
                </div>
                <div className="text-sm text-gray-500 mt-2">
                  Customer: {referralCode.company_name} ({referralCode.customer_number})
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="w-5 h-5" />
            Apply Referral Code
          </h2>
          <form onSubmit={handleApplyReferral} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Referral Code</label>
              <input
                type="text"
                value={applyForm.referral_code}
                onChange={(e) => setApplyForm({ ...applyForm, referral_code: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="XXXX-XXXXXX"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">New Customer ID</label>
              <input
                type="number"
                value={applyForm.new_customer_id}
                onChange={(e) => setApplyForm({ ...applyForm, new_customer_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter new customer ID"
              />
            </div>
            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Apply Referral
            </button>
          </form>
          {applyResult && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
              Referral applied successfully! Referred by: {applyResult.referral.referrer_name}
            </div>
          )}
        </div>
      </div>

      {referralStatus && (
        <div className="bg-white p-6 rounded-lg shadow border mb-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Referral Status for Customer #{selectedCustomerId}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-600">Referrals Made</div>
              <div className="text-2xl font-bold">{referralStatus.referrals_count}</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-sm text-green-600">Total Rewards Earned</div>
              <div className="text-2xl font-bold">{referralStatus.total_rewards_earned} SAR</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <div className="text-sm text-purple-600">Referral Received</div>
              <div className="text-2xl font-bold">
                {referralStatus.referral_received ? 'Yes' : 'No'}
              </div>
            </div>
          </div>

          {referralStatus.referrals_made.length > 0 && (
            <div>
              <h3 className="font-medium mb-2">Referrals Made</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left">Customer</th>
                      <th className="px-3 py-2 text-left">Status</th>
                      <th className="px-3 py-2 text-left">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {referralStatus.referrals_made.map((r) => (
                      <tr key={r.id} className="border-t">
                        <td className="px-3 py-2">{r.referred_company_name}</td>
                        <td className="px-3 py-2">
                          <span
                            className={`px-2 py-1 rounded text-xs ${
                              r.status === 'rewarded'
                                ? 'bg-green-100 text-green-700'
                                : r.status === 'qualified'
                                  ? 'bg-blue-100 text-blue-700'
                                  : 'bg-yellow-100 text-yellow-700'
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="px-3 py-2">{new Date(r.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {stats?.top_referrers?.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-lg font-semibold mb-4">Top Referrers</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">Rank</th>
                  <th className="px-3 py-2 text-left">Company</th>
                  <th className="px-3 py-2 text-left">Customer #</th>
                  <th className="px-3 py-2 text-left">Referrals</th>
                </tr>
              </thead>
              <tbody>
                {stats.top_referrers.map((r, i) => (
                  <tr key={r.id} className="border-t">
                    <td className="px-3 py-2 font-medium">#{i + 1}</td>
                    <td className="px-3 py-2">{r.company_name}</td>
                    <td className="px-3 py-2">{r.customer_number}</td>
                    <td className="px-3 py-2 font-bold text-blue-600">{r.referral_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
