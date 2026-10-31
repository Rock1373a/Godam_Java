import { Platform } from 'react-native';
import Constants from 'expo-constants';
import * as Application from 'expo-application';
import * as SecureStore from 'expo-secure-store';
import { api } from './api';

const SESSION_ID_KEY = 'analytics_session_id';
const DEVICE_ID_KEY = 'analytics_device_id';

let cachedSessionId: string | null = null;
let cachedDeviceId: string | null = null;

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
}

async function getSessionId(): Promise<string> {
  if (cachedSessionId) return cachedSessionId;
  try {
    const stored = await SecureStore.getItemAsync(SESSION_ID_KEY);
    if (stored) {
      cachedSessionId = stored;
      return stored;
    }
  } catch {}
  const newId = generateId();
  cachedSessionId = newId;
  try {
    await SecureStore.setItemAsync(SESSION_ID_KEY, newId);
  } catch {}
  return newId;
}

async function getDeviceId(): Promise<string> {
  if (cachedDeviceId) return cachedDeviceId;
  try {
    const stored = await SecureStore.getItemAsync(DEVICE_ID_KEY);
    if (stored) {
      cachedDeviceId = stored;
      return stored;
    }
  } catch {}
  const newId = generateId();
  cachedDeviceId = newId;
  try {
    await SecureStore.setItemAsync(DEVICE_ID_KEY, newId);
  } catch {}
  return newId;
}

function getAppVersion(): string {
  return (
    Constants.expoConfig?.version ||
    Application.nativeApplicationVersion ||
    'unknown'
  );
}

function getPlatform(): string {
  return Platform.OS;
}

export type AnalyticsEventName =
  | 'app_launched'
  | 'backend_url_configured'
  | 'login_screen_viewed'
  | 'login_success'
  | 'login_failure'
  | 'first_action_success';

export interface AnalyticsEventData {
  [key: string]: string | number | boolean | null | undefined;
}

export async function trackEvent(
  eventName: AnalyticsEventName,
  eventData?: AnalyticsEventData
): Promise<void> {
  try {
    const [sessionId, deviceId] = await Promise.all([getSessionId(), getDeviceId()]);
    const platform = getPlatform();
    const appVersion = getAppVersion();

    await api.post('/analytics/events', {
      eventName,
      eventCategory: 'onboarding',
      sessionId,
      deviceId,
      platform,
      appVersion,
      eventData: eventData || null,
    });
  } catch (e) {
    console.warn('Analytics event failed:', eventName, e);
  }
}

export async function trackAppLaunched(): Promise<void> {
  await trackEvent('app_launched', { timestamp: Date.now() });
}

export async function trackBackendUrlConfigured(urlOrigin: string): Promise<void> {
  await trackEvent('backend_url_configured', { urlOrigin });
}

export async function trackLoginScreenViewed(): Promise<void> {
  await trackEvent('login_screen_viewed');
}

export async function trackLoginSuccess(username: string): Promise<void> {
  await trackEvent('login_success', { username });
}

export async function trackLoginFailure(error: string): Promise<void> {
  await trackEvent('login_failure', { error });
}

export async function trackFirstActionSuccess(action: string): Promise<void> {
  await trackEvent('first_action_success', { action });
}

export function resetSessionId(): void {
  cachedSessionId = null;
  SecureStore.deleteItemAsync(SESSION_ID_KEY).catch(() => {});
}
