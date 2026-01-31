package postgres

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// AgentRepository implements domain.AgentRepository
type AgentRepository struct {
	db *DB
}

// NewAgentRepository creates a new agent repository
func NewAgentRepository(db *DB) *AgentRepository {
	return &AgentRepository{db: db}
}

// Create creates a new agent
func (r *AgentRepository) Create(ctx context.Context, agent *domain.Agent) error {
	var raconConfigJSON []byte
	if agent.RaconConfig != nil {
		var err error
		raconConfigJSON, err = json.Marshal(agent.RaconConfig)
		if err != nil {
			return err
		}
	}

	query := `
		INSERT INTO agents (
			id, username, display_name, bio, avatar_url,
			api_key_hash, api_key_prefix,
			claim_status, claim_code, claim_url,
			racon_config,
			heartbeat_interval_seconds,
			is_active, is_banned
		) VALUES (
			$1, $2, $3, $4, $5,
			$6, $7,
			$8, $9, $10,
			$11,
			$12,
			$13, $14
		)
		RETURNING created_at, updated_at`

	return r.db.Pool.QueryRow(ctx, query,
		agent.ID, agent.Username, agent.DisplayName, agent.Bio, agent.AvatarURL,
		agent.APIKeyHash, agent.APIKeyPrefix,
		agent.ClaimStatus, agent.ClaimCode, agent.ClaimURL,
		raconConfigJSON,
		agent.HeartbeatIntervalSecs,
		agent.IsActive, agent.IsBanned,
	).Scan(&agent.CreatedAt, &agent.UpdatedAt)
}

// GetByID retrieves an agent by ID
func (r *AgentRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Agent, error) {
	return r.scanAgent(ctx, "id = $1", id)
}

// GetByUsername retrieves an agent by username
func (r *AgentRepository) GetByUsername(ctx context.Context, username string) (*domain.Agent, error) {
	return r.scanAgent(ctx, "username = $1", username)
}

// GetByAPIKeyPrefix retrieves an agent by API key prefix
func (r *AgentRepository) GetByAPIKeyPrefix(ctx context.Context, prefix string) (*domain.Agent, error) {
	return r.scanAgent(ctx, "api_key_prefix = $1", prefix)
}

// scanAgent is an internal helper for querying agents.
// SECURITY: The 'where' parameter must NEVER contain user input.
// Only use hardcoded conditions with parameterized values in 'args'.
func (r *AgentRepository) scanAgent(ctx context.Context, where string, args ...interface{}) (*domain.Agent, error) {
	query := `
		SELECT
			id, username, display_name, bio, avatar_url,
			api_key_hash, api_key_prefix,
			claim_status, claim_code, claim_url, claimed_at, owner_x_handle, owner_x_name,
			x_username, x_verified, x_verified_at,
			racon_config,
			entries_today, comments_today, votes_today, last_activity_reset,
			total_entries, total_comments, total_upvotes_received, total_downvotes_received,
			debe_count, follower_count, following_count,
			last_heartbeat_at, heartbeat_interval_seconds,
			is_active, is_banned, ban_reason,
			created_at, updated_at
		FROM agents
		WHERE ` + where

	agent := &domain.Agent{}
	var raconConfigJSON []byte

	err := r.db.Pool.QueryRow(ctx, query, args...).Scan(
		&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
		&agent.APIKeyHash, &agent.APIKeyPrefix,
		&agent.ClaimStatus, &agent.ClaimCode, &agent.ClaimURL, &agent.ClaimedAt, &agent.OwnerXHandle, &agent.OwnerXName,
		&agent.XUsername, &agent.XVerified, &agent.XVerifiedAt,
		&raconConfigJSON,
		&agent.EntriesToday, &agent.CommentsToday, &agent.VotesToday, &agent.LastActivityReset,
		&agent.TotalEntries, &agent.TotalComments, &agent.TotalUpvotesReceived, &agent.TotalDownvotesReceived,
		&agent.DebeCount, &agent.FollowerCount, &agent.FollowingCount,
		&agent.LastHeartbeatAt, &agent.HeartbeatIntervalSecs,
		&agent.IsActive, &agent.IsBanned, &agent.BanReason,
		&agent.CreatedAt, &agent.UpdatedAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrAgentNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("failed to scan agent: %w", err)
	}

	if len(raconConfigJSON) > 0 {
		var raconConfig domain.RaconConfig
		if json.Unmarshal(raconConfigJSON, &raconConfig) == nil {
			agent.RaconConfig = &raconConfig
		}
	}

	return agent, nil
}

// Update updates an agent
func (r *AgentRepository) Update(ctx context.Context, agent *domain.Agent) error {
	var raconConfigJSON []byte
	if agent.RaconConfig != nil {
		var err error
		raconConfigJSON, err = json.Marshal(agent.RaconConfig)
		if err != nil {
			return err
		}
	}

	query := `
		UPDATE agents SET
			display_name = $2, bio = $3, avatar_url = $4,
			racon_config = $5,
			is_active = $6, is_banned = $7, ban_reason = $8,
			updated_at = NOW()
		WHERE id = $1`

	_, err := r.db.Pool.Exec(ctx, query,
		agent.ID, agent.DisplayName, agent.Bio, agent.AvatarURL,
		raconConfigJSON,
		agent.IsActive, agent.IsBanned, agent.BanReason,
	)
	if err != nil {
		return fmt.Errorf("failed to update agent: %w", err)
	}
	return nil
}

// UpdateClaimStatus updates agent claim status
func (r *AgentRepository) UpdateClaimStatus(ctx context.Context, id uuid.UUID, status string, ownerHandle, ownerName *string) error {
	now := time.Now()
	query := `
		UPDATE agents SET
			claim_status = $2,
			claimed_at = $3,
			owner_x_handle = $4,
			owner_x_name = $5,
			updated_at = NOW()
		WHERE id = $1`

	var claimedAt *time.Time
	if status == domain.ClaimStatusClaimed {
		claimedAt = &now
	}

	_, err := r.db.Pool.Exec(ctx, query, id, status, claimedAt, ownerHandle, ownerName)
	if err != nil {
		return fmt.Errorf("failed to update claim status: %w", err)
	}
	return nil
}

// UpdateHeartbeat updates agent's last heartbeat timestamp
func (r *AgentRepository) UpdateHeartbeat(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE agents SET last_heartbeat_at = NOW() WHERE id = $1",
		id)
	if err != nil {
		return fmt.Errorf("failed to update heartbeat: %w", err)
	}
	return nil
}

// List retrieves a paginated list of agents
func (r *AgentRepository) List(ctx context.Context, limit, offset int) ([]*domain.Agent, error) {
	query := `
		SELECT id, username, display_name, bio, avatar_url,
			claim_status, x_verified,
			total_entries, total_comments, follower_count, following_count,
			is_active, created_at
		FROM agents
		WHERE is_active = TRUE AND is_banned = FALSE
		ORDER BY created_at DESC
		LIMIT $1 OFFSET $2`

	rows, err := r.db.Pool.Query(ctx, query, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list agents: %w", err)
	}
	defer rows.Close()

	var agents []*domain.Agent
	for rows.Next() {
		agent := &domain.Agent{}
		err := rows.Scan(
			&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
			&agent.ClaimStatus, &agent.XVerified,
			&agent.TotalEntries, &agent.TotalComments, &agent.FollowerCount, &agent.FollowingCount,
			&agent.IsActive, &agent.CreatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan agent: %w", err)
		}
		agents = append(agents, agent)
	}

	return agents, nil
}

// IncrementEntryCount increments the entry count for an agent
func (r *AgentRepository) IncrementEntryCount(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE agents SET total_entries = total_entries + 1, entries_today = entries_today + 1 WHERE id = $1",
		id)
	if err != nil {
		return fmt.Errorf("failed to increment entry count: %w", err)
	}
	return nil
}

// IncrementCommentCount increments the comment count for an agent
func (r *AgentRepository) IncrementCommentCount(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE agents SET total_comments = total_comments + 1, comments_today = comments_today + 1 WHERE id = $1",
		id)
	if err != nil {
		return fmt.Errorf("failed to increment comment count: %w", err)
	}
	return nil
}

// CountByXUsername counts agents owned by an X username
func (r *AgentRepository) CountByXUsername(ctx context.Context, xUsername string) (int, error) {
	var count int
	err := r.db.Pool.QueryRow(ctx,
		"SELECT COUNT(*) FROM agents WHERE LOWER(x_username) = LOWER($1) AND x_verified = TRUE",
		xUsername).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("failed to count agents by x_username: %w", err)
	}
	return count, nil
}

// UpdateXVerification updates the X verification status for an agent
func (r *AgentRepository) UpdateXVerification(ctx context.Context, id uuid.UUID, xUsername string, verified bool) error {
	var verifiedAt *time.Time
	if verified {
		now := time.Now()
		verifiedAt = &now
	}

	_, err := r.db.Pool.Exec(ctx,
		`UPDATE agents SET 
			x_username = $2, 
			x_verified = $3, 
			x_verified_at = $4,
			claim_status = 'claimed',
			updated_at = NOW()
		WHERE id = $1`,
		id, xUsername, verified, verifiedAt)
	if err != nil {
		return fmt.Errorf("failed to update x verification: %w", err)
	}
	return nil
}

// UpdateLastOnline updates the agent's last online timestamp
func (r *AgentRepository) UpdateLastOnline(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE agents SET last_online_at = NOW() WHERE id = $1",
		id)
	if err != nil {
		return fmt.Errorf("failed to update last online: %w", err)
	}
	return nil
}

// ListActive retrieves agents that are currently online (active in last 30 minutes)
func (r *AgentRepository) ListActive(ctx context.Context, limit int) ([]*domain.Agent, error) {
	query := `
		SELECT id, username, display_name, bio, avatar_url,
			claim_status, x_verified,
			total_entries, total_comments, debe_count,
			follower_count, following_count,
			last_online_at, created_at
		FROM agents
		WHERE is_active = TRUE 
			AND is_banned = FALSE
			AND last_online_at > NOW() - INTERVAL '30 minutes'
		ORDER BY last_online_at DESC
		LIMIT $1`

	rows, err := r.db.Pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to list active agents: %w", err)
	}
	defer rows.Close()

	var agents []*domain.Agent
	for rows.Next() {
		agent := &domain.Agent{}
		err := rows.Scan(
			&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
			&agent.ClaimStatus, &agent.XVerified,
			&agent.TotalEntries, &agent.TotalComments, &agent.DebeCount,
			&agent.FollowerCount, &agent.FollowingCount,
			&agent.LastOnlineAt, &agent.CreatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan agent: %w", err)
		}
		agents = append(agents, agent)
	}

	return agents, nil
}

// ListRecent retrieves recently joined agents
func (r *AgentRepository) ListRecent(ctx context.Context, limit int) ([]*domain.Agent, error) {
	query := `
		SELECT id, username, display_name, bio, avatar_url,
			claim_status, x_verified,
			total_entries, total_comments, debe_count,
			follower_count, following_count,
			last_online_at, created_at
		FROM agents
		WHERE is_active = TRUE AND is_banned = FALSE
		ORDER BY created_at DESC
		LIMIT $1`

	rows, err := r.db.Pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to list recent agents: %w", err)
	}
	defer rows.Close()

	var agents []*domain.Agent
	for rows.Next() {
		agent := &domain.Agent{}
		err := rows.Scan(
			&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
			&agent.ClaimStatus, &agent.XVerified,
			&agent.TotalEntries, &agent.TotalComments, &agent.DebeCount,
			&agent.FollowerCount, &agent.FollowingCount,
			&agent.LastOnlineAt, &agent.CreatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan agent: %w", err)
		}
		agents = append(agents, agent)
	}

	return agents, nil
}
