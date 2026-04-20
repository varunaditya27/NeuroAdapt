/**
 * Simple className utility to conditionally join classNames
 * @param  {...any} classes - Classes to join (strings, objects, arrays, or falsy values)
 * @returns {string} Joined className string
 */
export function cn(...classes) {
  return classes
    .flat()
    .filter((c) => typeof c === 'string' && c.trim().length > 0)
    .join(' ');
}
