/**
 * Conversation List Component
 *
 * Sidebar showing past conversations.
 */

import React from 'react';
import styles from './ConversationList.module.css';

const ConversationList = ({
    conversations,
    activeId,
    onSelect,
    onDelete,
    onRename,
    onNewChat,
    onClose
}) => {
    const [editingId, setEditingId] = React.useState(null);
    const [editTitle, setEditTitle] = React.useState('');

    const handleStartEdit = (e, conv) => {
        e.stopPropagation();
        setEditingId(conv.id);
        setEditTitle(conv.title || '');
    };

    const handleSaveEdit = (e, convId) => {
        e.stopPropagation();
        if (editTitle.trim()) {
            onRename(convId, editTitle.trim());
        }
        setEditingId(null);
    };

    const handleKeyDown = (e, convId) => {
        if (e.key === 'Enter') {
            handleSaveEdit(e, convId);
        } else if (e.key === 'Escape') {
            setEditingId(null);
        }
    };
    // Group conversations by date
    const groupedConversations = groupByDate(conversations);

    return (
        <div className={styles.overlay} onClick={onClose}>
            <div className={styles.sidebar} onClick={e => e.stopPropagation()}>
                <div className={styles.header}>
                    <h3>Conversations</h3>
                    <button className={styles.closeBtn} onClick={onClose}>
                        &times;
                    </button>
                </div>

                <button className={styles.newChatBtn} onClick={onNewChat}>
                    + New Conversation
                </button>

                <div className={styles.list}>
                    {Object.entries(groupedConversations).map(([date, convs]) => (
                        <div key={date} className={styles.group}>
                            <div className={styles.dateHeader}>{date}</div>
                            {convs.map(conv => (
                                <div
                                    key={conv.id}
                                    className={`${styles.item} ${conv.id === activeId ? styles.active : ''}`}
                                    onClick={() => editingId !== conv.id && onSelect(conv.id)}
                                >
                                    <div className={styles.itemContent}>
                                        {editingId === conv.id ? (
                                            <input
                                                type="text"
                                                className={styles.editInput}
                                                value={editTitle}
                                                onChange={(e) => setEditTitle(e.target.value)}
                                                onKeyDown={(e) => handleKeyDown(e, conv.id)}
                                                onBlur={(e) => handleSaveEdit(e, conv.id)}
                                                onClick={(e) => e.stopPropagation()}
                                                autoFocus
                                            />
                                        ) : (
                                            <div className={styles.itemTitle}>
                                                {conv.title || 'Untitled conversation'}
                                            </div>
                                        )}
                                        {conv.session_device_id && (
                                            <div className={styles.itemMeta}>
                                                Session {conv.session_device_id}
                                            </div>
                                        )}
                                    </div>
                                    <div className={styles.itemActions}>
                                        <button
                                            className={styles.editBtn}
                                            onClick={(e) => handleStartEdit(e, conv)}
                                            title="Rename conversation"
                                        >
                                            ✎
                                        </button>
                                        <button
                                            className={styles.deleteBtn}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                if (window.confirm('Delete this conversation?')) {
                                                    onDelete(conv.id);
                                                }
                                            }}
                                            title="Delete conversation"
                                        >
                                            &times;
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ))}

                    {conversations.length === 0 && (
                        <div className={styles.empty}>
                            No conversations yet
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

/**
 * Group conversations by date.
 */
const groupByDate = (conversations) => {
    const groups = {};
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();

    conversations.forEach(conv => {
        const date = new Date(conv.created_at || conv.last_active);
        const dateStr = date.toDateString();

        let label;
        if (dateStr === today) {
            label = 'Today';
        } else if (dateStr === yesterday) {
            label = 'Yesterday';
        } else {
            label = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }

        if (!groups[label]) {
            groups[label] = [];
        }
        groups[label].push(conv);
    });

    return groups;
};

export default ConversationList;
