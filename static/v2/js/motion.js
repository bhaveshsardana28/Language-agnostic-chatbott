import { reducedMotion } from './preferences.js';

const active = new Set();
document.addEventListener('visibilitychange', () => {
  // Finish short UI transitions; the CSS ambient loops pause while hidden.
  if (document.hidden) active.forEach(animation => animation.finish());
});

export function tokenNumber(name, element = document.documentElement) {
  return parseFloat(getComputedStyle(element).getPropertyValue(name));
}

export function tokenTime(name) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return parseFloat(value) * (value.endsWith('ms') ? 1 : 1000);
}

export async function animate(element, frames, duration = '--motion-ui', easing = '--ease-enter') {
  if (reducedMotion() || document.hidden || typeof element.animate !== 'function') return;
  const animation = element.animate(frames, {
    duration: tokenTime(duration),
    easing: getComputedStyle(document.documentElement).getPropertyValue(easing).trim(),
  });
  active.add(animation);
  try { await animation.finished; } catch { /* Preference change/cancellation: state still completes. */ }
  finally { active.delete(animation); }
}

export function springFrames() {
  const mass = tokenNumber('--spring-mass');
  const stiffness = tokenNumber('--spring-stiffness');
  const damping = tokenNumber('--spring-damping');
  const omega = Math.sqrt(stiffness / mass);
  const zeta = damping / (2 * Math.sqrt(stiffness * mass));
  const damped = omega * Math.sqrt(1 - zeta * zeta);
  const response = time => 1 - Math.exp(-zeta * omega * time) *
    (Math.cos(damped * time) + zeta * omega / damped * Math.sin(damped * time));
  const seconds = tokenTime('--motion-panel') / 1000;
  const end = response(seconds);
  // 25 sampled keyframes of the tokenized physical spring, not a claimed CSS spring.
  return Array.from({ length: 25 }, (_, index) => {
    const offset = index / 24;
    const progress = response(seconds * offset) / end;
    return { offset, transform: `translateX(${(progress - 1) * 100}%)`, opacity: Math.min(offset * 4, 1) };
  });
}
