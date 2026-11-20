import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { initPaymentSheet, initStripe, presentPaymentSheet } from '@stripe/stripe-react-native';
import {
  ApiError,
  freeSlots,
  hold,
  myAppointments,
  services as loadServices,
  startPayment,
  therapists as loadTherapists,
  type Booking,
  type Service,
  type Slot,
  type Therapist,
} from '../api';
import { clinicToday, clockTime, dayLabel, money, nextDays } from '../format';
import { translate, type Language, type TextKey } from '../i18n';
import { colors } from '../theme';

type Props = {
  language: Language;
  accessToken: string;
  onExpired: () => void;
  onBooked: () => void; // go to "My appointments"
  pollMs?: number; // how often to check that Stripe's confirmation arrived (tests use 0)
};

type Step = 'service' | 'therapist' | 'time' | 'review' | 'waiting' | 'done' | 'slow';

const DAYS_SHOWN = 14;
const CHECKS = 15; // about 30 seconds at 2 seconds each

// Booking from the phone (B-BKG-01): service, therapist or first available, day and time,
// then the deposit paid with Stripe's payment sheet (test mode). The card details go straight
// to Stripe; the appointment is confirmed when Stripe's signed webhook reaches the API.
export default function BookScreen({ language, accessToken, onExpired, onBooked, pollMs = 2000 }: Props) {
  const t = (key: TextKey | string, params?: Record<string, string>) =>
    translate(language, key, params);
  const [step, setStep] = useState<Step>('service');
  const [catalog, setCatalog] = useState<{ services: Service[]; team: Therapist[] } | null>(null);
  const [service, setService] = useState<Service | null>(null);
  const [therapist, setTherapist] = useState<Therapist | null>(null); // null: first available
  const [day, setDay] = useState(() => clinicToday());
  // Free times with the search they answer, so an old answer is never shown for a new day.
  const [found, setFound] = useState<{ key: string; slots: Slot[] } | null>(null);
  const [slot, setSlot] = useState<Slot | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const fail = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.kind === 'unauthorized') return onExpired();
      const key =
        e instanceof ApiError && e.kind === 'offline' ? 'error.offline' : 'error.generic';
      setMessage(translate(language, key));
    },
    [language, onExpired],
  );

  useEffect(() => {
    Promise.all([loadServices(), loadTherapists()]).then(
      ([list, team]) => setCatalog({ services: list, team }),
      fail,
    );
  }, [fail]);

  const searchKey = `${service?.id}|${therapist?.id ?? 'any'}|${day}`;

  useEffect(() => {
    if (step !== 'time' || !service) return;
    let active = true;
    freeSlots(service.id, therapist?.id ?? null, day).then(
      (list) => active && setFound({ key: `${service.id}|${therapist?.id ?? 'any'}|${day}`, slots: list }),
      (e) => active && fail(e),
    );
    return () => {
      active = false;
    };
  }, [step, service, therapist, day, fail]);
  const slots = found?.key === searchKey ? found.slots : null;

  const name = (id: string) => {
    const person = catalog?.team.find((x) => x.id === id);
    return person ? `${person.first_name} ${person.last_name}` : '';
  };
  const serviceName = (s: Service) => (language === 'en' ? s.name_en : s.name_fr);

  /** Wait until the API has received Stripe's confirmation (the webhook). */
  async function waitForConfirmation(appointmentId: string) {
    setStep('waiting');
    for (let i = 0; i < CHECKS; i += 1) {
      try {
        const mine = await myAppointments(accessToken);
        if (mine.some((a) => a.id === appointmentId && a.status === 'confirmed')) {
          setStep('done');
          return;
        }
      } catch (e) {
        if (e instanceof ApiError && e.kind === 'unauthorized') return onExpired();
      }
      await new Promise((resolve) => setTimeout(resolve, pollMs));
    }
    setStep('slow');
  }

  /** Hold the time (once), then open Stripe's payment sheet. Can be retried. */
  async function pay() {
    if (!service || !slot) return;
    setMessage(null);
    setBusy(true);
    try {
      let current = booking;
      if (!current) {
        try {
          current = await hold(accessToken, service.id, slot);
        } catch (e) {
          if (e instanceof ApiError && e.kind === 'conflict') {
            setMessage(t('slotTaken'));
            setSlot(null);
            setStep('time');
            return;
          }
          throw e;
        }
        setBooking(current);
      }
      let payment;
      try {
        payment = await startPayment(accessToken, current.id);
      } catch (e) {
        if (e instanceof ApiError && e.status === 503) return setMessage(t('paymentOff'));
        throw e;
      }
      await initStripe({ publishableKey: payment.publishable_key });
      const init = await initPaymentSheet({
        paymentIntentClientSecret: payment.client_secret,
        merchantDisplayName: 'Clinique Physio Mont-Royal',
      });
      if (init.error) return setMessage(t('paymentFailed', { reason: init.error.message }));
      const result = await presentPaymentSheet();
      if (result.error) {
        return setMessage(
          result.error.code === 'Canceled'
            ? t('paymentCancelled')
            : t('paymentFailed', { reason: result.error.message }),
        );
      }
      await waitForConfirmation(current.id);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }

  if (!catalog) {
    return message ? <Text style={styles.error}>{message}</Text> : <ActivityIndicator color={colors.teal} />;
  }

  const back = (to: Step) => (
    <Pressable onPress={() => { setMessage(null); setStep(to); }} accessibilityRole="button" style={styles.back}>
      <Text style={styles.backText}>{t('back')}</Text>
    </Pressable>
  );

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title} accessibilityRole="header">
        {t('bookTitle')}
      </Text>
      {message && (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {message}
        </Text>
      )}

      {step === 'service' && (
        <>
          <Text style={styles.step}>{t('chooseService')}</Text>
          {catalog.services.map((s) => (
            <Choice
              key={s.id}
              title={serviceName(s)}
              detail={t('serviceLine', {
                minutes: String(s.duration_min),
                price: money(s.price_cents, language),
                deposit: money(s.deposit_cents, language),
              })}
              onPress={() => {
                setService(s);
                setTherapist(null);
                setStep('therapist');
              }}
            />
          ))}
        </>
      )}

      {step === 'therapist' && service && (
        <>
          {back('service')}
          <Text style={styles.step}>{t('chooseTherapist')}</Text>
          <Choice
            title={t('firstAvailable')}
            onPress={() => {
              setTherapist(null);
              setStep('time');
            }}
          />
          {catalog.team
            .filter((x) => service.therapist_ids.includes(x.id))
            .map((x) => (
              <Choice
                key={x.id}
                title={`${x.first_name} ${x.last_name}`}
                onPress={() => {
                  setTherapist(x);
                  setStep('time');
                }}
              />
            ))}
        </>
      )}

      {step === 'time' && (
        <>
          {back('therapist')}
          <Text style={styles.step}>{t('chooseTime')}</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.days}>
            {nextDays(clinicToday(), DAYS_SHOWN).map((d) => (
              <Pressable
                key={d}
                onPress={() => setDay(d)}
                accessibilityRole="button"
                accessibilityState={{ selected: d === day }}
                style={[styles.day, d === day && styles.dayActive]}
              >
                <Text style={[styles.dayText, d === day && styles.dayTextActive]}>
                  {dayLabel(d, language)}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
          {slots === null ? (
            <ActivityIndicator color={colors.teal} />
          ) : slots.length === 0 ? (
            <Text style={styles.hint}>{t('noSlot')}</Text>
          ) : (
            slots.map((s) => (
              <Choice
                key={`${s.therapist_id}-${s.start}`}
                title={t('slotWith', { time: clockTime(s.start_local), name: name(s.therapist_id) })}
                onPress={() => {
                  setSlot(s);
                  setBooking(null);
                  setMessage(null);
                  setStep('review');
                }}
              />
            ))
          )}
        </>
      )}

      {step === 'review' && service && slot && (
        <>
          {!booking && back('time')}
          <Text style={styles.step}>{t('reviewTitle')}</Text>
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{serviceName(service)}</Text>
            <Text style={styles.text}>
              {t('reviewWhen', { day: dayLabel(slot.start_local, language), time: clockTime(slot.start_local) })}
            </Text>
            <Text style={styles.text}>{name(slot.therapist_id)}</Text>
            <Text style={styles.hint}>
              {t('depositInfo', {
                deposit: money(service.deposit_cents, language),
                rest: money(service.price_cents - service.deposit_cents, language),
              })}
            </Text>
          </View>
          {booking && <Text style={styles.hint}>{t('holding')}</Text>}
          <Pressable
            onPress={pay}
            disabled={busy}
            accessibilityRole="button"
            style={[styles.button, busy && styles.buttonBusy]}
          >
            <Text style={styles.buttonText}>
              {booking ? t('tryAgain') : t('payDeposit', { deposit: money(service.deposit_cents, language) })}
            </Text>
          </Pressable>
        </>
      )}

      {step === 'waiting' && (
        <View style={styles.card}>
          <ActivityIndicator color={colors.teal} />
          <Text style={styles.text}>{t('waiting')}</Text>
        </View>
      )}

      {(step === 'done' || step === 'slow') && (
        <View style={styles.card}>
          {step === 'done' ? (
            <>
              <Text style={styles.cardTitle}>{t('bookedTitle')}</Text>
              <Text style={styles.text}>{t('bookedText')}</Text>
            </>
          ) : (
            <Text style={styles.text}>{t('slowConfirm')}</Text>
          )}
          <Pressable onPress={onBooked} accessibilityRole="button" style={styles.button}>
            <Text style={styles.buttonText}>{t('seeAppointments')}</Text>
          </Pressable>
        </View>
      )}
    </ScrollView>
  );
}

function Choice({ title, detail, onPress }: { title: string; detail?: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={styles.choice}>
      <Text style={styles.choiceTitle}>{title}</Text>
      {detail ? <Text style={styles.hint}>{detail}</Text> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { paddingBottom: 32, gap: 10 },
  title: { fontSize: 22, fontWeight: '700', color: colors.tealDark },
  step: { fontSize: 17, fontWeight: '700', color: colors.ink, marginTop: 6 },
  hint: { color: colors.inkSoft },
  text: { color: colors.ink, fontSize: 16 },
  error: { backgroundColor: colors.errorBg, color: colors.errorText, padding: 12, borderRadius: 10 },
  choice: {
    backgroundColor: colors.paper,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    minHeight: 48,
  },
  choiceTitle: { fontSize: 16, fontWeight: '600', color: colors.tealDark },
  back: { alignSelf: 'flex-start', minHeight: 44, justifyContent: 'center' },
  backText: { color: colors.tealDark, fontWeight: '600' },
  days: { flexGrow: 0, marginBottom: 4 },
  day: {
    paddingHorizontal: 14,
    minHeight: 44,
    justifyContent: 'center',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.line,
    marginRight: 8,
    backgroundColor: colors.paper,
  },
  dayActive: { backgroundColor: colors.teal, borderColor: colors.teal },
  dayText: { color: colors.tealDark, fontWeight: '600' },
  dayTextActive: { color: colors.paper },
  card: {
    backgroundColor: colors.paper,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    gap: 8,
  },
  cardTitle: { fontSize: 18, fontWeight: '700', color: colors.tealDark },
  button: {
    backgroundColor: colors.teal,
    borderRadius: 999,
    minHeight: 48,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 18,
    marginTop: 4,
  },
  buttonBusy: { opacity: 0.6 },
  buttonText: { color: colors.paper, fontWeight: '700', fontSize: 16 },
});
