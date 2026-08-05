/**
 * V7 Chat Panel
 *
 * Uses V7-specific components that are independent from V3.
 * Changes to V7 UI won't affect V3.
 */

import React from 'react';
import V7AgentChatPanel from './V7AgentChatPanel';

const V7ChatPanel = (props) => {
    return <V7AgentChatPanel {...props} />;
};

export default V7ChatPanel;
