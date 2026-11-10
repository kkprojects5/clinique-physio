import { useCallback, useEffect, useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import {
  ApiError,
  checkOff,
  myProgram,
  undoCheckOff,
  type Program,
  type ProgramItem,
} from '../api';
import { dayBefore, dayLabel } from '../format';
import { translate, type Language, type TextKey } from '../i18n';
import { colors } from '../theme';

type Props = {
  language: Language;
  accessToken: string;
  onExpired: () => void;
};

const PAIN_LEVELS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

// My home exercise program (B-EXE-03): check off each exercise once a day, with the pain felt.
// The therapist sees the adherence and pain levels in their workspace.
export default function ExercisesScreen({ language, accessToken, onExpired }: Props) {
  const t = (key: TextKey | string, params?: Record<string, string>) =>
    translate(language, key, params);
  const [program, setProgram] = useState<Program | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [asking, setAsking] = useState<string | null>(null); // item waiting for the pain level
  const [open, setOpen] = useState<string | null>(null); // item showing its instructions
  const [todayLogs, setTodayLogs] = useState<Record<string, string>>({}); // item -> check-off id

  const fail = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.kind === 'unauthorized') {
        onExpired();
        return;
      }
      const key =
        e instanceof ApiError && e.kind === 'offline' ? 'error.offline' : 'error.generic';
      setError(translate(language, key));
    },
    [language, onExpired],
  );

  const load = useCallback(
    () =>
      myProgram(accessToken).then((answer) => {
        setError(null);
        setProgram(answer);
      }, fail),
    [accessToken, fail],
  );

  useEffect(() => {
    load();
  }, [load]);

  async function refresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  async function done(item: ProgramItem, pain: number | null) {
    setAsking(null);
    try {
      const log = await checkOff(accessToken, item.id, pain);
      setTodayLogs((logs) => ({ ...logs, [item.id]: log.id }));
      await load();
    } catch (e) {
      if (e instanceof ApiError && e.kind === 'conflict') {
        await load(); // show it as done (perhaps checked on another device)
        setError(t('alreadyDone')); // after the reload, which clears old messages
        return;
      }
      fail(e);
    }
  }

  async function undo(item: ProgramItem) {
    const id = todayLogs[item.id];
    if (!id) return;
    try {
      await undoCheckOff(accessToken, id);
      setTodayLogs(({ [item.id]: _removed, ...rest }) => rest);
      await load();
    } catch (e) {
      fail(e);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title} accessibilityRole="header">
        {t('myProgram')}
      </Text>
      {error ? (
        <Text style={styles.error} accessibilityRole="alert">
          {error}
        </Text>
      ) : null}
      {program === undefined && !error ? <Text style={styles.hint}>{t('loading')}</Text> : null}
      {program === null ? <Text style={styles.empty}>{t('noProgram')}</Text> : null}
      {program ? (
        <FlatList
          data={program.items}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
          contentContainerStyle={{ gap: 10, paddingBottom: 24 }}
          ListHeaderComponent={
            <View style={styles.programHeader}>
              <Text style={styles.hint}>
                {t('programBy', {
                  name: `${program.therapist.first_name} ${program.therapist.last_name}`,
                  end: dayLabel(dayBefore(program.end_date), language),
                })}
              </Text>
              {program.notes ? <Text style={styles.notes}>{program.notes}</Text> : null}
            </View>
          }
          renderItem={({ item }) => {
            const ex = item.exercise;
            const name = language === 'en' ? ex.name_en : ex.name_fr;
            return (
              <View style={styles.card}>
                <Text style={styles.name}>{name}</Text>
                <Text style={styles.meta}>
                  {language === 'en' ? ex.description_en : ex.description_fr}
                </Text>
                <Text style={styles.dose}>
                  {t('dose', { sets: String(item.sets), reps: String(item.reps) })}
                </Text>
                <Text style={styles.meta}>
                  {t('thisWeek', {
                    done: String(item.done_this_week),
                    times: String(item.times_per_week),
                  })}
                </Text>

                <Pressable
                  onPress={() => setOpen(open === item.id ? null : item.id)}
                  accessibilityRole="button"
                  accessibilityState={{ expanded: open === item.id }}
                  style={styles.link}
                >
                  <Text style={styles.linkText}>
                    {open === item.id ? t('hideHow') : t('showHow')}
                  </Text>
                </Pressable>
                {open === item.id ? (
                  <Text style={styles.instructions}>
                    {language === 'en' ? ex.instructions_en : ex.instructions_fr}
                  </Text>
                ) : null}

                {item.done_today ? (
                  <View style={styles.row}>
                    <Text style={styles.doneText}>{t('doneToday')}</Text>
                    {todayLogs[item.id] ? (
                      <Pressable
                        onPress={() => undo(item)}
                        accessibilityRole="button"
                        accessibilityLabel={`${t('undo')} — ${name}`}
                        style={styles.secondary}
                      >
                        <Text style={styles.secondaryText}>{t('undo')}</Text>
                      </Pressable>
                    ) : null}
                  </View>
                ) : asking === item.id ? (
                  <View>
                    <Text style={styles.question}>{t('painQuestion')}</Text>
                    <View style={styles.painRow}>
                      {PAIN_LEVELS.map((level) => (
                        <Pressable
                          key={level}
                          onPress={() => done(item, level)}
                          accessibilityRole="button"
                          accessibilityLabel={t('painLabel', { level: String(level) })}
                          style={styles.pain}
                        >
                          <Text style={styles.painText}>{level}</Text>
                        </Pressable>
                      ))}
                    </View>
                    <Pressable
                      onPress={() => done(item, null)}
                      accessibilityRole="button"
                      style={styles.secondary}
                    >
                      <Text style={styles.secondaryText}>{t('skipPain')}</Text>
                    </Pressable>
                  </View>
                ) : (
                  <Pressable
                    onPress={() => setAsking(item.id)}
                    accessibilityRole="button"
                    accessibilityLabel={`${t('didIt')} — ${name}`}
                    style={styles.button}
                  >
                    <Text style={styles.buttonText}>{t('didIt')}</Text>
                  </Pressable>
                )}
              </View>
            );
          }}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  title: { fontSize: 24, fontWeight: '700', color: colors.tealDark, marginBottom: 6 },
  hint: { color: colors.inkSoft, marginBottom: 8 },
  notes: { color: colors.ink, fontStyle: 'italic', marginBottom: 8 },
  programHeader: { marginBottom: 4 },
  empty: { color: colors.inkSoft, fontSize: 16 },
  card: {
    backgroundColor: colors.paper,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    gap: 4,
  },
  name: { color: colors.tealDark, fontWeight: '700', fontSize: 17 },
  dose: { fontSize: 18, fontWeight: '700', color: colors.ink },
  meta: { color: colors.inkSoft },
  instructions: { color: colors.ink, lineHeight: 21 },
  link: { minHeight: 44, justifyContent: 'center', alignSelf: 'flex-start' },
  linkText: { color: colors.tealDark, textDecorationLine: 'underline', fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  doneText: { color: colors.teal, fontWeight: '700', fontSize: 16 },
  question: { color: colors.ink, fontWeight: '600', marginVertical: 6 },
  painRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  pain: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
  },
  painText: { color: colors.tealDark, fontWeight: '700', fontSize: 16 },
  button: {
    minHeight: 48,
    marginTop: 6,
    borderRadius: 999,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  buttonText: { color: colors.paper, fontWeight: '700', fontSize: 16 },
  secondary: {
    minHeight: 44,
    marginTop: 6,
    paddingHorizontal: 16,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'flex-start',
  },
  secondaryText: { color: colors.tealDark, fontWeight: '600' },
  error: {
    backgroundColor: colors.errorBg,
    color: colors.errorText,
    padding: 12,
    borderRadius: 10,
    marginBottom: 12,
  },
});
