#!/usr/bin/env python3
"""Export study interaction logs for all 12 participants to markdown."""

import mysql.connector
import json
from datetime import datetime

DEFAULT_DIM_KEYS = {'climate', 'communication', 'compatibility', 'conflict', 'context', 'contribution', 'constructive'}

PARTICIPANTS = [
    'GVNU', 'XCCU', 'VUQW', 'CCKE', 'CEPT', 'YKKX',
    'QCAK', 'TKAY', 'XNCD', 'RQXF', 'MRKY', 'YHWY'
]

# Time filters: (participant, cutoff_type, cutoff_time)
# 'after' = only include events after this time
# 'before' = only include events before this time
TIME_FILTERS = {
    'GVNU': ('after', '2026-02-28 16:53:00'),
    'CEPT': ('before', '2026-02-28 18:50:00'),
    'QCAK': ('before', '2026-03-02 14:55:00'),
    'TKAY': ('before', '2026-03-04 07:31:00'),
}

# Session device ID to session name mapping
DEVICE_SESSION_NAMES = {}

def get_conn(db='discussion_capture'):
    return mysql.connector.connect(host='localhost', user='vagrant', password='vagrant', database=db)

def load_session_names():
    """Load device ID to session name mapping from a study DB (all share same sessions)."""
    conn = get_conn('study_NWRF')
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT sd.id as device_id, s.name as session_name
        FROM session_device sd
        JOIN session s ON sd.session_id = s.id
    """)
    # Count how many devices per session name to detect duplicates
    name_counts = {}
    rows = cur.fetchall()
    for row in rows:
        name_counts[row['session_name']] = name_counts.get(row['session_name'], 0) + 1

    # For sessions with multiple devices, append the device table ID
    device_index = {}
    for row in rows:
        name = row['session_name']
        if name_counts[name] > 1:
            device_index[name] = device_index.get(name, 0) + 1
            DEVICE_SESSION_NAMES[row['device_id']] = f"{name} (Group {device_index[name]})"
        else:
            DEVICE_SESSION_NAMES[row['device_id']] = name
    cur.close()
    conn.close()

def get_interaction_logs(participant):
    """Get filtered interaction logs for a participant."""
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    query = "SELECT timestamp, action_type, session_device_id, action_data FROM study_interaction_log WHERE study_user_id = %s"
    params = [participant]

    if participant in TIME_FILTERS:
        direction, cutoff = TIME_FILTERS[participant]
        if direction == 'after':
            query += " AND timestamp >= %s"
        else:
            query += " AND timestamp <= %s"
        params.append(cutoff)

    query += " ORDER BY timestamp"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_agent_conversations(participant):
    """Get agent messages from participant's isolated DB."""
    db_name = f"study_{participant}"
    try:
        conn = get_conn(db_name)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT role, content, conversation_id, created_at FROM agent_message ORDER BY created_at")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        return []

def get_custom_dimensions(participant):
    """Get custom dimensions added by participant, with schema updated_at as timestamp."""
    db_name = f"study_{participant}"
    try:
        conn = get_conn(db_name)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT dimensions, updated_at FROM dimension_schema WHERE is_default=1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return []
        dims = json.loads(row['dimensions']) if isinstance(row['dimensions'], str) else row['dimensions']
        updated_at = row['updated_at']
        custom = []
        for d in dims:
            if d.get('key') not in DEFAULT_DIM_KEYS:
                custom.append({
                    'timestamp': updated_at,
                    'name': d.get('name', d.get('key', '?')),
                    'description': d.get('description', ''),
                })
        return custom
    except Exception:
        return []

def get_dimension_deactivations(participant):
    """Detect default dimensions explicitly deactivated per session.
    Only flags default 7C dimensions missing from a session's analysis."""
    db_name = f"study_{participant}"
    try:
        conn = get_conn(db_name)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT session_device_id, analysis_summary, updated_at FROM seven_cs_analysis WHERE analysis_summary IS NOT NULL")
        deactivations = []
        for row in cur.fetchall():
            summary = json.loads(row['analysis_summary']) if isinstance(row['analysis_summary'], str) else row['analysis_summary']
            present_keys = set(summary.keys()) if summary else set()
            missing_defaults = DEFAULT_DIM_KEYS - present_keys
            for dim_key in sorted(missing_defaults):
                deactivations.append({
                    'timestamp': row['updated_at'],
                    'session_device_id': row['session_device_id'],
                    'dimension': dim_key,
                })
        cur.close()
        conn.close()
        return deactivations
    except Exception:
        return []

def get_score_diffs(participant):
    """Get score edit diffs from participant's isolated DB."""
    db_name = f"study_{participant}"
    try:
        conn = get_conn(db_name)
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT sca.session_device_id, sca.analysis_summary, sca.ai_baseline
            FROM seven_cs_analysis sca
            WHERE sca.ai_baseline IS NOT NULL
              AND sca.analysis_summary != sca.ai_baseline
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        diffs = []
        for row in rows:
            try:
                current = json.loads(row['analysis_summary']) if isinstance(row['analysis_summary'], str) else row['analysis_summary']
                baseline = json.loads(row['ai_baseline']) if isinstance(row['ai_baseline'], str) else row['ai_baseline']
                if not current or not baseline:
                    continue

                sid = row['session_device_id']
                session_label = DEVICE_SESSION_NAMES.get(sid, f"Device {sid}")
                changed_dims = []

                # Top-level keys are dimension names (climate, context, etc.)
                all_dims = set(list(current.keys()) + list(baseline.keys()))
                for dim in sorted(all_dims):
                    c_entry = current.get(dim, {})
                    b_entry = baseline.get(dim, {})
                    c_score = c_entry.get('score') if isinstance(c_entry, dict) else None
                    b_score = b_entry.get('score') if isinstance(b_entry, dict) else None

                    if c_score is not None and b_score is not None and c_score != b_score:
                        changed_dims.append((dim, b_score, c_score))
                    elif dim in current and dim not in baseline:
                        c_score = c_entry.get('score') if isinstance(c_entry, dict) else None
                        if c_score is not None:
                            changed_dims.append((dim, 'N/A (new)', c_score))

                if changed_dims:
                    diffs.append((session_label, changed_dims))
            except Exception:
                continue

        return diffs
    except Exception:
        return []

def format_action_data(action_type, action_data, session_device_id):
    """Format action data into a readable string."""
    details = []

    session_name = DEVICE_SESSION_NAMES.get(session_device_id, f"Device {session_device_id}" if session_device_id else "")

    if action_type == 'session_navigate' and session_name:
        details.append(session_name)
    elif action_type == 'artifact_card_click' and action_data:
        data = json.loads(action_data) if isinstance(action_data, str) else action_data
        details.append(f"type={data.get('type','?')}, tab={data.get('tab','?')}")
        if session_name:
            details.append(session_name)
    elif action_type == 'assessment_edit' and action_data:
        data = json.loads(action_data) if isinstance(action_data, str) else action_data
        dim = data.get('dimension', '?')
        old = data.get('old_value', '?')
        new = data.get('value', '?')
        details.append(f"{dim}: {old} -> {new}")
        if session_name:
            details.append(session_name)
    elif action_type == 'chat_query' and action_data:
        data = json.loads(action_data) if isinstance(action_data, str) else action_data
        query = data.get('query', data.get('message', ''))
        if query:
            truncated = query[:120] + '...' if len(query) > 120 else query
            details.append(f'"{truncated}"')
    elif action_type == 'chat_response' and action_data:
        data = json.loads(action_data) if isinstance(action_data, str) else action_data
        tools = data.get('tools_used', [])
        resp_time = data.get('response_time', None)
        parts = []
        if resp_time:
            parts.append(f"{resp_time:.1f}s")
        if tools:
            parts.append(f"{len(tools)} tool{'s' if len(tools)>1 else ''}: {', '.join(tools)}")
        if parts:
            details.append(', '.join(parts))
    elif action_type == 'concept_regenerate' and action_data:
        data = json.loads(action_data) if isinstance(action_data, str) else action_data
        if session_name:
            details.append(session_name)
        filters = data.get('filters', data.get('speaker_filter', ''))
        if filters:
            details.append(f"filters={filters}")
    elif action_type in ('transcript_open', 'transcript_close') and session_name:
        details.append(session_name)
    elif action_type == 'dimension_add':
        # Synthesized event — action_data is a dict with name and description
        if action_data and isinstance(action_data, dict):
            details.append(f"{action_data.get('name', '?')}: {action_data.get('description', '')}")
    elif action_type == 'dimension_deactivate':
        if action_data and isinstance(action_data, dict):
            details.append(action_data.get('dimension', '?'))
            if session_name:
                details.append(session_name)

    return ' | '.join(details) if details else ''

def export_participant(participant):
    """Generate markdown section for one participant."""
    lines = []
    lines.append(f"## {participant}")
    lines.append("")

    # Get data
    logs = get_interaction_logs(participant)
    custom_dims = get_custom_dimensions(participant)
    deactivations = get_dimension_deactivations(participant)
    conversations = get_agent_conversations(participant)
    score_diffs = get_score_diffs(participant)

    # Merge dimension_add events into logs
    for dim in custom_dims:
        logs.append({
            'timestamp': dim['timestamp'],
            'action_type': 'dimension_add',
            'session_device_id': None,
            'action_data': {'name': dim['name'], 'description': dim['description']},
        })

    # Merge dimension_deactivate events into logs
    for deact in deactivations:
        logs.append({
            'timestamp': deact['timestamp'],
            'action_type': 'dimension_deactivate',
            'session_device_id': deact['session_device_id'],
            'action_data': {'dimension': deact['dimension']},
        })

    logs.sort(key=lambda x: x['timestamp'])

    if not logs:
        lines.append("_No interaction logs found._")
        lines.append("")
        return '\n'.join(lines)

    # Summary stats
    first_ts = logs[0]['timestamp']
    last_ts = logs[-1]['timestamp']
    duration = last_ts - first_ts
    duration_min = duration.total_seconds() / 60

    action_counts = {}
    for log in logs:
        action_counts[log['action_type']] = action_counts.get(log['action_type'], 0) + 1

    sessions_visited = set()
    for log in logs:
        if log['session_device_id']:
            sessions_visited.add(log['session_device_id'])

    filter_note = ""
    if participant in TIME_FILTERS:
        direction, cutoff = TIME_FILTERS[participant]
        if direction == 'after':
            filter_note = f" (filtered: only events after {cutoff})"
        else:
            filter_note = f" (filtered: only events before {cutoff})"

    lines.append(f"**Study period**: {first_ts.strftime('%Y-%m-%d %H:%M:%S')} to {last_ts.strftime('%H:%M:%S')} ({duration_min:.0f} min){filter_note}")
    lines.append(f"**Total events**: {len(logs)}")
    unique_session_names = sorted(set(DEVICE_SESSION_NAMES.get(sid, str(sid)) for sid in sessions_visited))
    lines.append(f"**Sessions visited**: {len(unique_session_names)} — {', '.join(unique_session_names)}")
    lines.append("")

    # Action breakdown
    lines.append("**Action breakdown**:")
    for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {action}: {count}")
    lines.append("")

    # Chronological event log
    lines.append("### Event Log")
    lines.append("")
    lines.append("| Time | Action | Details |")
    lines.append("|------|--------|---------|")

    for log in logs:
        ts = log['timestamp'].strftime('%H:%M:%S')
        action = log['action_type']
        details = format_action_data(action, log['action_data'], log['session_device_id'])
        # Escape pipe characters in details
        details = details.replace('|', '\\|')
        lines.append(f"| {ts} | `{action}` | {details} |")

    lines.append("")

    # Agent conversations
    if conversations:
        lines.append("### Agent Conversations")
        lines.append("")

        current_conv = None
        for msg in conversations:
            conv_id = msg.get('conversation_id', 'default')
            if conv_id != current_conv:
                current_conv = conv_id
                lines.append(f"**Conversation {conv_id}**")
                lines.append("")

            role = msg['role']
            content = msg['content'] or ''
            ts = msg['created_at'].strftime('%H:%M:%S') if msg.get('created_at') else ''

            if role == 'user':
                lines.append(f"**User** ({ts}): {content}")
                lines.append("")
            elif role == 'assistant':
                # Truncate very long responses
                if len(content) > 500:
                    content = content[:500] + '... [truncated]'
                # Escape markdown headers in agent content to prevent section confusion
                content = content.replace('\n#', '\n\\#')
                lines.append(f"**Agent** ({ts}): {content}")
                lines.append("")

    # Score diffs
    if score_diffs:
        lines.append("### Score Edits (vs AI Baseline)")
        lines.append("")
        lines.append("| Session | Dimension | AI Score | User Score |")
        lines.append("|---------|-----------|----------|------------|")
        for session_label, dims in score_diffs:
            for dim, old, new in dims:
                lines.append(f"| {session_label} | {dim} | {old} | {new} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    return '\n'.join(lines)

def main():
    load_session_names()

    output = []
    output.append("# Study Interaction Logs — All 12 Participants")
    output.append("")
    output.append(f"_Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
    output.append("")
    output.append("**Participants**: " + ', '.join(PARTICIPANTS))
    output.append("")
    output.append("**Time filters applied**:")
    output.append("- GVNU: Only events after 16:53 on Feb 28 (earlier cluster was pre-study)")
    output.append("- CEPT: Only events before 18:50 on Feb 28 (3 post-study navigations excluded)")
    output.append("- QCAK: Only events before 14:55 on Mar 2 (1 post-study navigation excluded)")
    output.append("- TKAY: Only events before 07:31 on Mar 4 (1 post-study navigation excluded)")
    output.append("")
    output.append("**Action types**: chat_query, chat_response, session_navigate, artifact_card_click, transcript_open, transcript_close, assessment_edit, concept_regenerate")
    output.append("")
    output.append("---")
    output.append("")

    for p in PARTICIPANTS:
        print(f"Exporting {p}...")
        output.append(export_participant(p))

    with open('study_interaction_logs.md', 'w') as f:
        f.write('\n'.join(output))

    print(f"\nDone. Written to server/study_interaction_logs.md")

if __name__ == '__main__':
    main()
