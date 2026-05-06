'use client';

import { useState, useEffect, useRef } from 'react';
import EnergyBar from '@/components/EnergyBar';
import PreferenceDelta from '@/components/PreferenceDelta';
import {
  init as initObserver,
  destroy as destroyObserver,
  flush as flushObserver,
  getLastStateVector,
  setPreferenceDelta,
} from '@/components/Observer';
import { LESSON_CATALOGUE } from '@/data/lessonCatalogue';
import { computePreferenceDelta } from '@/utils/preferenceDeltaCalculator';

export default function Home() {
  const [view, setView] = useState('subjects'); // subjects | topics | lesson
  const [selectedSubjectId, setSelectedSubjectId] = useState(null);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [showPreferenceDelta, setShowPreferenceDelta] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState('text');
  const [adaptiveContent, setAdaptiveContent] = useState(null);
  const [adaptiveLoading, setAdaptiveLoading] = useState(false);
  const [adaptiveError, setAdaptiveError] = useState(null);
  const [lastAction, setLastAction] = useState(null);
  const sessionIdRef = useRef(null);

  // Initialize Observer on mount
  useEffect(() => {
    // Generate or retrieve session ID
    const existingSessionId = sessionStorage.getItem('neuroAdapt_sessionId');
    if (existingSessionId) {
      sessionIdRef.current = existingSessionId;
    } else {
      // Generate new session ID (UUID-like format)
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('neuroAdapt_sessionId', newSessionId);
      sessionIdRef.current = newSessionId;
    }

    // Initialize Observer telemetry
    initObserver();

    return () => {
      // Cleanup Observer on unmount
      destroyObserver();
    };
  }, []);

  const selectedSubject = selectedSubjectId
    ? LESSON_CATALOGUE.find((s) => s.subjectId === selectedSubjectId)
    : null;

  const currentSlides = selectedTopic ? selectedTopic.lessonContent.slides : [];
  const currentSlide = currentSlides[currentSlideIndex] || null;

  const isFirstSlide = currentSlideIndex === 0;
  const isLastSlide = currentSlideIndex === currentSlides.length - 1;

  const handleSelectSubject = (subjectId) => {
    setSelectedSubjectId(subjectId);
    setView('topics');
    setShowModal(false);
  };

  const handleSelectTopic = (topic) => {
    setSelectedTopic(topic);
    setCurrentSlideIndex(0);
    setView('lesson');
  };

  const handleBackToSubjects = () => {
    setView('subjects');
    setSelectedSubjectId(null);
    setSelectedTopic(null);
    setCurrentSlideIndex(0);
  };

  const handleBackToTopics = () => {
    setView('topics');
    setSelectedTopic(null);
    setCurrentSlideIndex(0);
  };

  const handlePrevious = () => {
    if (!isFirstSlide) {
      setCurrentSlideIndex(currentSlideIndex - 1);
    }
  };

  const handleNext = () => {
    if (!isLastSlide) {
      setCurrentSlideIndex(currentSlideIndex + 1);
    }
  };

  /**
   * Handle format selection from PreferenceDelta modal
   * Calculates dynamic preference delta based on model prediction vs user choice
   */
  const handleFormatSelect = async (format) => {
    setSelectedFormat(format);
    
    try {
      // Compute preference delta based on model prediction vs user selection
      // Pass current format as fallback for when API state isn't available yet
      const dynamicPreferenceDelta = await computePreferenceDelta(
        sessionIdRef.current,
        format,
        selectedFormat // current format before update
      );

      // Update Observer with the calculated preference delta
      setPreferenceDelta(dynamicPreferenceDelta);
      await postFeedback('format_choice', format);

      console.log('[Home] Format selected and preference delta updated:', {
        previousFormat: selectedFormat,
        newFormat: format,
        preferenceDelta: dynamicPreferenceDelta,
      });
    } catch (error) {
      console.error('[Home] Error updating preference delta:', error);
      // Fallback: use neutral preference delta on error
      setPreferenceDelta(0.5);
      await postFeedback('format_choice', format);
    }
  };

  const progress = selectedTopic
    ? Math.round(((currentSlideIndex + 1) / currentSlides.length) * 100)
    : 0;

  useEffect(() => {
    if (view !== 'lesson' || !currentSlide || !sessionIdRef.current) {
      setAdaptiveContent(null);
      return;
    }

    let cancelled = false;

    const runAdaptiveCycle = async () => {
      setAdaptiveLoading(true);
      setAdaptiveError(null);

      try {
        await flushObserver();

        const actionResponse = await fetch(
          `/api/action?session_id=${encodeURIComponent(sessionIdRef.current)}`,
          { cache: 'no-store' }
        );
        if (!actionResponse.ok) {
          throw new Error(`Action request failed (${actionResponse.status})`);
        }

        const action = await actionResponse.json();
        if (cancelled) return;
        setLastAction(action);

        if (action.gated || action.action_id === 0) {
          setAdaptiveContent(null);
          return;
        }

        const generateResponse = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_id: action.action_id,
            slide_content: `${currentSlide.heading}\n\n${currentSlide.body}`,
            learner_level: 'grade8',
            session_id: sessionIdRef.current,
            confidence: action.confidence,
          }),
        });

        if (generateResponse.status === 204) {
          setAdaptiveContent(null);
          return;
        }
        if (!generateResponse.ok) {
          throw new Error(`Generation request failed (${generateResponse.status})`);
        }

        const generated = await generateResponse.json();
        if (!cancelled) {
          setAdaptiveContent(generated);
        }
      } catch (error) {
        if (!cancelled) {
          setAdaptiveError(error instanceof Error ? error.message : String(error));
          setAdaptiveContent(null);
        }
      } finally {
        if (!cancelled) {
          setAdaptiveLoading(false);
        }
      }
    };

    runAdaptiveCycle();
    const timer = setInterval(runAdaptiveCycle, 30000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [view, currentSlideIndex, currentSlide]);

  const postFeedback = async (event, chosenFormat = null) => {
    if (!sessionIdRef.current) return;

    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          event,
          chosen_format: chosenFormat,
          current_state: getLastStateVector() || [0.5, 0.5, 0.5, 0.5, 0.5],
          action_taken: lastAction?.action_id ?? 0,
        }),
      });
    } catch (error) {
      console.warn('[Home] feedback post failed:', error);
    }
  };

  const renderAdaptiveContent = () => {
    if (!adaptiveContent?.content) return null;

    const { action_id: actionId, content } = adaptiveContent;
    if (actionId === 4 && Array.isArray(content.quiz_json)) {
      return (
        <div style={{ marginTop: '32px', padding: '20px', border: '1px solid var(--border)', borderRadius: '8px' }}>
          <h2 style={{ color: 'var(--navy)', fontSize: '20px', marginBottom: '16px' }}>Quick Check</h2>
          {content.quiz_json.map((question) => (
            <div key={question.id} style={{ marginBottom: '18px' }}>
              <p style={{ fontWeight: 600, marginBottom: '8px' }}>{question.text}</p>
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                {question.options.map((option, index) => (
                  <li key={option} style={{ marginBottom: '4px' }}>
                    {option}{index === question.correct_index ? ' ✓' : ''}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      );
    }

    if (actionId === 5) {
      return (
        <div style={{ marginTop: '32px', padding: '20px', border: '1px solid var(--teal)', borderRadius: '8px' }}>
          <h2 style={{ color: 'var(--navy)', fontSize: '20px', marginBottom: '12px' }}>{content.title || 'Sensory Reset'}</h2>
          <p style={{ lineHeight: 1.7 }}>{content.break_template}</p>
        </div>
      );
    }

    if (content.video_url || content.image_url || content.audio_url) {
      return (
        <div style={{ marginTop: '32px' }}>
          {content.video_url && <video src={content.video_url} controls style={{ width: '100%', borderRadius: '8px' }} />}
          {content.image_url && <img src={content.image_url} alt="Generated lesson visual" style={{ width: '100%', borderRadius: '8px' }} />}
          {content.audio_url && <audio src={content.audio_url} controls style={{ width: '100%', marginTop: '12px' }} />}
          {content.simplified_text && <p style={{ marginTop: '16px', lineHeight: 1.7 }}>{content.simplified_text}</p>}
        </div>
      );
    }

    if (content.simplified_text) {
      return (
        <div style={{ marginTop: '32px', padding: '20px', border: '1px solid var(--border)', borderRadius: '8px' }}>
          <h2 style={{ color: 'var(--navy)', fontSize: '20px', marginBottom: '12px' }}>Adapted Version</h2>
          <p style={{ lineHeight: 1.7 }}>{content.simplified_text}</p>
        </div>
      );
    }

    return null;
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', paddingTop: '56px' }}>
      {/* Sidebar */}
      <aside
        style={{
          width: '260px',
          position: 'fixed',
          left: 0,
          top: '56px',
          height: 'calc(100vh - 56px)',
          backgroundColor: 'var(--surface)',
          borderRight: '1px solid var(--border)',
          padding: '24px 0',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ flex: 1, paddingLeft: '20px', paddingRight: '16px' }}>
          {/* Back buttons */}
          {view === 'topics' && (
            <button
              type="button"
              onClick={handleBackToSubjects}
              style={{
                padding: '8px 0',
                marginBottom: '20px',
                color: 'var(--teal)',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                backgroundColor: 'transparent',
                border: 'none',
                textAlign: 'left',
                pointerEvents: 'auto',
              }}
            >
              ← Back to Subjects
            </button>
          )}

          {view === 'lesson' && (
            <button
              type="button"
              onClick={handleBackToTopics}
              style={{
                padding: '8px 0',
                marginBottom: '20px',
                color: 'var(--teal)',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                backgroundColor: 'transparent',
                border: 'none',
                textAlign: 'left',
                pointerEvents: 'auto',
              }}
            >
              ← Back to Topics
            </button>
          )}

          {/* Sidebar title */}
          <div
            style={{
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.08em',
              color: 'var(--muted)',
              marginBottom: '16px',
              textTransform: 'uppercase',
            }}
          >
            {view === 'subjects' && 'Subjects'}
            {view === 'topics' && 'Topics'}
            {view === 'lesson' && 'Slides'}
          </div>

          {/* Subjects list */}
          {view === 'subjects' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {LESSON_CATALOGUE.map((subject) => (
                <button
                  key={subject.subjectId}
                  type="button"
                  onClick={() => handleSelectSubject(subject.subjectId)}
                  style={{
                    padding: '10px 12px',
                    color: 'var(--navy)',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    backgroundColor: 'transparent',
                    border: 'none',
                    textAlign: 'left',
                    pointerEvents: 'auto',
                    transition: 'all 200ms ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = 'var(--teal)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--navy)';
                  }}
                >
                  {subject.subject}
                </button>
              ))}
            </div>
          )}

          {/* Topics list */}
          {view === 'topics' && selectedSubject && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {selectedSubject.topics.map((topic) => (
                <button
                  key={topic.topicId}
                  type="button"
                  onClick={() => handleSelectTopic(topic)}
                  style={{
                    padding: '10px 12px',
                    color: 'var(--navy)',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    backgroundColor: 'rgba(0, 150, 136, 0.15)',
                    border: 'none',
                    borderRadius: '4px',
                    textAlign: 'left',
                    pointerEvents: 'auto',
                      transition: 'all 200ms ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = 'var(--teal)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = 'var(--navy)';
                    }}
                  >
                    {topic.title}
                  </button>
                ))}
            </div>
          )}

          {/* Slides list */}
          {view === 'lesson' && currentSlides && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {currentSlides.map((_, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setCurrentSlideIndex(idx)}
                  style={{
                    padding: '10px 12px',
                    borderLeft:
                      currentSlideIndex === idx ? '3px solid var(--teal)' : '3px solid transparent',
                    paddingLeft: currentSlideIndex === idx ? '9px' : '12px',
                    color: currentSlideIndex === idx ? 'var(--navy)' : 'var(--muted)',
                    fontSize: '13px',
                    fontWeight: currentSlideIndex === idx ? 500 : 400,
                    cursor: 'pointer',
                    backgroundColor: 'transparent',
                    border: 'none',
                    textAlign: 'left',
                    pointerEvents: 'auto',
                    transition: 'all 200ms ease',
                  }}
                  onMouseEnter={(e) => {
                    if (currentSlideIndex !== idx) {
                      e.currentTarget.style.color = 'var(--navy)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (currentSlideIndex !== idx) {
                      e.currentTarget.style.color = 'var(--muted)';
                    }
                  }}
                >
                  Slide {idx + 1}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Study Mode Button */}
        <div
          style={{
            borderTop: '1px solid var(--border)',
            padding: '16px 20px',
            marginTop: 'auto',
          }}
        >
          <button
            type="button"
            onClick={() => setShowPreferenceDelta(true)}
            style={{
              width: '100%',
              padding: '10px 12px',
              backgroundColor: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--navy)',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 200ms ease',
              pointerEvents: 'auto',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(0, 150, 136, 0.1)';
              e.currentTarget.style.borderColor = 'var(--teal)';
              e.currentTarget.style.color = 'var(--teal)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = 'var(--border)';
              e.currentTarget.style.color = 'var(--navy)';
            }}
          >
            ◐ Study Mode
          </button>
          <div
            style={{
              fontSize: '12px',
              color: 'var(--muted)',
              marginTop: '8px',
              textAlign: 'center',
            }}
          >
            {selectedFormat}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main
        style={{
          marginLeft: '260px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Progress Bar */}
        {view === 'lesson' && (
          <div
            style={{
              height: '4px',
              backgroundColor: 'var(--border)',
              position: 'sticky',
              top: '56px',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${progress}%`,
                backgroundColor: 'var(--teal)',
                transition: 'width 300ms ease',
              }}
            />
          </div>
        )}

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '48px 0' }}>
          {view === 'subjects' && (
            <div
              style={{
                maxWidth: '900px',
                margin: '0 auto',
                paddingLeft: '48px',
                paddingRight: '48px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                textAlign: 'center',
              }}
            >
              <p
                style={{
                  fontSize: '18px',
                  lineHeight: '1.8',
                  color: 'var(--text)',
                  marginBottom: '48px',
                  maxWidth: '700px',
                }}
              >
                <span style={{ fontSize: '24px', fontWeight: 600, color: 'var(--navy)', display: 'block', marginBottom: '16px' }}>
                  Hello & Welcome
                </span>
                NeuroAdapt is an adaptive learning platform designed to personalize your educational journey. 
                Our intelligent system learns your learning style and pace, adjusting content in real-time to keep 
                you engaged and maximizing your understanding. Start your lesson today by selecting a subject that interests you.
              </p>
              <button
                type="button"
                onClick={() => setShowModal(true)}
                style={{
                  padding: '14px 32px',
                  border: 'none',
                  backgroundColor: 'var(--teal)',
                  color: 'white',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 200ms ease',
                  pointerEvents: 'auto',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.opacity = '0.9';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.opacity = '1';
                }}
              >
                Begin Lesson
              </button>

              {/* Key Features Section */}
              <div
                style={{
                  marginTop: '96px',
                  paddingTop: '64px',
                  borderTop: '1px solid var(--border)',
                  width: '100%',
                }}
              >
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                    gap: '32px',
                    maxWidth: '1000px',
                    margin: '0 auto',
                  }}
                >
                  {/* Feature 1 */}
                  <div
                    style={{
                      padding: '32px 24px',
                      border: '1px solid var(--border)',
                      borderRadius: '12px',
                      backgroundColor: 'rgba(0, 150, 136, 0.05)',
                      textAlign: 'center',
                      transition: 'all 200ms ease',
                      cursor: 'default',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(0, 150, 136, 0.15)';
                      e.currentTarget.style.borderColor = 'var(--teal)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'none';
                      e.currentTarget.style.borderColor = 'var(--border)';
                    }}
                  >
                    <svg
                      width="40"
                      height="40"
                      viewBox="0 0 40 40"
                      fill="none"
                      stroke="var(--teal)"
                      strokeWidth="2"
                      style={{ margin: '0 auto 16px', display: 'block' }}
                    >
                      <circle cx="20" cy="20" r="16" />
                      <path d="M20 8v24M8 20h24" strokeLinecap="round" />
                      <circle cx="20" cy="20" r="3" fill="var(--teal)" />
                    </svg>
                    <h3
                      style={{
                        fontSize: '18px',
                        fontWeight: 600,
                        color: 'var(--navy)',
                        marginBottom: '12px',
                      }}
                    >
                      Adaptive Learning
                    </h3>
                    <p
                      style={{
                        fontSize: '14px',
                        color: 'var(--text)',
                        lineHeight: '1.6',
                      }}
                    >
                      Content dynamically adjusts to your learning pace and style, keeping you engaged and challenged.
                    </p>
                  </div>

                  {/* Feature 2 */}
                  <div
                    style={{
                      padding: '32px 24px',
                      border: '1px solid var(--border)',
                      borderRadius: '12px',
                      backgroundColor: 'rgba(0, 150, 136, 0.05)',
                      textAlign: 'center',
                      transition: 'all 200ms ease',
                      cursor: 'default',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(0, 150, 136, 0.15)';
                      e.currentTarget.style.borderColor = 'var(--teal)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'none';
                      e.currentTarget.style.borderColor = 'var(--border)';
                    }}
                  >
                    <svg
                      width="40"
                      height="40"
                      viewBox="0 0 40 40"
                      fill="none"
                      stroke="var(--teal)"
                      strokeWidth="2"
                      style={{ margin: '0 auto 16px', display: 'block' }}
                    >
                      <rect x="6" y="8" width="28" height="24" rx="2" />
                      <circle cx="20" cy="20" r="6" />
                      <path d="M14 20h-2M28 20h2M20 14v-2M20 28v2" strokeLinecap="round" />
                    </svg>
                    <h3
                      style={{
                        fontSize: '18px',
                        fontWeight: 600,
                        color: 'var(--navy)',
                        marginBottom: '12px',
                      }}
                    >
                      Personalized Support
                    </h3>
                    <p
                      style={{
                        fontSize: '14px',
                        color: 'var(--text)',
                        lineHeight: '1.6',
                      }}
                    >
                      Multiple teaching modalities and interventions tailored to your preferences and needs.
                    </p>
                  </div>

                  {/* Feature 3 */}
                  <div
                    style={{
                      padding: '32px 24px',
                      border: '1px solid var(--border)',
                      borderRadius: '12px',
                      backgroundColor: 'rgba(0, 150, 136, 0.05)',
                      textAlign: 'center',
                      transition: 'all 200ms ease',
                      cursor: 'default',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(0, 150, 136, 0.15)';
                      e.currentTarget.style.borderColor = 'var(--teal)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'none';
                      e.currentTarget.style.borderColor = 'var(--border)';
                    }}
                  >
                    <svg
                      width="40"
                      height="40"
                      viewBox="0 0 40 40"
                      fill="none"
                      stroke="var(--teal)"
                      strokeWidth="2"
                      style={{ margin: '0 auto 16px', display: 'block' }}
                    >
                      <path d="M20 4c-6 0-10 5-10 10 0 8 10 18 10 18s10-10 10-18c0-5-4-10-10-10z" />
                      <circle cx="20" cy="14" r="3" fill="var(--teal)" />
                    </svg>
                    <h3
                      style={{
                        fontSize: '18px',
                        fontWeight: 600,
                        color: 'var(--navy)',
                        marginBottom: '12px',
                      }}
                    >
                      Built for Everyone
                    </h3>
                    <p
                      style={{
                        fontSize: '14px',
                        color: 'var(--text)',
                        lineHeight: '1.6',
                      }}
                    >
                      Designed to work for all learners with special attention to supporting neurodivergent students.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {view === 'topics' && selectedSubject && (
            <div
              style={{
                maxWidth: '680px',
                margin: '0 auto',
                paddingLeft: '48px',
                paddingRight: '48px',
              }}
            >
              <h1
                style={{
                  fontFamily: "'DM Serif Display', serif",
                  fontSize: '36px',
                  fontWeight: 400,
                  color: 'var(--navy)',
                  marginBottom: '48px',
                }}
              >
                {selectedSubject.subject}
              </h1>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {selectedSubject.topics.map((topic) => (
                  <div
                    key={topic.topicId}
                    style={{
                      padding: '24px',
                      border: '1px solid var(--border)',
                      borderRadius: '8px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'all 200ms ease',
                      backgroundColor: 'rgba(0, 150, 136, 0.12)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontSize: '16px',
                          fontWeight: 600,
                          color: 'var(--navy)',
                          marginBottom: '8px',
                        }}
                      >
                        {topic.title}
                      </div>
                      <div
                        style={{
                          fontSize: '13px',
                          color: 'var(--muted)',
                        }}
                      >
                        {topic.duration}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSelectTopic(topic)}
                      style={{
                        padding: '8px 20px',
                        border: 'none',
                        backgroundColor: 'var(--teal)',
                        color: 'white',
                        borderRadius: '8px',
                        fontSize: '13px',
                        fontWeight: 500,
                        cursor: 'pointer',
                        transition: 'all 200ms ease',
                        pointerEvents: 'auto',
                        whiteSpace: 'nowrap',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.opacity = '0.9';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.opacity = '1';
                      }}
                    >
                      Start Lesson
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {view === 'lesson' && currentSlide && (
            <div
              style={{
                maxWidth: '680px',
                margin: '0 auto',
                paddingLeft: '48px',
                paddingRight: '48px',
              }}
            >
              <h1
                style={{
                  fontFamily: "'DM Serif Display', serif",
                  fontSize: '32px',
                  fontWeight: 400,
                  color: 'var(--navy)',
                  marginBottom: '24px',
                }}
              >
                {currentSlide.heading}
              </h1>

              <p
                style={{
                  fontSize: '17px',
                  lineHeight: '1.75',
                  color: 'var(--text)',
                  marginBottom: '48px',
                }}
              >
                {currentSlide.body}
              </p>

              {adaptiveLoading && (
                <p style={{ color: 'var(--muted)', fontSize: '14px' }}>Adapting this slide…</p>
              )}
              {adaptiveError && (
                <p style={{ color: '#B91C1C', fontSize: '14px' }}>{adaptiveError}</p>
              )}
              {renderAdaptiveContent()}

              {/* Navigation Buttons */}
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '48px' }}>
                {!isFirstSlide && (
                  <button
                    type="button"
                    onClick={handlePrevious}
                    style={{
                      padding: '10px 20px',
                      border: '1px solid var(--navy)',
                      backgroundColor: 'transparent',
                      color: 'var(--navy)',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      transition: 'all 200ms ease',
                      pointerEvents: 'auto',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'rgba(27, 42, 74, 0.05)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    ← Previous
                  </button>
                )}
                {!isLastSlide && (
                  <button
                    type="button"
                    onClick={handleNext}
                    style={{
                      padding: '10px 20px',
                      border: 'none',
                      backgroundColor: 'var(--teal)',
                      color: 'white',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      transition: 'all 200ms ease',
                      pointerEvents: 'auto',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.opacity = '0.9';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.opacity = '1';
                    }}
                  >
                    Next →
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Modal */}
      {showModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            pointerEvents: 'auto',
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{
              backgroundColor: 'var(--surface)',
              borderRadius: '12px',
              padding: '48px',
              maxWidth: '600px',
              width: '90%',
              maxHeight: '90vh',
              overflow: 'auto',
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
              pointerEvents: 'auto',
              marginLeft: '130px',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2
              style={{
                fontFamily: "'DM Serif Display', serif",
                fontSize: '36px',
                fontWeight: 400,
                color: 'var(--navy)',
                marginBottom: '40px',
                textAlign: 'center',
              }}
            >
              Select a Subject
            </h2>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                marginBottom: '32px',
              }}
            >
              {LESSON_CATALOGUE.map((subject) => (
                <button
                  key={subject.subjectId}
                  type="button"
                  onClick={() => handleSelectSubject(subject.subjectId)}
                  style={{
                    padding: '20px 24px',
                    border: '2px solid var(--border)',
                    backgroundColor: 'transparent',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 200ms ease',
                    textAlign: 'left',
                    pointerEvents: 'auto',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--border)';
                    e.currentTarget.style.borderColor = 'var(--teal)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  <div
                    style={{
                      fontSize: '18px',
                      fontWeight: 600,
                      color: 'var(--navy)',
                    }}
                  >
                    {subject.subject}
                  </div>
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setShowModal(false)}
              style={{
                padding: '12px 24px',
                border: '1px solid var(--border)',
                backgroundColor: 'transparent',
                color: 'var(--navy)',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 200ms ease',
                pointerEvents: 'auto',
                width: '100%',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(27, 42, 74, 0.05)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* PreferenceDelta Modal */}
      <PreferenceDelta
        open={showPreferenceDelta}
        onSelect={handleFormatSelect}
        onClose={() => setShowPreferenceDelta(false)}
      />

      {/* EnergyBar */}
      <EnergyBar
        onBreakRequest={() => {
          console.log('Break requested');
          postFeedback('energy_bar');
        }}
        onBreakEnd={() => {
          console.log('Break ended');
        }}
        breakDuration={60}
      />
    </div>
  );
}
