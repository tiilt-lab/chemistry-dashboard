import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './SessionNavigator.module.css';
import { logStudyAction } from '../../services/study-log-service';

const SessionNavigator = ({ sessions, sessionDevices, activeDeviceId, collapsed, onCollapsedChange }) => {
    const [expanded, setExpanded] = useState({}); // sessionId → boolean
    const navigate = useNavigate();

    const toggleSession = (sessionId) => {
        setExpanded(prev => ({ ...prev, [sessionId]: !prev[sessionId] }));
    };

    const isSessionExpanded = (sessionId) => expanded[sessionId] !== false;

    const handleDeviceClick = (deviceId) => {
        logStudyAction('session_navigate', { session_device_id: deviceId });
        navigate(`/app/${deviceId}/assessment`);
    };

    if (collapsed) {
        return (
            <div className={styles.navCollapsed}>
                <button
                    className={styles.collapseBtn}
                    onClick={() => onCollapsedChange(false)}
                    title="Expand navigator"
                >
                    ☰
                </button>
                {sessions.map(s => (
                    <div key={s.id} className={styles.sessionBadge} title={s.name}>
                        {s.name.charAt(0).toUpperCase()}
                    </div>
                ))}
            </div>
        );
    }

    return (
        <div className={styles.navigator}>
            <div className={styles.navHeader}>
                <span className={styles.navTitle}>Sessions</span>
                <button
                    className={styles.collapseBtn}
                    onClick={() => onCollapsedChange(true)}
                    title="Collapse navigator"
                >
                    ☰
                </button>
            </div>

            <div className={styles.navList}>
                {sessions.length === 0 && (
                    <div className={styles.loading}>Loading…</div>
                )}
                {sessions.map(session => {
                    const devices = sessionDevices[session.id] || [];
                    const isOpen = isSessionExpanded(session.id);

                    return (
                        <div key={session.id} className={styles.sessionGroup}>
                            <button
                                className={styles.sessionHeader}
                                onClick={() => toggleSession(session.id)}
                            >
                                <span className={styles.chevron}>{isOpen ? '▾' : '▸'}</span>
                                <span className={styles.sessionName} title={session.name}>
                                    {session.name}
                                </span>
                            </button>

                            {isOpen && (
                                <div className={styles.deviceList}>
                                    {devices.length === 0 && (
                                        <div className={styles.noDevices}>No devices</div>
                                    )}
                                    {devices.map(device => {
                                        const isActive = String(device.id) === String(activeDeviceId);
                                        return (
                                            <button
                                                key={device.id}
                                                className={`${styles.deviceItem} ${isActive ? styles.deviceItemActive : ''}`}
                                                onClick={() => handleDeviceClick(device.id)}
                                                title={device.name || `Device ${device.id}`}
                                            >
                                                <span className={styles.deviceDot}>·</span>
                                                <span className={styles.deviceName}>
                                                    {device.name || `Device ${device.id}`}
                                                </span>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default SessionNavigator;
