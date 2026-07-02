import sqlite3

def main():
    db_path = r"c:\Users\User\Documents\NEW_VERSION\football_intelligence.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List of foreign key indexes to create safely
    # Format: (table_name, column_name, index_name)
    fk_indexes = [
        ("users", "institution_id", "idx_users_institution_id"),
        ("user_sessions", "user_id", "idx_user_sessions_user_id"),
        ("players", "institution_id", "idx_players_institution_id_fk"),
        ("players", "team_id", "idx_players_team_id"),
        ("teams", "institution_id", "idx_teams_institution_id"),
        ("training_sessions", "institution_id", "idx_training_sessions_institution_id"),
        ("training_sessions", "team_id", "idx_training_sessions_team_id"),
        ("medical_records", "player_id", "idx_medical_records_player_id"),
        ("attendance", "institution_id", "idx_attendance_institution_id"),
        ("attendance", "player_id", "idx_attendance_player_id_fk"),
        ("attendance", "training_session_id", "idx_attendance_training_session_id"),
        ("transfers", "player_id", "idx_transfers_player_id"),
        ("transfers", "from_institution_id", "idx_transfers_from_institution_id"),
        ("transfers", "to_institution_id", "idx_transfers_to_institution_id"),
        ("awards", "competition_id", "idx_awards_competition_id"),
        ("awards", "player_id", "idx_awards_player_id"),
        ("player_votes", "player_id", "idx_player_votes_player_id"),
        ("player_votes", "voter_id", "idx_player_votes_voter_id"),
        ("player_votes", "competition_id", "idx_player_votes_competition_id"),
        ("matches", "competition_id", "idx_matches_competition_id"),
        ("matches", "home_team_id", "idx_matches_home_team_id"),
        ("matches", "away_team_id", "idx_matches_away_team_id"),
        ("disciplinary_history", "match_id", "idx_disciplinary_history_match_id"),
        ("disciplinary_history", "player_id", "idx_disciplinary_history_player_id"),
        ("match_events", "match_id", "idx_match_events_match_id_fk"),
        ("match_events", "player_id", "idx_match_events_player_id_fk"),
        ("match_events", "editor_id", "idx_match_events_editor_id"),
        ("player_stats", "player_id", "idx_player_stats_player_id_fk"),
        ("player_stats", "match_id", "idx_player_stats_match_id_fk"),
        ("ai_analysis", "player_id", "idx_ai_analysis_player_id_fk"),
        ("ai_analysis", "match_id", "idx_ai_analysis_match_id_fk"),
        ("match_analytics", "match_id", "idx_match_analytics_match_id"),
        ("fixtures", "match_id", "idx_fixtures_match_id"),
        ("fixtures", "approved_by_id", "idx_fixtures_approved_by_id"),
        ("live_sessions", "match_id", "idx_live_sessions_match_id"),
        ("match_squads", "match_id", "idx_match_squads_match_id"),
        ("match_squads", "player_id", "idx_match_squads_player_id"),
        ("audit_logs", "match_id", "idx_audit_logs_match_id"),
        ("tracking_frames", "match_id", "idx_tracking_frames_match_id"),
        ("tactical_snapshots", "match_id", "idx_tactical_snapshots_match_id"),
        ("match_sessions", "match_id", "idx_match_sessions_match_id"),
        ("match_sessions", "api_key_id", "idx_match_sessions_api_key_id"),
        ("idempotency_keys", "user_id", "idx_idempotency_keys_user_id"),
    ]
    
    print("Applying missing foreign key indexes to SQLite database...")
    for table, col, idx_name in fk_indexes:
        try:
            sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})"
            cursor.execute(sql)
            print(f"  Applied index: {idx_name} on {table}({col})")
        except Exception as e:
            print(f"  Error creating index {idx_name} on {table}({col}): {e}")
            
    conn.commit()
    conn.close()
    print("Database index application complete!")

if __name__ == "__main__":
    main()
