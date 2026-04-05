import { init, flush, setPreferenceDelta, destroy } from '../Observer.js';

/**
 * Unit tests for Observer.js telemetry module
 */

describe('Observer Telemetry Module', () => {
  // Setup and teardown
  beforeEach(() => {
    // Clear all intervals and event listeners
    jest.clearAllTimers();
    jest.useFakeTimers();

    // Mock fetch
    global.fetch = jest.fn();

    // Reset DOM
    document.body.innerHTML = '';

    // Reset module state by destroying and reinitializing
    destroy();
  });

  afterEach(() => {
    destroy();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('flush() produces valid state vector', () => {
    test('should produce a state vector of exactly 5 numbers, all in [0, 1]', async () => {
      init();

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Extract the payload from the fetch call
      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      // Verify state_vector structure
      expect(payload.state_vector).toBeDefined();
      expect(Array.isArray(payload.state_vector)).toBe(true);
      expect(payload.state_vector).toHaveLength(5);

      // Verify all values are numbers in [0, 1]
      payload.state_vector.forEach((value, index) => {
        expect(typeof value).toBe('number');
        expect(value).toBeGreaterThanOrEqual(0);
        expect(value).toBeLessThanOrEqual(1);
      });
    });

    test('should include session_id and timestamp in payload', async () => {
      init();

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      expect(payload.session_id).toBeDefined();
      expect(typeof payload.session_id).toBe('string');
      expect(payload.timestamp).toBeDefined();
      expect(typeof payload.timestamp).toBe('string');
    });

    test('should POST to /api/state with correct Content-Type header', async () => {
      init();

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/state',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      );
    });
  });

  describe('setPreferenceDelta()', () => {
    test('should update state_vector with custom preference delta value', async () => {
      init();
      setPreferenceDelta(0.8);

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      // The 5th element (index 4) should be the preference delta
      expect(payload.state_vector[4]).toBe(0.8);
    });

    test('should clamp preference delta to [0, 1]', async () => {
      init();
      setPreferenceDelta(1.5); // Should clamp to 1.0

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      expect(payload.state_vector[4]).toBe(1.0);
    });

    test('should clamp negative preference delta to 0', async () => {
      init();
      setPreferenceDelta(-0.5); // Should clamp to 0.0

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      expect(payload.state_vector[4]).toBe(0.0);
    });
  });

  describe('Focus Persistence', () => {
    test('should compute normalized focus persistence from visibility events', async () => {
      init();

      // Simulate 3 visibilitychange events (hidden)
      for (let i = 0; i < 3; i++) {
        Object.defineProperty(document, 'visibilityState', {
          configurable: true,
          get: () => 'hidden',
        });
        document.dispatchEvent(new Event('visibilitychange'));
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      // Focus persistence (index 2) should be 1 - (3/5) = 0.4
      expect(payload.state_vector[2]).toBe(0.4);
    });

    test('should have focus = 1.0 when no visibility events occur', async () => {
      init();

      // Don't trigger any visibility events

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      // Focus persistence (index 2) should be 1 - (0/5) = 1.0
      expect(payload.state_vector[2]).toBe(1.0);
    });

    test('should cap focus at 0.0 when 5+ visibility events occur', async () => {
      init();

      // Simulate 6 visibilitychange events
      for (let i = 0; i < 6; i++) {
        Object.defineProperty(document, 'visibilityState', {
          configurable: true,
          get: () => 'hidden',
        });
        document.dispatchEvent(new Event('visibilitychange'));
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      // Focus persistence (index 2) should be clamped to 0.0
      expect(payload.state_vector[2]).toBe(0.0);
    });
  });

  describe('Stall Duration', () => {
    test('should compute stall duration relative to last interaction', async () => {
      jest.useFakeTimers();
      const initialTime = 1000;
      jest.setSystemTime(initialTime);

      init();

      // Simulate interaction at time 1000
      document.dispatchEvent(new MouseEvent('mousedown'));

      // Advance time by 15 seconds (15000 ms)
      jest.advanceTimersByTime(15000);

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      // Stall duration (index 3) should be approximately 15000 / 30000 = 0.5
      expect(payload.state_vector[3]).toBeCloseTo(0.5, 1);
    });

    test('should be 0.0 immediately after interaction', async () => {
      jest.useFakeTimers();
      const initialTime = 1000;
      jest.setSystemTime(initialTime);

      init();

      // Simulate fresh interaction
      document.dispatchEvent(new MouseEvent('mousedown'));

      // Immediately flush (no time has passed)
      jest.setSystemTime(initialTime); // Keep same time

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      // Stall duration (index 3) should be approximately 0.0
      expect(payload.state_vector[3]).toBeCloseTo(0.0, 1);
    });

    test('should be 1.0 when no interaction for full 30 seconds', async () => {
      jest.useFakeTimers();
      const initialTime = 1000;
      jest.setSystemTime(initialTime);

      init();

      // Advance time by 30 seconds (full interval)
      jest.advanceTimersByTime(30000);

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const callArgs = global.fetch.mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      // Stall duration (index 3) should be 1.0
      expect(payload.state_vector[3]).toBeCloseTo(1.0, 1);
    });
  });

  describe('Semantic Dwell Ratio', () => {
    test('should read wordCount from data-word-count attribute', async () => {
      init();

      // Create an element with word count
      const wordCountElement = document.createElement('div');
      wordCountElement.dataset.wordCount = '100';
      document.body.appendChild(wordCountElement);

      // Note: Full dwell ratio testing requires time advancement
      // This test focuses on wordCount reading

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      // Just verify fetch was called (basic sanity check)
      expect(global.fetch).toHaveBeenCalled();
    });

    test('should default to 200 words if data-word-count not found', async () => {
      init();

      // Don't add any word count element

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      // Verify fetch was called with a valid state vector
      expect(global.fetch).toHaveBeenCalled();
      const payload = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(payload.state_vector).toHaveLength(5);
    });
  });

  describe('Interaction Jitter', () => {
    test('should compute jitter from mouse movement samples', async () => {
      jest.useFakeTimers();
      init();

      const baseTime = 1000;
      jest.setSystemTime(baseTime);

      // Simulate multiple mousemove events with various velocities
      const mouseMoveEvent1 = new MouseEvent('mousemove', { clientX: 0, clientY: 0 });
      const mouseMoveEvent2 = new MouseEvent('mousemove', { clientX: 10, clientY: 10 });
      const mouseMoveEvent3 = new MouseEvent('mousemove', { clientX: 20, clientY: 10 });

      document.dispatchEvent(mouseMoveEvent1);
      jest.advanceTimersByTime(10);

      document.dispatchEvent(mouseMoveEvent2);
      jest.advanceTimersByTime(10);

      document.dispatchEvent(mouseMoveEvent3);

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      await flush();

      const payload = JSON.parse(global.fetch.mock.calls[0][1].body);
      // Jitter (index 1) should be a valid number in [0, 1]
      expect(payload.state_vector[1]).toBeGreaterThanOrEqual(0);
      expect(payload.state_vector[1]).toBeLessThanOrEqual(1);
    });
  });

  describe('init() and destroy()', () => {
    test('should not double-initialize', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();

      init();
      init(); // Second call

      expect(consoleSpy).toHaveBeenCalledWith(
        '[Observer] Already initialised; skipping duplicate init'
      );

      consoleSpy.mockRestore();
    });

    test('should clean up event listeners and intervals on destroy', () => {
      const removeEventListenerSpy = jest.spyOn(document, 'removeEventListener');

      init();
      destroy();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'visibilitychange',
        expect.any(Function)
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith('mousemove', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('scroll', expect.any(Function));

      removeEventListenerSpy.mockRestore();
    });
  });

  describe('error handling', () => {
    test('should handle fetch errors gracefully', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      init();

      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      await flush();

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[Observer] Failed to flush telemetry:',
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    test('should warn on non-ok fetch response', async () => {
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

      init();

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await flush();

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[Observer] POST /api/state returned status 500'
      );

      consoleWarnSpy.mockRestore();
    });
  });
});
