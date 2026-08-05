/**
 * Baseline Chat Panel
 *
 * Wrapper component for the transcript-only baseline agent.
 * Used for AIED 2026 comparison to demonstrate the value of
 * heterogeneous artifacts (concept maps, 7C analysis, LIWC).
 *
 * This component uses the same AgentChatPanel but configured
 * to use Agent V3's baseline mode which only has transcript access.
 */

import React from 'react';
import AgentChatPanel from './AgentChatPanel';

const BaselineChatPanel = (props) => {
    return (
        <AgentChatPanel
            {...props}
            apiEndpoint="api/baseline/agent"
            variant="baseline"
            mode="baseline"
        />
    );
};

export default BaselineChatPanel;
