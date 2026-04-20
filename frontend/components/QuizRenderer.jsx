'use client';

import { useState, useEffect, useCallback } from 'react';
import { QUIZ_RESULT_MESSAGES } from '@/utils/constants';

/**
 * QuizRenderer Component
 * One-question-at-a-time quiz with multiple choice options and results screen
 */
export default function QuizRenderer({
  content = {},
  onQuizComplete = () => {},
}) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedOptionIndex, setSelectedOptionIndex] = useState(null);
  const [answered, setAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [showResults, setShowResults] = useState(false);

  const questions = content.questions || [];
  const title = content.title || 'Quiz';
  const isLastQuestion = currentQuestionIndex === questions.length - 1;
  const totalQuestions = questions.length;

  // Define handlers with useCallback to avoid re-creating on each render
  const currentQuestion = questions[currentQuestionIndex] || {};
  
  const handleAnswer = useCallback(
    (optionIndex) => {
      const isCorrect = optionIndex === currentQuestion.correct;
      if (isCorrect) {
        setScore((prev) => prev + 1);
      }
      setSelectedOptionIndex(optionIndex);
      setAnswered(true);
    },
    [currentQuestion.correct]
  );

  const handleNext = useCallback(() => {
    if (isLastQuestion) {
      setShowResults(true);
    } else {
      setCurrentQuestionIndex((prev) => prev + 1);
      setSelectedOptionIndex(null);
      setAnswered(false);
    }
  }, [isLastQuestion]);

  // Handle keyboard shortcuts for option selection
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (answered) {
        // After answering, → key advances
        if (e.key === 'ArrowRight' || e.key === 'Enter') {
          handleNext();
        }
      } else {
        // Before answering, 1-4 select options, Enter submits
        if (e.key >= '1' && e.key <= '4') {
          const index = parseInt(e.key, 10) - 1;
          if (index < currentQuestion.options?.length) {
            setSelectedOptionIndex(index);
          }
        } else if (e.key === 'Enter') {
          if (selectedOptionIndex !== null) {
            handleAnswer(selectedOptionIndex);
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [answered, selectedOptionIndex, currentQuestion.options?.length, handleAnswer, handleNext]);

  // Early return only AFTER all hooks are defined
  if (questions.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        No quiz content available
      </div>
    );
  }

  const progressPercent = ((currentQuestionIndex + 1) / totalQuestions) * 100;

  const getOptionLabel = (index) => String.fromCharCode(65 + index); // A, B, C, D

  if (showResults) {
    const percentage = (score / totalQuestions) * 100;
    const isGoodScore = percentage >= 70;
    const resultMessage = isGoodScore
      ? QUIZ_RESULT_MESSAGES.goodScore
      : QUIZ_RESULT_MESSAGES.needsReview;

    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
          alignItems: 'center',
          justifyContent: 'center',
          paddingTop: '56px',
          padding: '40px 20px',
          textAlign: 'center',
        }}
      >
        <h1
          style={{
            fontSize: '32px',
            fontWeight: 500,
            color: 'var(--navy)',
            marginBottom: '16px',
          }}
        >
          {score} out of {totalQuestions}
        </h1>

        <p
          style={{
            fontSize: '18px',
            color: 'var(--text)',
            maxWidth: '500px',
            lineHeight: 1.6,
            marginBottom: '32px',
          }}
        >
          {resultMessage}
        </p>

        <button
          onClick={() => onQuizComplete?.({ score, total: totalQuestions })}
          style={{
            minHeight: '44px',
            minWidth: '120px',
            padding: '12px 24px',
            backgroundColor: 'var(--teal)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--radius)',
            fontSize: '16px',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 200ms ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#237d74';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(42, 157, 143, 0.2)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--teal)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          Done
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        paddingTop: '56px',
        padding: '40px 20px',
        maxWidth: '800px',
        marginLeft: 'auto',
        marginRight: 'auto',
      }}
    >
      {/* Title */}
      <h1
        style={{
          fontSize: '24px',
          fontWeight: 500,
          marginBottom: '32px',
          color: 'var(--navy)',
          textAlign: 'center',
        }}
      >
        {title}
      </h1>

      {/* Progress Bar */}
      <div
        style={{
          height: '3px',
          backgroundColor: 'var(--border)',
          borderRadius: '2px',
          overflow: 'hidden',
          marginBottom: '40px',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progressPercent}%`,
            backgroundColor: 'var(--teal)',
            transition: 'width 300ms ease',
          }}
        />
      </div>

      {/* Question Card */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          paddingBottom: '40px',
        }}
      >
        {/* Question Prompt */}
        <h2
          style={{
            fontSize: '20px',
            lineHeight: '1.6',
            color: 'var(--text)',
            marginBottom: '32px',
            fontWeight: 500,
          }}
        >
          {currentQuestion.prompt}
        </h2>

        {/* Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '32px' }}>
          {currentQuestion.options.map((option, index) => {
            const isSelected = selectedOptionIndex === index;
            const isCorrect = index === currentQuestion.correct;
            const showAsCorrect = answered && isCorrect;
            const showAsIncorrect = answered && isSelected && !isCorrect;

            let backgroundColor = 'var(--surface)';
            let borderColor = 'var(--border)';
            let textColor = 'var(--text)';

            if (showAsCorrect) {
              backgroundColor = '#D4EDDA';
              borderColor = '#28A745';
              textColor = '#155724';
            } else if (showAsIncorrect) {
              backgroundColor = '#F8D7DA';
              borderColor = '#DC3545';
              textColor = '#721C24';
            } else if (isSelected && !answered) {
              borderColor = 'var(--teal)';
              backgroundColor = 'var(--teal-soft)';
            }

            return (
              <button
                key={index}
                onClick={() => !answered && handleAnswer(index)}
                disabled={answered}
                style={{
                  minHeight: '60px',
                  padding: '16px 20px',
                  backgroundColor,
                  border: `2px solid ${borderColor}`,
                  borderRadius: 'var(--radius)',
                  cursor: answered ? 'default' : 'pointer',
                  fontSize: '16px',
                  fontWeight: 400,
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  transition: 'all 200ms ease',
                  color: textColor,
                }}
                onMouseEnter={(e) => {
                  if (!answered) {
                    e.currentTarget.style.borderColor = 'var(--teal)';
                    e.currentTarget.style.backgroundColor = 'var(--teal-soft)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!answered && !isSelected) {
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.backgroundColor = 'var(--surface)';
                  }
                }}
                aria-label={`Option ${getOptionLabel(index)}: ${option}`}
              >
                <span
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '36px',
                    height: '36px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(0, 0, 0, 0.1)',
                    fontWeight: 500,
                    flexShrink: 0,
                  }}
                >
                  {getOptionLabel(index)}
                </span>
                <span>{option}</span>
                {showAsCorrect && <span style={{ marginLeft: 'auto' }}>✓</span>}
                {showAsIncorrect && <span style={{ marginLeft: 'auto' }}>✗</span>}
              </button>
            );
          })}
        </div>

        {/* Explanation (shown after answering) */}
        {answered && currentQuestion.explanation && (
          <div
            style={{
              padding: '16px',
              backgroundColor: 'var(--teal-soft)',
              borderLeft: '4px solid var(--teal)',
              borderRadius: '4px',
              fontSize: '15px',
              lineHeight: '1.6',
              color: 'var(--navy)',
              marginBottom: '24px',
            }}
          >
            {currentQuestion.explanation}
          </div>
        )}

        {/* Feedback message */}
        {answered && (
          <div
            style={{
              fontSize: '16px',
              fontWeight: 500,
              color: selectedOptionIndex === currentQuestion.correct ? '#28A745' : '#6B7280',
              marginBottom: '24px',
            }}
          >
            {selectedOptionIndex === currentQuestion.correct
              ? QUIZ_RESULT_MESSAGES.encouragement[
                  Math.floor(Math.random() * QUIZ_RESULT_MESSAGES.encouragement.length)
                ]
              : QUIZ_RESULT_MESSAGES.correction}
          </div>
        )}
      </div>

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        {!answered ? (
          <div style={{ fontSize: '12px', color: 'var(--muted)' }}>
            Select an option or press <kbd>1</kbd>-<kbd>4</kbd>, then <kbd>Enter</kbd> to submit
          </div>
        ) : (
          <button
            onClick={handleNext}
            style={{
              minHeight: '44px',
              minWidth: '140px',
              padding: '12px 24px',
              backgroundColor: 'var(--teal)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius)',
              fontSize: '16px',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 200ms ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#237d74';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(42, 157, 143, 0.2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--teal)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {isLastQuestion ? 'See Results →' : 'Next Question →'}
          </button>
        )}
      </div>
    </div>
  );
}
