package postgres

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// HeartbeatRepository implements domain.HeartbeatRepository
type HeartbeatRepository struct {
	db *DB
}

func NewHeartbeatRepository(db *DB) *HeartbeatRepository {
	return &HeartbeatRepository{db: db}
}

func (r *HeartbeatRepository) RecordHeartbeat(ctx context.Context, heartbeat *domain.AgentHeartbeat) error {
	query := `
		INSERT INTO agent_heartbeats (id, agent_id, checked_tasks, checked_dms, checked_feed, checked_skill_update,
			tasks_found, dms_found, actions_taken, skill_version)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		RETURNING created_at`

	heartbeat.ID = uuid.New()
	return r.db.Pool.QueryRow(ctx, query,
		heartbeat.ID, heartbeat.AgentID,
		heartbeat.CheckedTasks, heartbeat.CheckedDMs, heartbeat.CheckedFeed, heartbeat.CheckedSkillUpdate,
		heartbeat.TasksFound, heartbeat.DMsFound, heartbeat.ActionsTaken, heartbeat.SkillVersion,
	).Scan(&heartbeat.CreatedAt)
}

func (r *HeartbeatRepository) GetAgentHeartbeats(ctx context.Context, agentID uuid.UUID, limit int) ([]*domain.AgentHeartbeat, error) {
	query := `
		SELECT id, agent_id, checked_tasks, checked_dms, checked_feed, checked_skill_update,
			tasks_found, dms_found, actions_taken, skill_version, created_at
		FROM agent_heartbeats WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2`

	rows, err := r.db.Pool.Query(ctx, query, agentID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var heartbeats []*domain.AgentHeartbeat
	for rows.Next() {
		h := &domain.AgentHeartbeat{}
		err := rows.Scan(&h.ID, &h.AgentID, &h.CheckedTasks, &h.CheckedDMs, &h.CheckedFeed, &h.CheckedSkillUpdate,
			&h.TasksFound, &h.DMsFound, &h.ActionsTaken, &h.SkillVersion, &h.CreatedAt)
		if err != nil {
			return nil, err
		}
		heartbeats = append(heartbeats, h)
	}
	return heartbeats, nil
}

func (r *HeartbeatRepository) GetLatestSkillVersion(ctx context.Context) (*domain.SkillVersion, error) {
	query := `
		SELECT id, version, beceriler_md, racon_md, yoklama_md, changelog, is_latest, is_deprecated, created_at
		FROM skill_versions WHERE is_latest = TRUE LIMIT 1`

	sv := &domain.SkillVersion{}
	err := r.db.Pool.QueryRow(ctx, query).Scan(
		&sv.ID, &sv.Version, &sv.BecerilerMD, &sv.RaconMD, &sv.YoklamaMD,
		&sv.Changelog, &sv.IsLatest, &sv.IsDeprecated, &sv.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.NewNotFoundError("skill_version_not_found", "No skill version found")
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get latest skill version: %w", err)
	}
	return sv, nil
}

func (r *HeartbeatRepository) GetSkillVersion(ctx context.Context, version string) (*domain.SkillVersion, error) {
	query := `
		SELECT id, version, beceriler_md, racon_md, yoklama_md, changelog, is_latest, is_deprecated, created_at
		FROM skill_versions WHERE version = $1`

	sv := &domain.SkillVersion{}
	err := r.db.Pool.QueryRow(ctx, query, version).Scan(
		&sv.ID, &sv.Version, &sv.BecerilerMD, &sv.RaconMD, &sv.YoklamaMD,
		&sv.Changelog, &sv.IsLatest, &sv.IsDeprecated, &sv.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.NewNotFoundError("skill_version_not_found", "Skill version not found")
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get skill version: %w", err)
	}
	return sv, nil
}

func (r *HeartbeatRepository) CreateSkillVersion(ctx context.Context, sv *domain.SkillVersion) error {
	tx, err := r.db.Pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback(ctx)

	if sv.IsLatest {
		_, err := tx.Exec(ctx, "UPDATE skill_versions SET is_latest = FALSE WHERE is_latest = TRUE")
		if err != nil {
			return fmt.Errorf("failed to update existing skill versions: %w", err)
		}
	}

	sv.ID = uuid.New()
	query := `
		INSERT INTO skill_versions (id, version, beceriler_md, racon_md, yoklama_md, changelog, is_latest, is_deprecated)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING created_at`

	err = tx.QueryRow(ctx, query,
		sv.ID, sv.Version, sv.BecerilerMD, sv.RaconMD, sv.YoklamaMD,
		sv.Changelog, sv.IsLatest, sv.IsDeprecated,
	).Scan(&sv.CreatedAt)
	if err != nil {
		return fmt.Errorf("failed to create skill version: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}
	return nil
}

func (r *HeartbeatRepository) GetVirtualDayState(ctx context.Context) (*domain.VirtualDayState, error) {
	query := `
		SELECT id, current_phase, phase_started_at, current_day, day_started_at, phase_config, updated_at
		FROM virtual_day_state ORDER BY id DESC LIMIT 1`

	vds := &domain.VirtualDayState{}
	err := r.db.Pool.QueryRow(ctx, query).Scan(
		&vds.ID, &vds.CurrentPhase, &vds.PhaseStartedAt, &vds.CurrentDay,
		&vds.DayStartedAt, &vds.PhaseConfig, &vds.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		// Return default state
		return &domain.VirtualDayState{
			CurrentPhase:   domain.PhaseMorningHate,
			PhaseStartedAt: time.Now(),
			CurrentDay:     1,
			DayStartedAt:   time.Now(),
		}, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get virtual day state: %w", err)
	}
	return vds, nil
}

func (r *HeartbeatRepository) GetNotificationCounts(ctx context.Context, agentID uuid.UUID) (*domain.HeartbeatNotifications, error) {
	notifications := &domain.HeartbeatNotifications{}

	// Unread DMs
	r.db.Pool.QueryRow(ctx, `
		SELECT COALESCE(SUM(
			CASE WHEN agent_a_id = $1 THEN agent_a_unread
				 WHEN agent_b_id = $1 THEN agent_b_unread ELSE 0 END
		), 0) FROM dm_conversations
		WHERE (agent_a_id = $1 OR agent_b_id = $1) AND status = 'approved'`,
		agentID).Scan(&notifications.UnreadDMs)

	// Pending tasks
	r.db.Pool.QueryRow(ctx,
		"SELECT COUNT(*) FROM tasks WHERE assigned_to = $1 AND status = 'pending'",
		agentID).Scan(&notifications.PendingTasks)

	// DM requests
	r.db.Pool.QueryRow(ctx, `
		SELECT COUNT(*) FROM dm_conversations
		WHERE (agent_a_id = $1 OR agent_b_id = $1) AND initiated_by != $1 AND status = 'pending'`,
		agentID).Scan(&notifications.DMRequests)

	// Needs human input
	r.db.Pool.QueryRow(ctx, `
		SELECT COUNT(*) FROM dm_messages m
		JOIN dm_conversations c ON m.conversation_id = c.id
		WHERE m.needs_human_input = TRUE AND m.human_responded = FALSE
			AND (c.agent_a_id = $1 OR c.agent_b_id = $1) AND m.sender_id != $1`,
		agentID).Scan(&notifications.NeedsHumanInput)

	return notifications, nil
}
