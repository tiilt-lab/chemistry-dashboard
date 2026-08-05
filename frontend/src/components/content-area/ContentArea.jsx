import React, { useEffect } from 'react';
import styles from './ContentArea.module.css';
import SevenCsPanel from '../seven-cs/SevenCsPanel';
import ConceptMapView from '../concept-map/ConceptMapView';
import TranscriptPanel from '../transcript-drawer/TranscriptDrawer';
import { logStudyAction } from '../../services/study-log-service';

const ContentArea = ({ deviceId, deviceInfo, transcriptOpen, onTranscriptToggle }) => {

    // Close transcript when device changes
    useEffect(() => {
        if (transcriptOpen) onTranscriptToggle(false);
    }, [deviceId]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleTranscriptToggle = (open) => {
        logStudyAction(open ? 'transcript_open' : 'transcript_close', { session_device_id: parseInt(deviceId) });
        onTranscriptToggle(open);
    };

    const sessionName = deviceInfo?.session?.name;
    const deviceName = deviceInfo?.device?.name;

    return (
        <div className={styles.contentArea}>
            {!deviceId ? (
                <div className={styles.empty}>
                    <div className={styles.emptyInner}>
                        <span className={styles.emptyIcon}>◎</span>
                        <p className={styles.emptyText}>Select a session device from the left to get started</p>
                        <p className={styles.emptyHint}>Or chat with the agent</p>
                    </div>
                </div>
            ) : (
                <>
                    {/* Header */}
                    <div className={styles.contentHeader}>
                        {sessionName && (
                            <span className={styles.breadcrumb}>
                                {sessionName}{deviceName ? ` · ${deviceName}` : ''}
                            </span>
                        )}
                        <button
                            className={`${styles.transcriptBtn} ${transcriptOpen ? styles.transcriptBtnActive : ''}`}
                            onClick={() => handleTranscriptToggle(!transcriptOpen)}
                        >
                            {transcriptOpen ? '✕ Transcript' : 'Transcript ▶'}
                        </button>
                    </div>

                    {/* Body */}
                    <div className={styles.scrollBody}>
                        {/* Assessment + optional transcript side-by-side */}
                        <div className={transcriptOpen ? styles.splitRow : styles.assessmentFull}>
                            <div className={transcriptOpen ? styles.assessmentCol : undefined}>
                                <SevenCsPanel
                                    sessionDeviceId={parseInt(deviceId)}
                                    sessionName={sessionName}
                                    deviceName={deviceName}
                                    singleColumn={transcriptOpen}
                                    transcriptOpen={transcriptOpen}
                                />
                            </div>
                            {transcriptOpen && (
                                <div className={styles.transcriptCol}>
                                    <TranscriptPanel
                                        deviceId={deviceId}
                                        onClose={() => handleTranscriptToggle(false)}
                                    />
                                </div>
                            )}
                        </div>

                        {/* Concept map — always full-width below, unaffected */}
                        <div className={styles.conceptMapSection}>
                            <h2 className={styles.sectionTitle}>Visual Scaffolding</h2>
                            <ConceptMapView
                                sessionId={deviceInfo?.sessionId || null}
                                sessionDeviceId={parseInt(deviceId)}
                            />
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default ContentArea;
