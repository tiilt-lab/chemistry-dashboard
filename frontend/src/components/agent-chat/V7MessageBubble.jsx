/**
 * V7 Message Bubble Component
 *
 * V7-specific message display. Simplified - no legacy citations/references.
 * Shows: message content + tools used.
 * Custom markdown rendering: transcript quotes and timestamps styled inline.
 */

import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import styles from './V7MessageBubble.module.css';
import ArtifactLinkCard from './ArtifactLinkCard';

// --- Text extraction helper ---

const extractText = (children) => {
    if (typeof children === 'string') return children;
    if (Array.isArray(children)) return children.map(extractText).join('');
    if (children?.props?.children) return extractText(children.props.children);
    return '';
};

// --- Quote detection for blockquote promotion (existing logic) ---

const isQuotedText = (text) => {
    const trimmed = text.trim();
    if (trimmed.length < 30) return false;
    if (!/^[""\u201C]/.test(trimmed)) return false;
    return /[""\u201D][.?!,;:)]*(\s*[-—–]\s*[\[\(]?\d{1,3}:\d{2}[\]\)]?)?(\s*[\[\(]\d{1,3}:\d{2}[\]\)])?$/.test(trimmed);
};

const isParagraphQuote = (text) => {
    const trimmed = text.trim();
    if (trimmed.length < 30) return false;
    if (!/^[""\u201C]/.test(trimmed)) return false;
    return /[""\u201D][.?!,;:)]*\s*[\[\(]\d{1,3}:\d{2}(?:\s*[-—–]\s*\d{1,3}:\d{2})?[\]\)]$/.test(trimmed);
};

// --- Core pipeline helper ---
// Process only the string segments in a mixed array of strings and React elements.

const processTextSegments = (children, processor) => {
    if (typeof children === 'string') return processor(children);
    if (Array.isArray(children)) {
        return children.flatMap((child) => {
            if (typeof child === 'string') return processor(child);
            return [child];
        });
    }
    return [children];
};

// --- Styling functions ---

const INLINE_QUOTE_RE = /([""\u201C])([^""\u201D]{4,120})([""\u201D])/g;

const styleInlineQuotes = (text) => {
    const parts = text.split(INLINE_QUOTE_RE);
    if (parts.length === 1) return [text];
    // split produces: [before, openQuote, content, closeQuote, after, ...]
    const result = [];
    let i = 0;
    while (i < parts.length) {
        if (i + 3 < parts.length && /^[""\u201C]$/.test(parts[i + 1])) {
            if (parts[i]) result.push(parts[i]);
            const full = parts[i + 1] + parts[i + 2] + parts[i + 3];
            result.push(
                <span key={`q-${i}`} className={styles.inlinePhrase}>{full}</span>
            );
            i += 4;
        } else {
            if (parts[i]) result.push(parts[i]);
            i++;
        }
    }
    return result;
};

const TS_PATTERN = /(\[\d{1,3}:\d{2}\]|\(\d{1,3}:\d{2}(?:\s*[-—–]\s*\d{1,3}:\d{2})?\))/g;

const styleTimestamps = (text) => {
    const parts = text.split(TS_PATTERN);
    if (parts.length === 1) return [text];
    return parts.map((part, i) =>
        /^[\[\(]\d{1,3}:\d{2}/.test(part)
            ? <span key={`ts-${i}`} className={styles.timestamp}>{part}</span>
            : part
    ).filter(Boolean);
};

// --- Hook: build markdown components with inline styling ---

const useMarkdownComponents = () => {
    const styledInline = useMemo(() => {
        const applyPipeline = (children) => {
            if (!children) return children;
            let result = children;
            result = processTextSegments(result, styleInlineQuotes);
            result = processTextSegments(result, styleTimestamps);
            // Wrap any remaining bare strings in spans for stable keys
            if (Array.isArray(result)) {
                result = result.map((item, i) =>
                    typeof item === 'string' ? <span key={`t-${i}`}>{item}</span> : item
                );
            }
            return result;
        };
        return applyPipeline;
    }, []);

    return useMemo(() => ({
        em: ({ children }) => {
            const text = extractText(children);
            if (isQuotedText(text)) {
                return <blockquote className={styles.inlineQuote}><p>{children}</p></blockquote>;
            }
            return <em>{children}</em>;
        },
        li: ({ children }) => {
            const text = extractText(children);
            if (isQuotedText(text) || isParagraphQuote(text)) {
                return <li className={styles.quotedListItem}>{styledInline(children)}</li>;
            }
            return <li>{styledInline(children)}</li>;
        },
        p: ({ children }) => {
            const text = extractText(children);
            if (isParagraphQuote(text)) {
                return <blockquote className={styles.inlineQuote}><p>{styledInline(children)}</p></blockquote>;
            }
            return <p>{styledInline(children)}</p>;
        }
    }), [styledInline]);
};

// --- Component ---

const V7MessageBubble = ({ message, onCitationClick }) => {
    const isUser = message.role === 'user' || message.isUser;
    const hasTools = message.tools_used && message.tools_used.length > 0;
    const hasCitations = !isUser && message.citations && message.citations.length > 0;
    const markdownComponents = useMarkdownComponents();

    return (
        <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.assistantBubble}`}>
            {/* Message content */}
            <div className={styles.content}>
                {message.content ? (
                    <ReactMarkdown components={markdownComponents}>{message.content}</ReactMarkdown>
                ) : null}
            </div>

            {/* Artifact link cards */}
            {hasCitations && (
                <div className={styles.citationCards}>
                    {message.citations.map((citation, idx) => (
                        <ArtifactLinkCard key={`${citation.discussion_id}-${citation.type}-${idx}`} citation={citation} />
                    ))}
                </div>
            )}

            {/* Assistant message extras */}
            {!isUser && hasTools && (
                <div className={styles.metadata}>
                    <span className={styles.tools} title={message.tools_used.join(', ')}>
                        {message.tools_used.length} tool{message.tools_used.length !== 1 ? 's' : ''} used
                    </span>
                </div>
            )}
        </div>
    );
};

export default V7MessageBubble;
