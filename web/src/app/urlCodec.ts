// Short URL lists: TanStack Router writes every array as JSON (`["dft","tla"]`, percent-encoded),
// which made a few chosen families a wall of `%22%2C`. Arrays of plain tokens go out as a comma
// list instead (`dft,tla`); `core/search.ts list()` reads both forms, so old links keep working.
// Anything that wouldn't round-trip (a comma or quote in an item, a lone item that reads as JSON)
// keeps the JSON form.
import { parseSearchWith, stringifySearchWith } from '@tanstack/react-router';

const TOKEN = /^[^,"[\]{}]+$/;
/** A lone item JSON.parse would turn into a number/boolean/null (`123`, `true`). */
const jsonish = (v: string) => {
  try {
    return typeof JSON.parse(v) !== 'string';
  } catch {
    return false;
  }
};

function stringifyValue(value: unknown): string {
  if (Array.isArray(value) && value.length > 0 && value.every((v) => typeof v === 'string' && TOKEN.test(v))) {
    if (value.length > 1 || !jsonish(value[0] as string)) return value.join(',');
  }
  return JSON.stringify(value);
}

// JSON.parse as the parser keeps strings symmetric: a string that reads as JSON (`123`) is quoted.
export const stringifySearch = stringifySearchWith(stringifyValue, JSON.parse);
export const parseSearch = parseSearchWith(JSON.parse);
