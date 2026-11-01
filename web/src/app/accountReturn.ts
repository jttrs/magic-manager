// "Sign in again" before deleting an account leaves the page for the provider; this
// tab-scoped mark reopens Settings → Delete account when the person comes back.
const KEY = 'mm.account.reauth';

function store(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function markAccountReturn(): void {
  store()?.setItem(KEY, '1');
}

/** Coming back from re-auth? (Doesn't clear: Settings opens, then the dialog takes it.) */
export function peekAccountReturn(): boolean {
  return store()?.getItem(KEY) === '1';
}

/** Coming back from re-auth? Clears the mark. */
export function takeAccountReturn(): boolean {
  const s = store();
  const back = s?.getItem(KEY) === '1';
  s?.removeItem(KEY);
  return back;
}
