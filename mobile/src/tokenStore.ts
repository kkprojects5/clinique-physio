// The access token is kept in the phone's secure storage (Keychain / Keystore),
// never in plain storage (spec B.8.2).
import * as SecureStore from 'expo-secure-store';

const KEY = 'access_token';

export const tokenStore = {
  get: () => SecureStore.getItemAsync(KEY),
  set: (token: string) => SecureStore.setItemAsync(KEY, token),
  clear: () => SecureStore.deleteItemAsync(KEY),
};
