import { useCallback, useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { translate, type Language } from './src/i18n';
import { tokenStore } from './src/tokenStore';
import { colors } from './src/theme';
import LoginScreen from './src/screens/LoginScreen';
import AppointmentsScreen from './src/screens/AppointmentsScreen';

export default function App() {
  const [language, setLanguage] = useState<Language>('fr');
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  // Reopen the app logged in if a token is still stored (it is refused once expired).
  useEffect(() => {
    tokenStore
      .get()
      .then(setToken)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  const loggedIn = useCallback(async (accessToken: string) => {
    await tokenStore.set(accessToken);
    setNotice(null);
    setToken(accessToken);
  }, []);

  const loggedOut = useCallback(
    async (message: string | null) => {
      await tokenStore.clear();
      setNotice(message);
      setToken(null);
    },
    [],
  );

  const other: Language = language === 'fr' ? 'en' : 'fr';

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safe}>
        <StatusBar style="dark" />
        <View style={styles.topBar}>
          <Text style={styles.brand}>{translate(language, 'appTitle')}</Text>
          <Pressable
            onPress={() => setLanguage(other)}
            accessibilityRole="button"
            accessibilityLabel={translate(language, 'switchLanguageLabel')}
            style={styles.langButton}
          >
            <Text style={styles.langText}>{translate(language, 'switchLanguage')}</Text>
          </Pressable>
        </View>
        <View style={styles.content}>
          {!ready ? null : token ? (
            <AppointmentsScreen
              language={language}
              accessToken={token}
              onExpired={() => loggedOut(translate(language, 'error.expired'))}
              onLogout={() => loggedOut(null)}
            />
          ) : (
            <LoginScreen key={notice ?? 'login'} language={language} notice={notice} onLoggedIn={loggedIn} />
          )}
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.cream },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: colors.paper,
    borderBottomColor: colors.line,
    borderBottomWidth: 1,
  },
  brand: { fontWeight: '700', color: colors.tealDark, fontSize: 16 },
  langButton: {
    minHeight: 40,
    paddingHorizontal: 14,
    justifyContent: 'center',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.line,
  },
  langText: { color: colors.tealDark, fontWeight: '600' },
  content: { flex: 1, padding: 16 },
});
