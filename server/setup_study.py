#!/usr/bin/env python3
"""
Setup / Reset / Export script for CUI 2026 user study.

Usage:
  python setup_study.py --setup --devices 26,27,32,33,34,35 --participants 15
  python setup_study.py --reset P03
  python setup_study.py --export P03 --output ./exports/P03/
  python setup_study.py --teardown   # Remove all study databases

Requires: mysql.connector, chromadb (from project virtualenv)
Run from: /home/ubuntu/chemistry-dashboard/server/
"""
import argparse
import json
import logging
import os
import shutil
import sys

import mysql.connector

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAIN_DB = 'discussion_capture'
DB_HOST = 'localhost'
DB_USER = 'vagrant'
DB_PASS = 'vagrant'
STUDY_PASSWORD = os.environ.get('STUDY_PASSWORD', 'changeme')

# Characters for random IDs (excluding confusable: I, O, L, S, Z)
ID_CHARS = 'ABCDEFGHJKMNPQRTUVWXY'
MAPPING_FILE = './study_participants.json'

# Session IDs for the study (parent sessions)
STUDY_SESSION_IDS = [26, 27, 30]

# Default study device IDs
DEFAULT_DEVICE_IDS = [26, 27, 32, 33, 34, 35]

# Dimensions to strip from participant copies (custom, not part of 7Cs)
STRIP_DIMENSIONS = ['depth', 'creativity']


def get_connection(database=MAIN_DB):
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS,
        database=database
    )


def get_admin_connection():
    """Connection without specific database for admin operations."""
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS,
    )


# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------

def _generate_random_id(existing_ids, length=4):
    """Generate a random ID that doesn't collide with existing ones."""
    import random
    while True:
        rid = ''.join(random.choices(ID_CHARS, k=length))
        if rid not in existing_ids:
            return rid


def create_study_users(conn, num_participants):
    """Create study user accounts with random 4-letter IDs in the main database."""
    import hashlib, os as _os, binascii
    cursor = conn.cursor(dictionary=True)

    # Check for existing study users
    cursor.execute("SELECT email FROM user WHERE role = 'study'")
    existing = {row['email'] for row in cursor.fetchall()}

    if existing:
        logger.info(f"  {len(existing)} study users already exist: {sorted(existing)}")
        logger.info("  Run --teardown first if you want to regenerate IDs")
        return sorted(existing)

    # Generate unique random IDs
    created = []
    all_ids = set()
    for i in range(1, num_participants + 1):
        pid = _generate_random_id(all_ids)
        all_ids.add(pid)

        salt = hashlib.sha256(_os.urandom(60)).hexdigest()
        salt_bytes = salt.encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', STUDY_PASSWORD.encode('utf-8'), salt_bytes, 100000)
        hash_pass = binascii.hexlify(pwdhash).decode('ascii')

        cursor.execute("""
            INSERT INTO user (email, role, salt, hash_pass, change_password, locked, creation_date)
            VALUES (%s, 'study', %s, %s, 0, 0, NOW())
        """, (pid, salt, hash_pass))
        created.append(pid)

    conn.commit()
    cursor.close()

    # Save mapping to file for researcher reference
    mapping = {f'Participant {i+1}': pid for i, pid in enumerate(created)}
    mapping['_password'] = STUDY_PASSWORD
    with open(MAPPING_FILE, 'w') as f:
        json.dump(mapping, f, indent=2)

    logger.info(f"  Created {len(created)} study user accounts")
    logger.info(f"  Mapping saved to {MAPPING_FILE}")
    logger.info(f"  Password for all: {STUDY_PASSWORD}")
    logger.info("")
    for i, pid in enumerate(created):
        logger.info(f"    Participant {i+1:2d} → {pid}")

    return created


def create_interaction_log_table(conn):
    """Create the study_interaction_log table in the main database."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_interaction_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            study_user_id VARCHAR(10) NOT NULL,
            timestamp DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
            phase VARCHAR(20) DEFAULT 'unknown',
            action_type VARCHAR(50) NOT NULL,
            session_device_id INT,
            action_data JSON,
            INDEX idx_user_ts (study_user_id, timestamp),
            INDEX idx_user_action (study_user_id, action_type)
        )
    """)
    conn.commit()
    cursor.close()
    logger.info("  study_interaction_log table ready")


def get_table_create_statements(conn):
    """Get CREATE TABLE statements for all tables in the current database."""
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]

    creates = {}
    for table in tables:
        cursor.execute(f"SHOW CREATE TABLE `{table}`")
        row = cursor.fetchone()
        creates[table] = row[1]

    cursor.close()
    return creates


def _strip_custom_dimensions(study_conn, device_ids):
    """Remove non-7Cs dimensions (depth, creativity, etc.) from participant copy.

    1. Removes keys from the dimension_schema pool.
    2. Removes assessed data from analysis_summary and ai_baseline.
    """
    if not STRIP_DIMENSIONS:
        return

    cursor = study_conn.cursor()

    # 1. Remove from dimension pool
    for dim_key in STRIP_DIMENSIONS:
        # Find the index of this key and remove it
        cursor.execute("""
            SELECT JSON_LENGTH(dimensions) as len FROM dimension_schema WHERE is_default = 1
        """)
        row = cursor.fetchone()
        if not row:
            continue
        pool_len = row[0]
        # Walk backwards to avoid index shifting
        for i in range(pool_len - 1, -1, -1):
            cursor.execute(f"""
                SELECT JSON_UNQUOTE(JSON_EXTRACT(dimensions, '$[{i}].key')) as k
                FROM dimension_schema WHERE is_default = 1
            """)
            k_row = cursor.fetchone()
            if k_row and k_row[0] == dim_key:
                cursor.execute(f"""
                    UPDATE dimension_schema
                    SET dimensions = JSON_REMOVE(dimensions, '$[{i}]')
                    WHERE is_default = 1
                """)
                break

    # 2. Remove from assessment data (analysis_summary + ai_baseline)
    for dim_key in STRIP_DIMENSIONS:
        cursor.execute(f"""
            UPDATE seven_cs_analysis
            SET analysis_summary = JSON_REMOVE(analysis_summary, '$.{dim_key}'),
                ai_baseline = JSON_REMOVE(ai_baseline, '$.{dim_key}')
            WHERE JSON_CONTAINS_PATH(analysis_summary, 'one', '$.{dim_key}')
        """)

    study_conn.commit()
    cursor.close()

    stripped = ', '.join(STRIP_DIMENSIONS)
    logger.info(f"    Stripped custom dimensions: {stripped}")


def setup_participant_db(admin_conn, main_conn, pid, device_ids):
    """Create and populate a participant's isolated database."""
    study_db = f'study_{pid}'
    cursor_admin = admin_conn.cursor()

    # Create database
    cursor_admin.execute(f"DROP DATABASE IF EXISTS `{study_db}`")
    cursor_admin.execute(f"CREATE DATABASE `{study_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor_admin.execute(f"GRANT ALL PRIVILEGES ON `{study_db}`.* TO '{DB_USER}'@'localhost'")
    cursor_admin.execute("FLUSH PRIVILEGES")
    cursor_admin.close()

    logger.info(f"  Created database {study_db}")

    # Clone schema from main DB
    creates = get_table_create_statements(main_conn)
    study_conn = get_connection(study_db)
    study_cursor = study_conn.cursor()

    # Disable FK checks during schema creation
    study_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    # Tables to create — ALL tables from main DB so SQLAlchemy relationships
    # (e.g. User.api_client lazy='joined') never hit a missing table.
    tables_to_create = [
        'user', 'api_client', 'folder', 'topic_model',
        'session', 'device', 'session_device',
        'seven_cs_analysis', 'seven_cs_coded_segment',
        'concept_session', 'concept_node', 'concept_edge', 'concept_cluster',
        'cluster_node_mapping', 'dimension_score_edit',
        'transcript', 'speaker', 'speaker_transcript_metrics',
        'dimension_schema',
        'agent_conversation', 'agent_message',
        'discussion_pulse',
        'agent_response', 'expert_agent_rating',
        'expert_7c_annotation', 'expert_concept_map_rating',
        'keyword', 'keyword_list', 'keyword_list_item', 'keyword_usage',
        'alembic_version',
    ]

    for table in tables_to_create:
        if table in creates:
            try:
                study_cursor.execute(creates[table])
            except mysql.connector.errors.ProgrammingError as e:
                if 'already exists' not in str(e):
                    logger.warning(f"    Skipping table {table}: {e}")

    study_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    study_conn.commit()

    # Now copy data — disable FK checks for the entire copy phase
    main_cursor = main_conn.cursor(dictionary=True)
    study_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    device_ids_str = ','.join(str(d) for d in device_ids)
    session_ids_str = ','.join(str(s) for s in STUDY_SESSION_IDS)

    # 1. Users — session owner (id=1) + this participant
    main_cursor.execute("SELECT id FROM user WHERE email = %s", (pid,))
    user_row = main_cursor.fetchone()
    participant_user_id = user_row['id'] if user_row else None
    user_ids = {1}  # Always include session owner (llmblinc)
    if participant_user_id:
        user_ids.add(participant_user_id)
    user_ids_str = ','.join(str(u) for u in user_ids)
    _copy_rows(main_cursor, study_cursor,
               f"SELECT * FROM user WHERE id IN ({user_ids_str})",
               'user')

    # 2. Sessions
    _copy_rows(main_cursor, study_cursor,
               f"SELECT * FROM session WHERE id IN ({session_ids_str})",
               'session')

    # 2b. Re-assign session ownership to this participant
    if participant_user_id:
        study_cursor.execute(
            f"UPDATE session SET owner_id = %s WHERE id IN ({session_ids_str})",
            (participant_user_id,))

    # 3. Session devices
    _copy_rows(main_cursor, study_cursor,
               f"SELECT * FROM session_device WHERE id IN ({device_ids_str})",
               'session_device')

    # 4. Seven Cs analysis
    _copy_rows(main_cursor, study_cursor,
               f"SELECT * FROM seven_cs_analysis WHERE session_device_id IN ({device_ids_str})",
               'seven_cs_analysis')

    # 5. Seven Cs coded segments
    _copy_rows(main_cursor, study_cursor,
               f"""SELECT cs.* FROM seven_cs_coded_segment cs
                   JOIN seven_cs_analysis a ON cs.analysis_id = a.id
                   WHERE a.session_device_id IN ({device_ids_str})""",
               'seven_cs_coded_segment')

    # 6. Speakers (before concept nodes which reference them)
    _copy_rows(main_cursor, study_cursor,
               f"SELECT * FROM speaker WHERE session_device_id IN ({device_ids_str})",
               'speaker')

    # 7. Concept sessions
    _copy_rows(main_cursor, study_cursor,
               f"SELECT * FROM concept_session WHERE session_device_id IN ({device_ids_str})",
               'concept_session')

    # 8. Concept nodes (depend on concept_session, speaker)
    _copy_rows(main_cursor, study_cursor,
               f"""SELECT cn.* FROM concept_node cn
                   JOIN concept_session cs ON cn.concept_session_id = cs.id
                   WHERE cs.session_device_id IN ({device_ids_str})""",
               'concept_node')

    # 9. Concept clusters
    _copy_rows(main_cursor, study_cursor,
               f"""SELECT cc.* FROM concept_cluster cc
                   JOIN concept_session cs ON cc.concept_session_id = cs.id
                   WHERE cs.session_device_id IN ({device_ids_str})""",
               'concept_cluster')

    # 10. Concept edges (depend on concept_node, concept_session)
    _copy_rows(main_cursor, study_cursor,
               f"""SELECT ce.* FROM concept_edge ce
                   JOIN concept_session cs ON ce.concept_session_id = cs.id
                   WHERE cs.session_device_id IN ({device_ids_str})""",
               'concept_edge')

    # 11. Cluster-node mapping
    _copy_rows(main_cursor, study_cursor,
               f"""SELECT cnm.* FROM cluster_node_mapping cnm
                   JOIN concept_cluster cc ON cnm.cluster_id = cc.id
                   JOIN concept_session cs ON cc.concept_session_id = cs.id
                   WHERE cs.session_device_id IN ({device_ids_str})""",
               'cluster_node_mapping')

    # 12. Transcripts
    _copy_rows(main_cursor, study_cursor,
               f"SELECT * FROM transcript WHERE session_device_id IN ({device_ids_str})",
               'transcript')

    # 13. Dimension schema (full copy)
    _copy_rows(main_cursor, study_cursor,
               "SELECT * FROM dimension_schema",
               'dimension_schema')

    # 14. Alembic version (so migrations don't re-run)
    _copy_rows(main_cursor, study_cursor,
               "SELECT * FROM alembic_version",
               'alembic_version')

    study_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    study_conn.commit()
    main_cursor.close()

    # Post-copy cleanup: strip non-7Cs dimensions from participant copy
    _strip_custom_dimensions(study_conn, device_ids)

    study_conn.close()

    logger.info(f"  Populated {study_db} with data for devices {device_ids}")


def _copy_rows(src_cursor, dst_cursor, query, table_name):
    """Copy rows from source query into destination table."""
    src_cursor.execute(query)
    rows = src_cursor.fetchall()
    if not rows:
        return 0

    columns = list(rows[0].keys())
    placeholders = ', '.join(['%s'] * len(columns))
    col_names = ', '.join(f'`{c}`' for c in columns)
    insert_sql = f"INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders})"

    for row in rows:
        values = tuple(row[c] for c in columns)
        try:
            dst_cursor.execute(insert_sql, values)
        except mysql.connector.errors.IntegrityError:
            pass  # Skip duplicates on re-run

    logger.info(f"    {table_name}: {len(rows)} rows copied")
    return len(rows)


def setup_chromadb(pid, device_ids):
    """Create and populate ChromaDB for a participant."""
    chroma_path = f'./chroma_db_{pid}'

    # Remove existing
    if os.path.exists(chroma_path):
        shutil.rmtree(chroma_path)

    # We need Flask app context for the serializer and RAG service
    # Import here to avoid circular imports at module level
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from session_serializer import SessionSerializer
    from rag_service import RAGService
    from speaker_serializer import SpeakerSerializer

    serializer = SessionSerializer()
    rag = RAGService(persist_directory=chroma_path)
    speaker_serializer = SpeakerSerializer()

    indexed = 0
    for device_id in device_ids:
        docs = serializer.serialize_all(device_id)
        if not docs:
            logger.warning(f"    No data for device {device_id}")
            continue

        metadata = docs.get('metadata', {})

        if docs.get('transcript'):
            rag.index_session_transcript(device_id, docs['transcript'], metadata)
        if docs.get('concepts'):
            rag.index_session_concepts(device_id, docs['concepts'], metadata)
        if docs.get('seven_c'):
            rag.index_session_7c(device_id, docs['seven_c'], metadata)
        indexed += 1

    # Index speakers
    from tables.speaker import Speaker
    speakers = Speaker.query.filter(
        Speaker.session_device_id.in_(device_ids)
    ).all()
    aliases = set(s.alias for s in speakers if s.alias)

    for alias in aliases:
        try:
            serialized = speaker_serializer.serialize_speaker(alias)
            if serialized:
                rag.index_speaker(alias, serialized)
        except Exception as e:
            logger.error(f"    Failed to index speaker {alias}: {e}")

    logger.info(f"  ChromaDB {chroma_path}: indexed {indexed} devices, {len(aliases)} speakers")


def run_setup(device_ids, num_participants):
    """Full setup: create users, databases, ChromaDB, logging table."""
    logger.info("=" * 60)
    logger.info("CUI 2026 Study Setup")
    logger.info(f"  Participants: {num_participants}")
    logger.info(f"  Devices: {device_ids}")
    logger.info("=" * 60)

    main_conn = get_connection(MAIN_DB)
    admin_conn = get_admin_connection()

    # Step 1: Create user accounts
    logger.info("\n[Step 1] Creating study user accounts...")
    pids = create_study_users(main_conn, num_participants)

    # Step 2: Create interaction log table
    logger.info("\n[Step 2] Creating interaction log table...")
    create_interaction_log_table(main_conn)

    # Step 3: Create participant databases
    logger.info("\n[Step 3] Creating participant databases...")
    for pid in pids:
        logger.info(f"\n  --- Setting up {pid} ---")
        setup_participant_db(admin_conn, main_conn, pid, device_ids)

    main_conn.close()
    admin_conn.close()

    # Step 4: Create ChromaDB instances (requires Flask app context)
    logger.info("\n[Step 4] Creating ChromaDB instances...")
    # Need app context for ORM queries in serializers
    from app import app, db
    with app.app_context():
        for pid in pids:
            logger.info(f"\n  --- ChromaDB for {pid} ---")
            # Switch to participant DB for serializer reads
            db.session.execute(db.text(f'USE study_{pid}'))
            setup_chromadb(pid, device_ids)
        # Reset to main DB
        db.session.execute(db.text(f'USE {MAIN_DB}'))

    logger.info("\n" + "=" * 60)
    logger.info("Setup complete!")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# RESET
# ---------------------------------------------------------------------------

def run_reset(pid, device_ids):
    """Reset a participant: drop & recreate their DB and ChromaDB."""
    study_db = f'study_{pid}'
    logger.info(f"Resetting participant {pid}...")

    main_conn = get_connection(MAIN_DB)
    admin_conn = get_admin_connection()

    # Recreate database
    setup_participant_db(admin_conn, main_conn, pid, device_ids)

    # Mark old interaction logs
    cursor = main_conn.cursor()
    cursor.execute("""
        UPDATE study_interaction_log
        SET phase = CONCAT('reset_', phase)
        WHERE study_user_id = %s AND phase NOT LIKE 'reset_%%'
    """, (pid,))
    main_conn.commit()
    cursor.close()

    main_conn.close()
    admin_conn.close()

    # Recreate ChromaDB
    from app import app, db
    with app.app_context():
        db.session.execute(db.text(f'USE {study_db}'))
        setup_chromadb(pid, device_ids)
        db.session.execute(db.text(f'USE {MAIN_DB}'))

    logger.info(f"Reset complete for {pid}")


# ---------------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------------

def run_export(pid, output_dir):
    """Export a participant's data for analysis."""
    study_db = f'study_{pid}'
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Exporting {pid} data to {output_dir}...")

    main_conn = get_connection(MAIN_DB)
    study_conn = get_connection(study_db)

    # 1. Interaction logs
    cursor = main_conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM study_interaction_log
        WHERE study_user_id = %s
        ORDER BY timestamp
    """, (pid,))
    logs = cursor.fetchall()
    cursor.close()

    # Convert datetime objects for JSON
    for log in logs:
        for key in log:
            if hasattr(log[key], 'isoformat'):
                log[key] = log[key].isoformat()

    with open(os.path.join(output_dir, 'interaction_logs.json'), 'w') as f:
        json.dump(logs, f, indent=2, default=str)
    logger.info(f"  Exported {len(logs)} interaction logs")

    # 2. Agent conversations and messages
    study_cursor = study_conn.cursor(dictionary=True)
    study_cursor.execute("SELECT * FROM agent_conversation ORDER BY created_at")
    conversations = study_cursor.fetchall()

    for conv in conversations:
        for key in conv:
            if hasattr(conv[key], 'isoformat'):
                conv[key] = conv[key].isoformat()
        study_cursor.execute("""
            SELECT * FROM agent_message
            WHERE conversation_id = %s
            ORDER BY created_at
        """, (conv['id'],))
        msgs = study_cursor.fetchall()
        for msg in msgs:
            for key in msg:
                if hasattr(msg[key], 'isoformat'):
                    msg[key] = msg[key].isoformat()
        conv['messages'] = msgs

    with open(os.path.join(output_dir, 'conversations.json'), 'w') as f:
        json.dump(conversations, f, indent=2, default=str)
    logger.info(f"  Exported {len(conversations)} conversations")

    # 3. Final assessment state
    study_cursor.execute("""
        SELECT session_device_id, analysis_summary, ai_baseline, created_at, analysis_status
        FROM seven_cs_analysis
        ORDER BY session_device_id
    """)
    analyses = study_cursor.fetchall()

    for a in analyses:
        for key in a:
            if hasattr(a[key], 'isoformat'):
                a[key] = a[key].isoformat()
            elif isinstance(a[key], (bytes, bytearray)):
                a[key] = a[key].decode('utf-8')

    with open(os.path.join(output_dir, 'assessments.json'), 'w') as f:
        json.dump(analyses, f, indent=2, default=str)
    logger.info(f"  Exported {len(analyses)} assessments")

    # 4. Edit diffs (analysis_summary vs ai_baseline)
    diffs = []
    for a in analyses:
        summary = json.loads(a['analysis_summary']) if isinstance(a['analysis_summary'], str) else a['analysis_summary']
        baseline = json.loads(a['ai_baseline']) if isinstance(a['ai_baseline'], str) else a['ai_baseline']

        if not summary or not baseline:
            continue

        for dim_key in summary:
            s = summary.get(dim_key, {})
            b = baseline.get(dim_key, {})
            if s != b:
                diffs.append({
                    'session_device_id': a['session_device_id'],
                    'dimension': dim_key,
                    'baseline_score': b.get('score'),
                    'final_score': s.get('score'),
                    'explanation_changed': s.get('explanation') != b.get('explanation'),
                    'evidence_changed': s.get('evidence') != b.get('evidence'),
                })

    with open(os.path.join(output_dir, 'edit_diffs.json'), 'w') as f:
        json.dump(diffs, f, indent=2)
    logger.info(f"  Exported {len(diffs)} edit diffs")

    # 5. Concept map final state
    study_cursor.execute("""
        SELECT cs.session_device_id,
               (SELECT COUNT(*) FROM concept_node cn WHERE cn.concept_session_id = cs.id) as node_count,
               (SELECT COUNT(*) FROM concept_edge ce WHERE ce.concept_session_id = cs.id) as edge_count,
               cs.generation_status
        FROM concept_session cs
        ORDER BY cs.session_device_id
    """)
    concept_summary = study_cursor.fetchall()
    with open(os.path.join(output_dir, 'concept_maps.json'), 'w') as f:
        json.dump(concept_summary, f, indent=2, default=str)
    logger.info(f"  Exported {len(concept_summary)} concept map summaries")

    study_cursor.close()
    study_conn.close()
    main_conn.close()

    logger.info(f"Export complete: {output_dir}")


# ---------------------------------------------------------------------------
# TEARDOWN
# ---------------------------------------------------------------------------

def run_teardown():
    """Remove all study databases, ChromaDB directories, and user accounts."""
    logger.info("Tearing down study infrastructure...")

    main_conn = get_connection(MAIN_DB)
    main_cursor = main_conn.cursor(dictionary=True)

    # Find all study users by role
    main_cursor.execute("SELECT email FROM user WHERE role = 'study'")
    study_users = [row['email'] for row in main_cursor.fetchall()]

    if not study_users:
        logger.info("  No study users found")
        main_cursor.close()
        main_conn.close()
        return

    admin_conn = get_admin_connection()
    admin_cursor = admin_conn.cursor()

    for pid in study_users:
        study_db = f'study_{pid}'
        chroma_path = f'./chroma_db_{pid}'

        admin_cursor.execute(f"DROP DATABASE IF EXISTS `{study_db}`")
        logger.info(f"  Dropped database {study_db}")

        if os.path.exists(chroma_path):
            shutil.rmtree(chroma_path)
            logger.info(f"  Removed {chroma_path}")

    admin_cursor.close()
    admin_conn.close()

    # Delete study user accounts
    main_cursor.execute("DELETE FROM user WHERE role = 'study'")
    main_conn.commit()
    logger.info(f"  Deleted {len(study_users)} study user accounts")

    main_cursor.close()
    main_conn.close()

    # Remove mapping file
    if os.path.exists(MAPPING_FILE):
        os.remove(MAPPING_FILE)
        logger.info(f"  Removed {MAPPING_FILE}")

    logger.info("Teardown complete")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='CUI 2026 User Study Setup')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--setup', action='store_true', help='Full setup')
    group.add_argument('--reset', metavar='PID', help='Reset participant (e.g. XKRM)')
    group.add_argument('--export', metavar='PID', help='Export participant data (e.g. XKRM)')
    group.add_argument('--teardown', action='store_true', help='Remove all study data')

    parser.add_argument('--devices', default=','.join(str(d) for d in DEFAULT_DEVICE_IDS),
                        help='Comma-separated device IDs')
    parser.add_argument('--participants', type=int, default=15,
                        help='Number of participants')
    parser.add_argument('--output', default='./exports',
                        help='Export output directory')

    args = parser.parse_args()
    device_ids = [int(d.strip()) for d in args.devices.split(',')]

    if args.setup:
        run_setup(device_ids, args.participants)
    elif args.reset:
        run_reset(args.reset, device_ids)
    elif args.export:
        out_dir = os.path.join(args.output, args.export)
        run_export(args.export, out_dir)
    elif args.teardown:
        run_teardown()


if __name__ == '__main__':
    main()
