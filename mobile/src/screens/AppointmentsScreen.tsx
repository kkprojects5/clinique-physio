import { useCallback, useEffect, useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { ApiError, myAppointments, type MyAppointment } from '../api';
import { addMinutes, clockTime, dayLabel } from '../format';
import { translate, type Language, type TextKey } from '../i18n';
import { colors } from '../theme';

type Props = {
  language: Language;
  accessToken: string;
  onExpired: () => void;
  onLogout: () => void;
};

export default function AppointmentsScreen({ language, accessToken, onExpired, onLogout }: Props) {
  const t = (key: TextKey | string, params?: Record<string, string>) =>
    translate(language, key, params);
  const [items, setItems] = useState<MyAppointment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // State is only updated when the answer arrives (in the promise callbacks).
  const load = useCallback(
    () =>
      myAppointments(accessToken).then(
        (list) => {
          setError(null);
          setItems(list);
        },
        (e: unknown) => {
          if (e instanceof ApiError && e.kind === 'unauthorized') {
            onExpired(); // the 10-minute access token expired
            return;
          }
          const key = e instanceof ApiError && e.kind === 'offline' ? 'error.offline' : 'error.generic';
          setError(translate(language, key));
        },
      ),
    [accessToken, language, onExpired],
  );

  useEffect(() => {
    load();
  }, [load]);

  async function refresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title} accessibilityRole="header">
          {t('myAppointments')}
        </Text>
        <Pressable onPress={onLogout} accessibilityRole="button" style={styles.logout}>
          <Text style={styles.logoutText}>{t('logout')}</Text>
        </Pressable>
      </View>
      <Text style={styles.hint}>{t('timezone')}</Text>

      {error ? (
        <Text style={styles.error} accessibilityRole="alert">
          {error}
        </Text>
      ) : null}
      {items === null && !error ? <Text style={styles.hint}>{t('loading')}</Text> : null}

      <FlatList
        data={items ?? []}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
        ListEmptyComponent={items ? <Text style={styles.empty}>{t('noAppointments')}</Text> : undefined}
        contentContainerStyle={{ gap: 10, paddingBottom: 24 }}
        renderItem={({ item }) => {
          const start = clockTime(item.start_local);
          const end = addMinutes(start, item.service.duration_min);
          const therapist = `${item.therapist.first_name} ${item.therapist.last_name}`;
          return (
            <View style={styles.card} accessible accessibilityLabel={`${dayLabel(item.start_local, language)}, ${start}`}>
              <Text style={styles.day}>{dayLabel(item.start_local, language)}</Text>
              <Text style={styles.time}>
                {start}–{end}
              </Text>
              <Text style={styles.service}>
                {language === 'en' ? item.service.name_en : item.service.name_fr}
              </Text>
              <Text style={styles.meta}>{t('with', { name: therapist })}</Text>
              <Text style={styles.status}>{t(`status.${item.status}`)}</Text>
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontSize: 24, fontWeight: '700', color: colors.tealDark },
  logout: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 8 },
  logoutText: { color: colors.tealDark, fontWeight: '600' },
  hint: { color: colors.inkSoft, marginBottom: 12 },
  empty: { color: colors.inkSoft, fontSize: 16 },
  card: {
    backgroundColor: colors.paper,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
  },
  day: { color: colors.tealDark, fontWeight: '700', fontSize: 16 },
  time: { fontSize: 20, fontWeight: '700', color: colors.ink, marginVertical: 2 },
  service: { color: colors.ink, fontSize: 15 },
  meta: { color: colors.inkSoft },
  status: { color: colors.inkSoft, fontStyle: 'italic', marginTop: 4 },
  error: {
    backgroundColor: colors.errorBg,
    color: colors.errorText,
    padding: 12,
    borderRadius: 10,
    marginBottom: 12,
  },
});
