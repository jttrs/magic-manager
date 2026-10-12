// The Settings dialog (header gear) is ONE surface for preferences. The shell
// owns Appearance, Privacy and About; any view can add its own section while
// it is mounted:
//
//   const section = useMemo(() => ({
//     id: 'collection',
//     title: 'Collection',
//     content: <SettingsRow label="Missing means" …><SettingsChoice … /></SettingsRow>,
//   }), [deps]);
//   useSettingsSection(section);
//
// Sections render between Appearance and Privacy, ordered by `order` (default
// 50) then title. A section disappears when its view unmounts, so view-scoped
// settings only show where they apply. Build the content from the controls in
// `components/settings/SettingsControls.tsx` so every section looks the same;
// memoize the section object so it re-registers only when its content changes.
import { useEffect, useSyncExternalStore, type ReactNode } from 'react';

export type SettingsSection = {
  /** Stable key; registering the same id again replaces the section. */
  id: string;
  /** Section heading in the dialog. */
  title: string;
  /** Lower sorts first; Appearance is 0. Default 50. */
  order?: number;
  content: ReactNode;
};

const sections = new Map<string, SettingsSection>();
const listeners = new Set<() => void>();
let snapshot: SettingsSection[] = [];

function emit() {
  snapshot = [...sections.values()].sort((a, b) => (a.order ?? 50) - (b.order ?? 50) || a.title.localeCompare(b.title));
  for (const l of listeners) l();
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => { listeners.delete(l); };
}

/** Adds `section` to the Settings dialog while the calling component is mounted. */
export function useSettingsSection(section: SettingsSection | null): void {
  useEffect(() => {
    if (!section) return;
    sections.set(section.id, section);
    emit();
    return () => {
      if (sections.get(section.id) === section) {
        sections.delete(section.id);
        emit();
      }
    };
  }, [section]);
}

/** Every registered section, in display order (for the dialog). */
export function useSettingsSections(): SettingsSection[] {
  return useSyncExternalStore(subscribe, () => snapshot);
}
