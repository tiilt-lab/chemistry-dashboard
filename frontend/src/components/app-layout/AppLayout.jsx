import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import styles from './AppLayout.module.css';
import SessionNavigator from '../session-navigator/SessionNavigator';
import ContentArea from '../content-area/ContentArea';
import V7AgentChatPanel from '../agent-chat/V7AgentChatPanel';

const AppLayout = () => {
    const { deviceId } = useParams();
    const [searchParams, setSearchParams] = useSearchParams();
    const [sessions, setSessions] = useState([]);
    const [sessionDevices, setSessionDevices] = useState({}); // sessionId → devices[]

    // Lifted shared state
    const [navigatorCollapsed, setNavigatorCollapsed] = useState(false);
    const [transcriptOpen, setTranscriptOpen] = useState(false);

    // Open transcript drawer when navigated with ?transcript=open
    useEffect(() => {
        if (searchParams.get('transcript') === 'open' && deviceId) {
            setTranscriptOpen(true);
            setNavigatorCollapsed(true);
            searchParams.delete('transcript');
            setSearchParams(searchParams, { replace: true });
        }
    }, [deviceId, searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

    // Mutual exclusion: opening transcript collapses navigator; expanding navigator closes transcript
    const handleTranscriptToggle = (open) => {
        setTranscriptOpen(open);
        if (open) {
            setNavigatorCollapsed(true);
        } else {
            setNavigatorCollapsed(false); // restore navigator when transcript closes
        }
    };

    const handleNavigatorCollapse = (collapsed) => {
        setNavigatorCollapsed(collapsed);
        if (!collapsed) setTranscriptOpen(false);
    };

    useEffect(() => {
        fetchSessionsAndDevices();
    }, []);

    const fetchSessionsAndDevices = async () => {
        try {
            const res = await fetch('/api/v1/sessions');
            if (!res.ok) return;
            const sessionsData = await res.json();
            setSessions(sessionsData);

            const devicesMap = {};
            await Promise.all(sessionsData.map(async s => {
                try {
                    const devRes = await fetch(`/api/v1/sessions/${s.id}/devices`);
                    devicesMap[s.id] = devRes.ok ? await devRes.json() : [];
                } catch (_) {
                    devicesMap[s.id] = [];
                }
            }));
            setSessionDevices(devicesMap);
        } catch (_) {}
    };

    const activeDeviceInfo = useMemo(() => {
        if (!deviceId) return null;
        for (const [sessionId, devices] of Object.entries(sessionDevices)) {
            const device = devices.find(d => String(d.id) === String(deviceId));
            if (device) {
                const session = sessions.find(s => String(s.id) === String(sessionId));
                return { device, session, sessionId: parseInt(sessionId) };
            }
        }
        return null;
    }, [deviceId, sessionDevices, sessions]);

    return (
        <div className={styles.layout}>
            <div className={styles.leftPanel}>
                <SessionNavigator
                    sessions={sessions}
                    sessionDevices={sessionDevices}
                    activeDeviceId={deviceId}
                    collapsed={navigatorCollapsed}
                    onCollapsedChange={handleNavigatorCollapse}
                />
                <ContentArea
                    deviceId={deviceId}
                    deviceInfo={activeDeviceInfo}
                    transcriptOpen={transcriptOpen}
                    onTranscriptToggle={handleTranscriptToggle}
                />
            </div>
            <div className={styles.rightPanel}>
                <V7AgentChatPanel
                    sessionDeviceId={deviceId ? parseInt(deviceId) : null}
                    embedded={true}
                />
            </div>
        </div>
    );
};

export default AppLayout;
