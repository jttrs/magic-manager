import type { ComponentProps, ComponentType, SVGProps } from 'react';

type Props = ComponentProps<'button'> & { Icon: ComponentType<SVGProps<SVGSVGElement>>; label: string };

/** A labelled ghost action on paper (a sheet's main action, e.g. "Add cards"):
 *  amber-ink mark + words, a quiet sunk fill on hover/focus/open — no lift, no
 *  underline. The icon-only sibling is IconAction; both share this hover. */
export function GhostAction({ Icon, label, className = '', ...rest }: Props) {
  return (
    <button
      type="button"
      {...rest}
      className={`inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-sm px-2 text-md voice-semi font-medium text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk data-[state=open]:bg-paper-sunk ${className}`}
    >
      <Icon className="size-5" />
      {label}
    </button>
  );
}
