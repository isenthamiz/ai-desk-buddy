import { useCallback, useEffect, useState } from 'react';
import {
  Platform, Pressable, ScrollView, StyleSheet, Text, TextInput,
  useWindowDimensions, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { apiBaseUrl, BuddyState, controlApi, ControlStatus, Reminder } from '@/api/client';

const colors = {
  background: '#0c1010', panel: '#171e1c', line: '#2b3531', text: '#f4f2e9',
  muted: '#9ea9a4', mint: '#84f0bc', mintDark: '#173d2e', amber: '#f0c475',
  danger: '#ff958b', input: '#0e1413',
};

const captions: Record<BuddyState, string> = {
  IDLE: 'Buddy is ready when you are.', THINKING: 'Working on your request.',
  SPEAKING: 'Buddy has something to say.', TIMER: 'Keeping time for you.',
  ALERT: 'Buddy needs your attention.', LISTENING: 'Listening for your request.',
  SLEEPING: 'Taking a quiet break.', ERROR: 'Something needs a quick check.',
  OFFLINE: 'Start the simulator to bring Buddy online.',
};

type ActionButtonProps = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  secondary?: boolean;
};

function ActionButton({ label, onPress, disabled, secondary }: ActionButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        secondary ? styles.buttonSecondary : styles.buttonPrimary,
        disabled && styles.buttonDisabled,
        pressed && !disabled && styles.buttonPressed,
      ]}>
      <Text style={[styles.buttonText, secondary && styles.buttonSecondaryText]}>{label}</Text>
    </Pressable>
  );
}

function FieldLabel({ children }: { children: string }) {
  return <Text style={styles.fieldLabel}>{children}</Text>;
}

function formatDueAt(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium', timeStyle: 'short',
  }).format(new Date(value));
}

export default function ControlCenter() {
  const compact = useWindowDimensions().width < 760;
  const [status, setStatus] = useState<ControlStatus | null>(null);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [timerMinutes, setTimerMinutes] = useState('5');
  const [message, setMessage] = useState('');
  const [reminderText, setReminderText] = useState('');
  const [reminderMinutes, setReminderMinutes] = useState('60');
  const [notice, setNotice] = useState<{ text: string; error: boolean } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const showNotice = useCallback((text: string, error = false) => {
    setNotice({ text, error });
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await controlApi.status());
    } catch {
      setStatus(null);
    }
  }, []);

  const refreshReminders = useCallback(async () => {
    try {
      setReminders(await controlApi.reminders());
    } catch (error) {
      showNotice(error instanceof Error ? error.message : 'Could not load reminders.', true);
    }
  }, [showNotice]);

  useEffect(() => {
    const initialStatusTimer = setTimeout(() => void refreshStatus(), 0);
    const initialReminderTimer = setTimeout(() => void refreshReminders(), 0);
    const statusTimer = setInterval(() => void refreshStatus(), 1000);
    const reminderTimer = setInterval(() => void refreshReminders(), 5000);
    return () => {
      clearTimeout(initialStatusTimer);
      clearTimeout(initialReminderTimer);
      clearInterval(statusTimer);
      clearInterval(reminderTimer);
    };
  }, [refreshReminders, refreshStatus]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  const run = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    try {
      await action();
    } catch (error) {
      showNotice(error instanceof Error ? error.message : 'Something went wrong.', true);
    } finally {
      setBusy(null);
    }
  };

  const connected = status?.device.connected ?? false;
  const state = status?.device.state ?? 'OFFLINE';
  const timerActive = status?.timer.active ?? false;

  const startTimer = () => void run('timer', async () => {
    const minutes = Number(timerMinutes);
    if (!Number.isFinite(minutes) || minutes <= 0 || minutes > 1440) {
      throw new Error('Enter between 1 and 1,440 minutes.');
    }
    await controlApi.startTimer(Math.round(minutes * 60));
    showNotice('Timer started.');
    await refreshStatus();
  });

  const sendMessage = () => void run('message', async () => {
    const text = message.trim();
    if (!text) throw new Error('Write a message first.');
    await controlApi.sendText(text);
    setMessage('');
    showNotice('Message sent to Buddy.');
    await refreshStatus();
  });

  const createReminder = () => void run('reminder', async () => {
    const minutes = Number(reminderMinutes);
    if (!reminderText.trim()) throw new Error('Write a reminder first.');
    if (!Number.isFinite(minutes) || minutes <= 0) {
      throw new Error('Reminder delay must be greater than zero.');
    }
    await controlApi.createReminder(
      reminderText.trim(),
      new Date(Date.now() + minutes * 60_000).toISOString(),
    );
    setReminderText('');
    showNotice('Reminder added.');
    await refreshReminders();
  });

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.shell}>
          <View style={[styles.hero, compact && styles.heroCompact]}>
            <View style={styles.heroCopy}>
              <Text style={styles.eyebrow}>AI DESK BUDDY</Text>
              <Text accessibilityRole="header" style={styles.title}>Control Center</Text>
              <Text style={styles.subtitle}>A quiet place to check in, set the pace, and leave a note.</Text>
            </View>
            <View style={styles.connectionCard}>
              <View style={[styles.statusDot, connected && styles.statusDotOnline]} />
              <View>
                <Text style={styles.connectionTitle}>{connected ? 'Buddy connected' : 'Buddy offline'}</Text>
                <Text style={styles.connectionDetail}>
                  {status?.device.type
                    ? `${status.device.id} · ${status.device.type}`
                    : status?.device.id ?? apiBaseUrl}
                </Text>
              </View>
            </View>
          </View>

          <View style={[styles.card, styles.buddyPanel, compact && styles.buddyPanelCompact]}>
            <View style={[styles.face, compact && styles.faceCompact]}><View style={styles.eye} /><View style={styles.eye} /></View>
            <View style={styles.stateCopy}>
              <Text style={styles.sectionLabel}>CURRENT STATE</Text>
              <Text style={[styles.stateTitle, compact && styles.stateTitleCompact]}>{state}</Text>
              <Text style={styles.caption}>{captions[state]}</Text>
            </View>
          </View>

          {notice && (
            <View style={[styles.notice, notice.error && styles.noticeError]}>
              <Text style={[styles.noticeText, notice.error && styles.noticeErrorText]}>{notice.text}</Text>
            </View>
          )}

          <View style={[styles.columns, compact && styles.columnsCompact]}>
            <View style={[styles.card, styles.column]}>
              <View style={styles.cardHeading}>
                <View><Text style={styles.sectionLabel}>QUICK ACTION</Text><Text style={styles.cardTitle}>Timer</Text></View>
                <Text style={styles.badge}>{timerActive ? `${status?.timer.durationSeconds}s active` : 'No timer'}</Text>
              </View>
              <FieldLabel>MINUTES</FieldLabel>
              <TextInput
                accessibilityLabel="Timer minutes"
                keyboardType="number-pad"
                onChangeText={setTimerMinutes}
                style={styles.input}
                value={timerMinutes}
              />
              <View style={styles.actionGap}>
                <ActionButton label={busy === 'timer' ? 'Starting…' : 'Start timer'} onPress={startTimer} disabled={!connected || timerActive || busy !== null} />
                <ActionButton
                  label="Cancel active timer"
                  secondary
                  disabled={!connected || !timerActive || busy !== null}
                  onPress={() => void run('cancel-timer', async () => {
                    await controlApi.cancelTimer();
                    showNotice('Timer cancelled.');
                    await refreshStatus();
                  })}
                />
              </View>
            </View>

            <View style={[styles.card, styles.column]}>
              <Text style={styles.sectionLabel}>SAY SOMETHING</Text>
              <Text style={styles.cardTitle}>Talk to Buddy</Text>
              <TextInput
                accessibilityLabel="Message"
                multiline
                onChangeText={setMessage}
                placeholder="What would you like to ask?"
                placeholderTextColor="#65706b"
                style={[styles.input, styles.messageInput]}
                value={message}
              />
              <ActionButton label={busy === 'message' ? 'Buddy is thinking…' : 'Send to Buddy'} onPress={sendMessage} disabled={!connected || busy !== null} />
            </View>
          </View>

          <View style={[styles.card, styles.remindersCard]}>
            <View style={styles.cardHeading}>
              <View><Text style={styles.sectionLabel}>DON’T FORGET</Text><Text style={styles.cardTitle}>Reminders</Text></View>
              <Text style={[styles.badge, styles.count]}>{reminders.length}</Text>
            </View>
            <View style={[styles.reminderForm, compact && styles.reminderFormCompact]}>
              <View style={styles.reminderTextField}>
                <FieldLabel>REMINDER</FieldLabel>
                <TextInput
                  accessibilityLabel="Reminder"
                  onChangeText={setReminderText}
                  placeholder="Stretch and drink some water"
                  placeholderTextColor="#65706b"
                  style={styles.input}
                  value={reminderText}
                />
              </View>
              <View style={styles.reminderDelayField}>
                <FieldLabel>IN MINUTES</FieldLabel>
                <TextInput
                  accessibilityLabel="Reminder delay in minutes"
                  keyboardType="number-pad"
                  onChangeText={setReminderMinutes}
                  style={styles.input}
                  value={reminderMinutes}
                />
              </View>
              <View style={styles.reminderButton}>
                <ActionButton label={busy === 'reminder' ? 'Adding…' : 'Add reminder'} onPress={createReminder} disabled={busy !== null} />
              </View>
            </View>

            <View style={styles.reminderList}>
              {reminders.length === 0 ? (
                <Text style={styles.empty}>Nothing pending. Your desk is clear.</Text>
              ) : reminders.map((reminder) => (
                <View key={reminder.id} style={styles.reminderRow}>
                  <View style={styles.reminderCopy}>
                    <Text style={styles.reminderTitle}>{reminder.text}</Text>
                    <Text style={styles.reminderDue}>{formatDueAt(reminder.dueAt)}</Text>
                  </View>
                  <Pressable
                    accessibilityRole="button"
                    disabled={busy !== null}
                    onPress={() => void run(`cancel-${reminder.id}`, async () => {
                      await controlApi.cancelReminder(reminder.id);
                      showNotice('Reminder cancelled.');
                      await refreshReminders();
                    })}>
                    <Text style={styles.cancelText}>Cancel</Text>
                  </Pressable>
                </View>
              ))}
            </View>
          </View>
          {Platform.OS !== 'web' && <Text style={styles.apiHint}>Backend: {apiBaseUrl}</Text>}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  scrollContent: { flexGrow: 1, backgroundColor: colors.background },
  shell: { width: '100%', maxWidth: 1120, alignSelf: 'center', paddingHorizontal: 20, paddingTop: 42, paddingBottom: 72 },
  hero: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24, marginBottom: 30 },
  heroCompact: { alignItems: 'flex-start', flexDirection: 'column' },
  heroCopy: { flex: 1 },
  eyebrow: { color: colors.mint, fontSize: 12, fontWeight: '800', letterSpacing: 2.2, marginBottom: 10 },
  title: { color: colors.text, fontSize: 58, lineHeight: 62, fontWeight: '900', letterSpacing: -3 },
  subtitle: { color: colors.muted, fontSize: 16, lineHeight: 24, marginTop: 12, maxWidth: 540 },
  connectionCard: { minWidth: 230, flexDirection: 'row', alignItems: 'center', gap: 13, paddingVertical: 14, paddingHorizontal: 18, borderWidth: 1, borderColor: colors.line, borderRadius: 999, backgroundColor: colors.panel },
  statusDot: { width: 11, height: 11, borderRadius: 6, backgroundColor: colors.amber },
  statusDotOnline: { backgroundColor: colors.mint },
  connectionTitle: { color: colors.text, fontSize: 14, fontWeight: '800' },
  connectionDetail: { color: colors.muted, fontSize: 11, marginTop: 2 },
  card: { borderWidth: 1, borderColor: colors.line, borderRadius: 22, backgroundColor: colors.panel, padding: 28 },
  buddyPanel: { flexDirection: 'row', alignItems: 'center', gap: 26, marginBottom: 20 },
  buddyPanelCompact: { gap: 18, paddingHorizontal: 20 },
  face: { width: 106, height: 106, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 15, borderWidth: 1, borderColor: '#30473d', borderRadius: 38, backgroundColor: '#101715' },
  faceCompact: { width: 82, height: 82, borderRadius: 28 },
  eye: { width: 18, height: 30, borderRadius: 12, backgroundColor: colors.mint },
  stateCopy: { flex: 1 },
  sectionLabel: { color: colors.mint, fontSize: 11, fontWeight: '800', letterSpacing: 1.8, marginBottom: 8 },
  stateTitle: { color: colors.text, fontSize: 48, lineHeight: 52, fontWeight: '900', letterSpacing: -2 },
  stateTitleCompact: { fontSize: 36, lineHeight: 40, letterSpacing: -1.5 },
  caption: { color: colors.muted, fontSize: 15, marginTop: 5 },
  notice: { marginBottom: 20, paddingVertical: 12, paddingHorizontal: 16, borderWidth: 1, borderColor: '#3c594b', borderRadius: 12, backgroundColor: colors.mintDark },
  noticeError: { borderColor: '#693b39', backgroundColor: '#321c1b' },
  noticeText: { color: colors.mint, fontWeight: '600' },
  noticeErrorText: { color: colors.danger },
  columns: { flexDirection: 'row', gap: 20, marginBottom: 20 },
  columnsCompact: { flexDirection: 'column' },
  column: { flex: 1, minWidth: 0 },
  cardHeading: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 },
  cardTitle: { color: colors.text, fontSize: 24, fontWeight: '800', letterSpacing: -0.7, marginBottom: 18 },
  badge: { color: colors.muted, backgroundColor: '#0f1514', fontSize: 12, paddingVertical: 7, paddingHorizontal: 11, borderRadius: 99, overflow: 'hidden' },
  count: { color: colors.mint, minWidth: 34, textAlign: 'center' },
  fieldLabel: { color: colors.muted, fontSize: 11, fontWeight: '700', letterSpacing: 0.6, marginBottom: 8 },
  input: { width: '100%', minHeight: 46, borderWidth: 1, borderColor: colors.line, borderRadius: 12, backgroundColor: colors.input, color: colors.text, fontSize: 15, paddingHorizontal: 13, paddingVertical: 10 },
  messageInput: { minHeight: 106, textAlignVertical: 'top', marginBottom: 12 },
  actionGap: { gap: 12, marginTop: 12 },
  button: { minHeight: 46, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18, borderRadius: 12 },
  buttonPrimary: { backgroundColor: colors.mint },
  buttonSecondary: { borderWidth: 1, borderColor: colors.line, backgroundColor: 'transparent' },
  buttonText: { color: '#0a2117', fontWeight: '900', fontSize: 14 },
  buttonSecondaryText: { color: colors.muted },
  buttonDisabled: { opacity: 0.42 },
  buttonPressed: { opacity: 0.82 },
  remindersCard: { marginBottom: 18 },
  reminderForm: { flexDirection: 'row', alignItems: 'flex-end', gap: 12, paddingBottom: 22, borderBottomWidth: 1, borderBottomColor: colors.line },
  reminderFormCompact: { flexDirection: 'column', alignItems: 'stretch' },
  reminderTextField: { flex: 2 },
  reminderDelayField: { flex: 1 },
  reminderButton: { minWidth: 142 },
  reminderList: { gap: 10, paddingTop: 18 },
  reminderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 18, paddingVertical: 14, paddingHorizontal: 16, borderRadius: 14, backgroundColor: '#101615' },
  reminderCopy: { flex: 1 },
  reminderTitle: { color: colors.text, fontSize: 15, fontWeight: '700' },
  reminderDue: { color: colors.muted, fontSize: 12, marginTop: 4 },
  cancelText: { color: colors.danger, fontSize: 14, fontWeight: '800', padding: 8 },
  empty: { color: colors.muted, textAlign: 'center', paddingVertical: 8 },
  apiHint: { color: '#65706b', fontSize: 11, textAlign: 'center' },
});
