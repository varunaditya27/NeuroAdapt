import { useEffect, useRef } from 'react';

/**
 * Custom hook to trap focus within a modal or dialog element.
 * @param {React.RefObject} containerRef - Ref to the container element to trap focus within
 * @param {boolean} isActive - Whether focus trapping is active (default: true)
 */
export function useFocusTrap(containerRef, isActive = true) {
  const previousActiveElementRef = useRef(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    // Store the previously focused element so we can restore it on unmount
    previousActiveElementRef.current = document.activeElement;

    const container = containerRef.current;

    // Get all focusable elements within the container
    const getFocusableElements = () => {
      const selector = [
        'a[href]',
        'button:not([disabled])',
        'textarea:not([disabled])',
        'input:not([disabled])',
        'select:not([disabled])',
        '[tabindex]:not([tabindex="-1"])',
      ].join(',');

      return Array.from(container.querySelectorAll(selector));
    };

    // Handle Tab key to trap focus
    const handleKeyDown = (e) => {
      if (e.key !== 'Tab') return;

      const focusableElements = getFocusableElements();
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      // Shift + Tab on first element → focus last
      if (e.shiftKey && activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      }
      // Tab on last element → focus first
      else if (!e.shiftKey && activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    // Focus the first focusable element on mount
    const focusableElements = getFocusableElements();
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      // Restore focus to the previously focused element
      if (previousActiveElementRef.current && previousActiveElementRef.current.focus) {
        previousActiveElementRef.current.focus();
      }
    };
  }, [isActive, containerRef]);
}
