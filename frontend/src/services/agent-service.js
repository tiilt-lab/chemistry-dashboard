/**
 * Agent Service
 *
 * Client for the Agentic RAG API endpoints.
 */

import { ApiService } from './api-service';

const api = new ApiService();

export class AgentService {
    /**
     * Send a query to the agent system.
     *
     * @param {string} query - The user's question
     * @param {string|null} conversationId - Optional conversation ID for follow-ups
     * @param {number|null} sessionDeviceId - Optional session context
     * @param {Object|null} steeringOptions - Optional user steering preferences
     * @param {Array<string>} steeringOptions.preferred_representations - Representations to focus on
     * @param {Array<string>} steeringOptions.exclude_representations - Representations to exclude
     * @param {string} steeringOptions.analysis_mode - Mode: 'explore', 'compare', 'trace'
     * @param {string} apiEndpoint - API endpoint path (default: 'api/v7/agent')
     * @param {string} mode - Agent mode: 'enhanced' (all artifacts) or 'baseline' (transcript only)
     * @returns {Promise<Object>} Agent response with answer, citations, etc.
     */
    async query(query, conversationId = null, sessionDeviceId = null, steeringOptions = null, apiEndpoint = 'api/v7/agent', mode = 'enhanced') {
        const data = {
            query,
            conversation_id: conversationId,
            session_device_id: sessionDeviceId,
            mode: mode
        };

        // Add steering options if provided (Co-Discovery feature)
        if (steeringOptions) {
            if (steeringOptions.preferred_representations) {
                data.preferred_representations = steeringOptions.preferred_representations;
            }
            if (steeringOptions.exclude_representations) {
                data.exclude_representations = steeringOptions.exclude_representations;
            }
            if (steeringOptions.analysis_mode) {
                data.analysis_mode = steeringOptions.analysis_mode;
            }
        }

        const response = await api.post(`${apiEndpoint}/query`, data);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(error.error || 'Query failed');
        }

        return response.json();
    }

    /**
     * Send a query to the baseline (transcript-only) agent.
     * Convenience method for AIED 2026 comparison.
     *
     * @param {string} query - The user's question
     * @param {string|null} conversationId - Optional conversation ID
     * @param {number|null} sessionDeviceId - Optional session context
     * @returns {Promise<Object>} Baseline agent response
     */
    async queryBaseline(query, conversationId = null, sessionDeviceId = null) {
        return this.query(query, conversationId, sessionDeviceId, null, 'api/v3/agent/baseline', 'baseline');
    }

    /**
     * List user's conversations.
     *
     * @param {number} limit - Max conversations to return
     * @param {string|null} variant - Filter by variant ('baseline' or null for full agent)
     * @param {string} apiEndpoint - API endpoint path (default: 'api/v7/agent')
     * @returns {Promise<Array>} List of conversations
     */
    async listConversations(limit = 20, variant = null, apiEndpoint = 'api/v7/agent') {
        const response = await api.get(`${apiEndpoint}/conversations`);

        if (!response.ok) {
            // Fall back to empty list instead of throwing
            console.warn('Failed to load conversations');
            return [];
        }

        const data = await response.json();
        return data.conversations || [];
    }

    /**
     * Get a specific conversation with messages.
     *
     * @param {string} conversationId - Conversation ID
     * @param {string} apiEndpoint - API endpoint path (default: 'api/v7/agent')
     * @returns {Promise<Object>} Conversation with messages
     */
    async getConversation(conversationId, apiEndpoint = 'api/v7/agent') {
        const response = await api.get(`${apiEndpoint}/conversations/${conversationId}`);

        if (!response.ok) {
            throw new Error('Failed to load conversation');
        }

        return response.json();
    }

    /**
     * Get messages for a conversation.
     * Returns the messages from getConversation.
     *
     * @param {string} conversationId - Conversation ID
     * @param {number} offset - Starting offset
     * @param {number|null} limit - Max messages
     * @param {string} apiEndpoint - API endpoint path (default: 'api/v7/agent')
     * @returns {Promise<Array>} Messages
     */
    async getMessages(conversationId, offset = 0, limit = null, apiEndpoint = 'api/v7/agent') {
        const conversation = await this.getConversation(conversationId, apiEndpoint);
        return conversation.messages || [];
    }

    /**
     * Delete a conversation.
     *
     * @param {string} conversationId - Conversation ID
     * @param {string} apiEndpoint - API endpoint path (default: 'api/v7/agent')
     * @returns {Promise<boolean>} Success status
     */
    async deleteConversation(conversationId, apiEndpoint = 'api/v7/agent') {
        const response = await api.delete(`${apiEndpoint}/conversations/${conversationId}`);

        if (!response.ok) {
            throw new Error('Failed to delete conversation');
        }

        return true;
    }

    /**
     * Create a new conversation.
     *
     * @param {string|null} title - Optional title for the conversation
     * @param {string} apiEndpoint - API endpoint path (default: 'api/v7/agent')
     * @returns {Promise<Object>} Created conversation
     */
    async createConversation(title = null, apiEndpoint = 'api/v7/agent') {
        const response = await api.post(`${apiEndpoint}/conversations`, {
            title: title || 'New Conversation'
        });

        if (!response.ok) {
            throw new Error('Failed to create conversation');
        }

        return response.json();
    }

    /**
     * Rename a conversation.
     * Note: Rename endpoint not implemented - titles are set from first message.
     *
     * @param {string} conversationId - Conversation ID
     * @param {string} newTitle - New title for the conversation
     * @returns {Promise<Object>} Updated conversation
     */
    async renameConversation(conversationId, newTitle) {
        // Rename not implemented - titles are set from first message
        console.warn('Rename not implemented - conversation titles are set from first message');
        return { conversation_id: conversationId, title: newTitle };
    }

    /**
     * Classify a query without executing it.
     *
     * @param {string} query - Query to classify
     * @returns {Promise<Object>} Classification result
     */
    async classifyQuery(query) {
        const response = await api.post('api/v1/agent/classify', { query });

        if (!response.ok) {
            throw new Error('Classification failed');
        }

        return response.json();
    }

    /**
     * List available tools.
     *
     * @returns {Promise<Array>} List of tools
     */
    async listTools() {
        const response = await api.get('api/v1/agent/tools');

        if (!response.ok) {
            throw new Error('Failed to load tools');
        }

        const data = await response.json();
        return data.tools;
    }
}

// Export singleton instance
export const agentService = new AgentService();
