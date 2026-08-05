/**
 * Study interaction logging — fire-and-forget POST to /api/v1/study/log.
 * Non-study users are silently ignored by the server.
 */

export function logStudyAction(actionType, data = {}) {
    fetch('/api/v1/study/log', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_type: actionType, ...data }),
    }).catch(() => {}); // fire-and-forget
}
