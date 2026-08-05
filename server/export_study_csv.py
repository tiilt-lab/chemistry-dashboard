#!/usr/bin/env python3
"""Export study interaction logs to CSV — user actions only."""

import csv
import mysql.connector
import json

PARTICIPANTS = [
    'GVNU', 'XCCU', 'VUQW', 'CCKE', 'CEPT', 'YKKX',
    'QCAK', 'TKAY', 'XNCD', 'RQXF', 'MRKY', 'YHWY'
]

TIME_FILTERS = {
    'GVNU': ('after', '2026-02-28 16:53:00'),
    'CEPT': ('before', '2026-02-28 18:50:00'),
    'QCAK': ('before', '2026-03-02 14:55:00'),
    'TKAY': ('before', '2026-03-04 07:31:00'),
}

CSV_ACTION_TYPES = ('chat_query', 'assessment_edit', 'concept_regenerate', 'session_navigate', 'artifact_card_click')

DEFAULT_DIM_KEYS = {'climate', 'communication', 'compatibility', 'conflict', 'context', 'contribution', 'constructive'}
DEVICE_SESSION_NAMES = {}

def get_conn(db='discussion_capture'):
    return mysql.connector.connect(host='localhost', user='vagrant', password='vagrant', database=db)

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

def load_session_names():
    conn = get_conn('study_NWRF')
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT sd.id as device_id, s.name as session_name
        FROM session_device sd
        JOIN session s ON sd.session_id = s.id
    """)
    name_counts = {}
    rows = cur.fetchall()
    for row in rows:
        name_counts[row['session_name']] = name_counts.get(row['session_name'], 0) + 1
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

def format_details(action_type, action_data, session_device_id):
    session_name = DEVICE_SESSION_NAMES.get(session_device_id, '')
    data = {}
    if action_data:
        data = json.loads(action_data) if isinstance(action_data, str) else action_data

    if action_type == 'chat_query':
        return data.get('query', data.get('message', ''))
    elif action_type == 'assessment_edit':
        dim = data.get('dimension', '?')
        old = data.get('old_value', '?')
        new = data.get('value', '?')
        return f"{dim}: {old} -> {new}"
    elif action_type == 'concept_regenerate':
        filters = data.get('filters', data.get('speaker_filter', ''))
        return f"filters={filters}" if filters else ''
    elif action_type == 'artifact_card_click':
        return f"type={data.get('type','?')}, tab={data.get('tab','?')}"
    elif action_type == 'session_navigate':
        return ''
    return ''

def main():
    load_session_names()

    with open('study_interaction_logs.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['participant', 'timestamp', 'action_type', 'session_name', 'details'])

        for participant in PARTICIPANTS:
            conn = get_conn()
            cur = conn.cursor(dictionary=True)

            placeholders = ','.join(['%s'] * len(CSV_ACTION_TYPES))
            query = f"SELECT timestamp, action_type, session_device_id, action_data FROM study_interaction_log WHERE study_user_id = %s AND action_type IN ({placeholders})"
            params = [participant] + list(CSV_ACTION_TYPES)

            if participant in TIME_FILTERS:
                direction, cutoff = TIME_FILTERS[participant]
                if direction == 'after':
                    query += " AND timestamp >= %s"
                else:
                    query += " AND timestamp <= %s"
                params.append(cutoff)

            query += " ORDER BY timestamp"
            cur.execute(query, params)

            # Build combined event list: interaction logs + synthesized dimension_add events
            events = []
            for row in cur.fetchall():
                session_name = DEVICE_SESSION_NAMES.get(row['session_device_id'], '')
                details = format_details(row['action_type'], row['action_data'], row['session_device_id'])
                events.append((row['timestamp'], row['action_type'], session_name, details))

            # Add custom dimension events
            for dim in get_custom_dimensions(participant):
                events.append((
                    dim['timestamp'],
                    'dimension_add',
                    '',
                    f"{dim['name']}: {dim['description']}",
                ))

            # Add dimension deactivation events
            for deact in get_dimension_deactivations(participant):
                session_name = DEVICE_SESSION_NAMES.get(deact['session_device_id'], '')
                events.append((
                    deact['timestamp'],
                    'dimension_deactivate',
                    session_name,
                    deact['dimension'],
                ))

            # Sort by timestamp
            events.sort(key=lambda e: e[0])

            for ts, action_type, session_name, details in events:
                writer.writerow([
                    participant,
                    ts.strftime('%Y-%m-%d %H:%M:%S'),
                    action_type,
                    session_name,
                    details,
                ])

            cur.close()
            conn.close()
            print(f"Exported {participant}")

    print("\nDone. Written to server/study_interaction_logs.csv")

if __name__ == '__main__':
    main()
