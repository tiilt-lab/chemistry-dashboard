/**
 * Reasoning Trace Component
 *
 * Displays the agent's reasoning steps in a collapsible format.
 */

import React from 'react';
import styles from './ReasoningTrace.module.css';

const ReasoningTrace = ({ trace }) => {
    if (!trace || trace.length === 0) {
        return null;
    }

    return (
        <div className={styles.container}>
            <h4 className={styles.title}>Reasoning Steps</h4>
            <div className={styles.steps}>
                {trace.map((step, index) => (
                    <div key={index} className={styles.step}>
                        <div className={styles.stepNumber}>{index + 1}</div>
                        <div className={styles.stepContent}>
                            {formatStep(step)}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

/**
 * Format a reasoning step for display.
 */
const formatStep = (step) => {
    if (!step) return '';

    // Handle different step formats
    if (typeof step === 'string') {
        // Check for "Thought:", "Action:", "Plan:" prefixes
        if (step.startsWith('Thought:')) {
            return (
                <>
                    <span className={styles.label}>Thought:</span>
                    <span className={styles.text}>{step.substring(8).trim()}</span>
                </>
            );
        }
        if (step.startsWith('Action:')) {
            return (
                <>
                    <span className={styles.label}>Action:</span>
                    <span className={styles.toolName}>{step.substring(7).trim()}</span>
                </>
            );
        }
        if (step.startsWith('Plan:')) {
            return (
                <>
                    <span className={styles.label}>Plan:</span>
                    <span className={styles.text}>{step.substring(5).trim()}</span>
                </>
            );
        }
        if (step.startsWith('Step ')) {
            const match = step.match(/^Step (\d+):\s*(\w+)\s*-\s*(.*)$/);
            if (match) {
                return (
                    <>
                        <span className={styles.label}>Step {match[1]}:</span>
                        <span className={styles.toolName}>{match[2]}</span>
                        <span className={styles.purpose}>{match[3]}</span>
                    </>
                );
            }
        }

        return <span className={styles.text}>{step}</span>;
    }

    if (typeof step === 'object') {
        return (
            <>
                {step.thought && (
                    <div>
                        <span className={styles.label}>Thought:</span>
                        <span className={styles.text}>{step.thought}</span>
                    </div>
                )}
                {step.action && (
                    <div>
                        <span className={styles.label}>Action:</span>
                        <span className={styles.toolName}>
                            {step.action.tool || step.action}
                        </span>
                    </div>
                )}
            </>
        );
    }

    return String(step);
};

export default ReasoningTrace;
