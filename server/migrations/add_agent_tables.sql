-- Migration: Add Agent Conversation Tables
-- For BLINC Agentic RAG System
-- Run with: mysql -u vagrant -pvagrant discussion_capture < migrations/add_agent_tables.sql

-- Create agent_conversation table
CREATE TABLE IF NOT EXISTS agent_conversation (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    session_device_id INT NULL,
    title VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (session_device_id) REFERENCES session_device(id) ON DELETE SET NULL,
    INDEX idx_user_last_active (user_id, last_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create agent_message table
CREATE TABLE IF NOT EXISTS agent_message (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    citations JSON NULL,
    tools_used JSON NULL,
    reasoning_trace JSON NULL,
    confidence FLOAT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES agent_conversation(id) ON DELETE CASCADE,
    INDEX idx_conversation_created (conversation_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Success message
SELECT 'Agent tables created successfully!' as message;
