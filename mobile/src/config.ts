// Address of the API. EXPO_PUBLIC_ variables are read by Expo at build time.
export const API_URL = (
  process.env.EXPO_PUBLIC_API_URL || 'https://clinique-physio-api.onrender.com'
).replace(/\/$/, '');

// Address of the website, used for pages the app opens in the browser (password reset).
export const WEB_URL = (process.env.EXPO_PUBLIC_WEB_URL || 'https://clinique-physio.vercel.app').replace(
  /\/$/,
  '',
);
