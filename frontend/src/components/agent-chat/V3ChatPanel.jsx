/**
 * V3 Chat Panel
 *
 * Wrapper component for Agent V3 - the Ultra Agent with intelligent reasoning.
 *
 * Key V3 features:
 * - Self-reflective RAG
 * - Query rewriting
 * - Intelligent reasoning
 * - Multi-turn context
 * - Database-backed conversation persistence
 */

import React from 'react';
import AgentChatPanel from './AgentChatPanel';

const V3ChatPanel = (props) => {
    return (
        <AgentChatPanel
            {...props}
            apiEndpoint="api/v3/agent"
            variant="full"
            mode="enhanced"
        />
    );
};

export default V3ChatPanel;
