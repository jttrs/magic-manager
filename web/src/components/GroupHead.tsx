import type { ReactNode } from 'react';

type Props = {
  /** The group's name (condensed uppercase). */
  label: ReactNode;
  /** Right-aligned tabular detail: a count, `12 recipes · 3 ready`, … */
  meta?: ReactNode;
  /** `accent` marks a group that needs attention (Purchase history's *Needs review*). */
  tone?: 'muted' | 'accent';
  as?: 'h2' | 'h3';
  id?: string;
  /** Stick to the top of the scroll region (default). */
  sticky?: boolean;
};

/**
 * The ruled head of a group in a scrolling list. Its paper band runs to the edges
 * of the list's `px-sheet` scroll region (so rows scroll under it with no visible box
 * edge), and its text sits in from that edge, aligned with the rows' content.
 */
export function GroupHead({ label, meta, tone = 'muted', as: Tag = 'h2', id, sticky = true }: Props) {
  return (
    <Tag
      id={id}
      className={`${sticky ? 'sticky top-0 z-10' : ''} -mx-sheet flex items-baseline gap-2 border-b bg-paper px-sheet pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-caps ${
        tone === 'accent' ? 'border-rule-strong text-accent-ink' : 'border-rule text-ink-muted'
      }`}
    >
      <span className="min-w-0 truncate">{label}</span>
      {meta != null && meta !== '' && <span className="ml-auto shrink-0 tabular normal-case tracking-normal text-ink-muted">{meta}</span>}
    </Tag>
  );
}
