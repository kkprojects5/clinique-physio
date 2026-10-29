// Address of the API. EXPO_PUBLIC_ variables are read by Expo at build time.
export const API_URL = (
  process.env.EXPO_PUBLIC_API_URL || 'https://clinique-physio-api.onrender.com'
).replace(/\/$/, '');
