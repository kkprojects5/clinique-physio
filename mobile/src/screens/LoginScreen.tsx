import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { ApiError, login } from '../api';
import { translate, type Language, type TextKey } from '../i18n';
import { colors } from '../theme';

type Props = {
  language: Language;
  notice?: string | null;
  onLoggedIn: (accessToken: string) => void;
};

const ERRORS: Record<string, TextKey> = {
  offline: 'error.offline',
  unauthorized: 'error.credentials',
  forbidden: 'error.unverified',
  tooMany: 'error.tooMany',
};

export default function LoginScreen({ language, notice, onLoggedIn }: Props) {
  const t = (key: TextKey) => translate(language, key);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(notice ?? null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError(null);
    if (!email.trim() || !password) {
      setError(t('missing'));
      return;
    }
    setBusy(true);
    try {
      const result = await login(email.trim(), password);
      if (result.kind === 'staff') {
        setError(t('staffAccount'));
        return;
      }
      setPassword('');
      onLoggedIn(result.accessToken);
    } catch (e) {
      setError(t(e instanceof ApiError ? (ERRORS[e.kind] ?? 'error.generic') : 'error.generic'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.card}>
      <Text style={styles.title} accessibilityRole="header">
        {t('loginTitle')}
      </Text>

      <Text style={styles.label} nativeID="emailLabel">
        {t('email')}
      </Text>
      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        accessibilityLabel={t('email')}
        accessibilityLabelledBy="emailLabel"
      />

      <Text style={styles.label} nativeID="passwordLabel">
        {t('password')}
      </Text>
      <TextInput
        style={styles.input}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoComplete="password"
        accessibilityLabel={t('password')}
        accessibilityLabelledBy="passwordLabel"
        onSubmitEditing={submit}
      />

      <Pressable
        style={({ pressed }) => [styles.button, pressed && styles.pressed]}
        onPress={submit}
        disabled={busy}
        accessibilityRole="button"
        accessibilityState={{ disabled: busy, busy }}
      >
        {busy ? <ActivityIndicator color={colors.paper} /> : <Text style={styles.buttonText}>{t('login')}</Text>}
      </Pressable>

      {error ? (
        <Text style={styles.error} accessibilityRole="alert">
          {error}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.paper,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 14,
    padding: 20,
    gap: 6,
  },
  title: { fontSize: 22, fontWeight: '700', color: colors.tealDark, marginBottom: 10 },
  label: { fontWeight: '600', color: colors.ink, marginTop: 6 },
  input: {
    borderColor: '#b9b1a2',
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    minHeight: 48, // comfortable touch target (one-hand use, NFR-09)
    fontSize: 16,
    color: colors.ink,
    backgroundColor: colors.paper,
  },
  button: {
    marginTop: 16,
    backgroundColor: colors.teal,
    borderRadius: 999,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { backgroundColor: colors.tealDark },
  buttonText: { color: colors.paper, fontWeight: '700', fontSize: 16 },
  error: {
    marginTop: 12,
    backgroundColor: colors.errorBg,
    color: colors.errorText,
    padding: 12,
    borderRadius: 10,
  },
});
