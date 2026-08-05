/**
 * Baseline Agent Chat Panel
 *
 * Transcript-only baseline for V7 comparison (AIED 2026).
 * Only has access to transcripts and speaker profiles.
 * No concept maps, 7C analysis, or LIWC metrics.
 *
 * Features:
 * - Welcome message for new conversations
 * - Confidence indicators
 * - Tools used display
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { agentService } from '../../services/agent-service';
import V7MessageBubble from './V7MessageBubble';
import CitationPopover from './CitationPopover';
import styles from './V7AgentChatPanel.module.css';

// Welcome message shown for new conversations
const WELCOME_MESSAGE = {
    id: 'welcome',
    role: 'assistant',
    content: `Hello! I'm your Discussion Analysis Assistant (Baseline).

I can help you explore:
- **Transcripts** - What students discussed
- **Speaker Patterns** - Participation analysis

What would you like to know about your discussions?`,
    isUser: false,
    isWelcome: true,
    created_at: new Date().toISOString()
};

// Available representation options for steering (baseline: transcript only)
const REPRESENTATION_OPTIONS = [
    { id: 'transcript', label: 'Transcripts' },
    { id: 'speaker_profile', label: 'Speaker Profiles' }
];

const ANALYSIS_MODES = [
    { id: null, label: 'Auto', description: 'Let the agent decide' },
    { id: 'explore', label: 'Explore', description: 'Search across sessions' },
    { id: 'compare', label: 'Compare', description: 'Compare multiple sessions' },
    { id: 'trace', label: 'Trace', description: 'Follow concept paths' }
];

const BaselineAgentChatPanel = ({ sessionDeviceId, onClose }) => {
    const apiEndpoint = 'api/baseline/agent';
    const [messages, setMessages] = useState([]);
    const [conversations, setConversations] = useState([]);
    const [activeConversationId, setActiveConversationId] = useState(null);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    // Steering controls state
    const [showSteeringControls, setShowSteeringControls] = useState(false);
    const [preferredRepresentations, setPreferredRepresentations] = useState([]);
    const [excludeRepresentations, setExcludeRepresentations] = useState([]);
    const [analysisMode, setAnalysisMode] = useState(null);

    // Citation popover state
    const [activeCitation, setActiveCitation] = useState(null);
    const [popoverPosition, setPopoverPosition] = useState(null);

    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    const handleCitationClick = useCallback((citation, event) => {
        event.stopPropagation();
        setActiveCitation(citation);
        setPopoverPosition({ x: event.clientX, y: event.clientY });
    }, []);

    const closeCitationPopover = useCallback(() => {
        setActiveCitation(null);
        setPopoverPosition(null);
    }, []);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, scrollToBottom]);

    useEffect(() => {
        loadConversations();
    }, []);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const loadConversations = async () => {
        try {
            const convs = await agentService.listConversations(1000, null, apiEndpoint);
            setConversations(convs);
        } catch (err) {
            console.error('Failed to load conversations:', err);
        }
    };

    const loadConversation = async (conversationId) => {
        try {
            setIsLoading(true);
            const data = await agentService.getConversation(conversationId, apiEndpoint);
            setMessages(data.messages.map(m => ({ ...m, isUser: m.role === 'user' })));
            setActiveConversationId(conversationId);
        } catch (err) {
            setError('Failed to load conversation');
        } finally {
            setIsLoading(false);
        }
    };

    const startNewConversation = () => {
        setMessages([{ ...WELCOME_MESSAGE, id: `welcome-${Date.now()}` }]);
        setActiveConversationId(null);
        inputRef.current?.focus();
    };

    useEffect(() => {
        if (messages.length === 0 && !activeConversationId) {
            setMessages([{ ...WELCOME_MESSAGE, id: `welcome-${Date.now()}` }]);
        }
    }, []);

    const handleDeleteConversation = async (conversationId) => {
        try {
            await agentService.deleteConversation(conversationId, apiEndpoint);
            setConversations(convs => convs.filter(c => c.conversation_id !== conversationId));
            if (activeConversationId === conversationId) {
                startNewConversation();
            }
        } catch (err) {
            setError('Failed to delete conversation');
        }
    };

    const handleRenameConversation = async (conversationId, newTitle) => {
        try {
            await agentService.renameConversation(conversationId, newTitle);
            setConversations(convs => convs.map(c =>
                c.id === conversationId ? { ...c, title: newTitle } : c
            ));
        } catch (err) {
            setError('Failed to rename conversation');
        }
    };

    const handleSubmit = async (e) => {
        e?.preventDefault();

        const query = inputValue.trim();
        if (!query || isLoading) return;

        const userMessage = {
            id: Date.now(),
            role: 'user',
            content: query,
            isUser: true,
            created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);
        setError(null);

        try {
            const steeringOptions = {};
            if (preferredRepresentations.length > 0) {
                steeringOptions.preferred_representations = preferredRepresentations;
            }
            if (excludeRepresentations.length > 0) {
                steeringOptions.exclude_representations = excludeRepresentations;
            }
            if (analysisMode) {
                steeringOptions.analysis_mode = analysisMode;
            }

            const response = await agentService.query(
                query,
                activeConversationId,
                sessionDeviceId,
                Object.keys(steeringOptions).length > 0 ? steeringOptions : null,
                apiEndpoint,
                'enhanced'
            );

            const assistantMessage = {
                id: response.message_id || Date.now() + 1,
                role: 'assistant',
                content: response.answer,
                tools_used: response.tools_used,
                isUser: false,
                created_at: new Date().toISOString()
            };
            setMessages(prev => [...prev.filter(m => !m.isWelcome), assistantMessage]);

            if (response.conversation_id && !activeConversationId) {
                setActiveConversationId(response.conversation_id);
                loadConversations();
            }

        } catch (err) {
            setError(err.message || 'Failed to get response');
            setMessages(prev => [...prev.filter(m => !m.isWelcome), {
                id: Date.now() + 1,
                role: 'assistant',
                content: `Sorry, I encountered an error: ${err.message}`,
                isUser: false,
                isError: true,
                created_at: new Date().toISOString()
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const togglePreferredRep = (repId) => {
        setPreferredRepresentations(prev => {
            if (prev.includes(repId)) {
                return prev.filter(r => r !== repId);
            } else {
                setExcludeRepresentations(exc => exc.filter(r => r !== repId));
                return [...prev, repId];
            }
        });
    };

    const toggleExcludeRep = (repId) => {
        setExcludeRepresentations(prev => {
            if (prev.includes(repId)) {
                return prev.filter(r => r !== repId);
            } else {
                setPreferredRepresentations(pref => pref.filter(r => r !== repId));
                return [...prev, repId];
            }
        });
    };

    const clearSteering = () => {
        setPreferredRepresentations([]);
        setExcludeRepresentations([]);
        setAnalysisMode(null);
    };

    const hasSteeringActive = preferredRepresentations.length > 0 ||
                              excludeRepresentations.length > 0 ||
                              analysisMode !== null;

    const groupConversationsByDate = (convos) => {
        const groups = {};
        const today = new Date().toDateString();
        const yesterday = new Date(Date.now() - 86400000).toDateString();

        convos.forEach(conv => {
            const date = new Date(conv.updated_at || conv.created_at).toDateString();
            let label;
            if (date === today) label = 'Today';
            else if (date === yesterday) label = 'Yesterday';
            else label = date;

            if (!groups[label]) groups[label] = [];
            groups[label].push(conv);
        });
        return groups;
    };

    const groupedConversations = groupConversationsByDate(conversations);

    return (
        <div className={styles.chatPanel}>
            {/* Sidebar */}
            <div className={styles.sidebar}>
                <div className={styles.sidebarHeader}>
                    <button className={styles.newChatButton} onClick={startNewConversation}>
                        + New Chat
                    </button>
                </div>

                <div className={styles.sidebarList}>
                    {conversations.length === 0 ? (
                        <div className={styles.emptySidebar}>No conversations yet</div>
                    ) : (
                        Object.entries(groupedConversations).map(([date, convos]) => (
                            <div key={date}>
                                <div className={styles.dateGroup}>{date}</div>
                                {convos.map(conv => (
                                    <div
                                        key={conv.id}
                                        className={`${styles.conversationItem} ${
                                            conv.id === activeConversationId ? styles.active : ''
                                        }`}
                                        onClick={() => loadConversation(conv.id)}
                                    >
                                        <span className={styles.conversationTitle}>
                                            {conv.title || 'New conversation'}
                                        </span>
                                        <div className={styles.conversationActions}>
                                            <button
                                                className={styles.conversationBtn}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    const newTitle = prompt('Rename conversation:', conv.title);
                                                    if (newTitle) handleRenameConversation(conv.id, newTitle);
                                                }}
                                                title="Rename"
                                            >
                                                ✎
                                            </button>
                                            <button
                                                className={styles.conversationBtn}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    if (window.confirm('Delete this conversation?')) {
                                                        handleDeleteConversation(conv.id);
                                                    }
                                                }}
                                                title="Delete"
                                            >
                                                ×
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className={styles.mainChat}>
                <div className={styles.header}>
                    <h2 className={styles.title}>Discussion Assistant (Baseline)</h2>
                    {onClose && (
                        <button className={styles.closeButton} onClick={onClose}>&times;</button>
                    )}
                </div>

                <div className={styles.messagesArea}>
                    <div className={styles.messagesContainer}>
                        {messages.map((message) => (
                            <V7MessageBubble
                                key={message.id}
                                message={message}
                                onCitationClick={handleCitationClick}
                            />
                        ))}

                        {isLoading && (
                            <div className={styles.loadingIndicator}>
                                <div className={styles.typingDots}>
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                                <span className={styles.loadingText}>Thinking...</span>
                            </div>
                        )}

                        {error && !isLoading && (
                            <div className={styles.errorMessage}>{error}</div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </div>

                {/* Input Area */}
                <div className={styles.inputWrapper}>
                    <div className={styles.inputContainer}>
                        {showSteeringControls && (
                            <div className={styles.steeringPanel}>
                                <div className={styles.steeringHeader}>
                                    <span>Customize Analysis</span>
                                    {hasSteeringActive && (
                                        <button className={styles.clearSteering} onClick={clearSteering}>
                                            Reset
                                        </button>
                                    )}
                                </div>

                                <div className={styles.steeringSection}>
                                    <label className={styles.steeringLabel}>Mode:</label>
                                    <div className={styles.modeButtons}>
                                        {ANALYSIS_MODES.map(mode => (
                                            <button
                                                key={mode.id || 'auto'}
                                                className={`${styles.modeButton} ${analysisMode === mode.id ? styles.active : ''}`}
                                                onClick={() => setAnalysisMode(mode.id)}
                                                title={mode.description}
                                            >
                                                {mode.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className={styles.steeringSection}>
                                    <label className={styles.steeringLabel}>Focus on:</label>
                                    <div className={styles.repButtons}>
                                        {REPRESENTATION_OPTIONS.map(rep => (
                                            <button
                                                key={rep.id}
                                                className={`${styles.repButton} ${
                                                    preferredRepresentations.includes(rep.id) ? styles.preferred :
                                                    excludeRepresentations.includes(rep.id) ? styles.excluded : ''
                                                }`}
                                                onClick={() => togglePreferredRep(rep.id)}
                                                onContextMenu={(e) => {
                                                    e.preventDefault();
                                                    toggleExcludeRep(rep.id);
                                                }}
                                                title="Click to prefer, right-click to exclude"
                                            >
                                                {rep.label}
                                            </button>
                                        ))}
                                    </div>
                                    <span className={styles.steeringHint}>
                                        Click to focus, right-click to exclude
                                    </span>
                                </div>
                            </div>
                        )}

                        <form className={styles.inputArea} onSubmit={handleSubmit}>
                            <button
                                type="button"
                                className={`${styles.steeringToggle} ${hasSteeringActive ? styles.active : ''}`}
                                onClick={() => setShowSteeringControls(!showSteeringControls)}
                                title="Customize analysis"
                            >
                                {showSteeringControls ? '▼' : '▲'}
                            </button>
                            <textarea
                                ref={inputRef}
                                className={styles.input}
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder={hasSteeringActive ?
                                    `Ask (${analysisMode || 'custom'} mode)...` :
                                    "Ask about your discussions..."}
                                disabled={isLoading}
                                rows={1}
                            />
                            <button
                                type="submit"
                                className={styles.sendButton}
                                disabled={isLoading || !inputValue.trim()}
                            >
                                {isLoading ? '...' : 'Send'}
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            {activeCitation && (
                <CitationPopover
                    citation={activeCitation}
                    position={popoverPosition}
                    onClose={closeCitationPopover}
                />
            )}
        </div>
    );
};

export default BaselineAgentChatPanel;
