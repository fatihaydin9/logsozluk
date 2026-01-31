package postgres

import (
	"context"
	"errors"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// FollowRepository implements domain.FollowRepository
type FollowRepository struct {
	db *DB
}

func NewFollowRepository(db *DB) *FollowRepository {
	return &FollowRepository{db: db}
}

func (r *FollowRepository) Create(ctx context.Context, follow *domain.AgentFollow) error {
	query := `INSERT INTO agent_follows (id, follower_id, following_id) VALUES ($1, $2, $3) RETURNING created_at`
	err := r.db.Pool.QueryRow(ctx, query, follow.ID, follow.FollowerID, follow.FollowingID).Scan(&follow.CreatedAt)
	if err != nil {
		return fmt.Errorf("failed to create follow: %w", err)
	}

	// Update counts
	r.db.Pool.Exec(ctx, "UPDATE agents SET following_count = following_count + 1 WHERE id = $1", follow.FollowerID)
	r.db.Pool.Exec(ctx, "UPDATE agents SET follower_count = follower_count + 1 WHERE id = $1", follow.FollowingID)

	return nil
}

func (r *FollowRepository) Delete(ctx context.Context, followerID, followingID uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx, "DELETE FROM agent_follows WHERE follower_id = $1 AND following_id = $2", followerID, followingID)
	if err != nil {
		return fmt.Errorf("failed to delete follow: %w", err)
	}

	// Update counts
	r.db.Pool.Exec(ctx, "UPDATE agents SET following_count = following_count - 1 WHERE id = $1 AND following_count > 0", followerID)
	r.db.Pool.Exec(ctx, "UPDATE agents SET follower_count = follower_count - 1 WHERE id = $1 AND follower_count > 0", followingID)

	return nil
}

func (r *FollowRepository) GetByIDs(ctx context.Context, followerID, followingID uuid.UUID) (*domain.AgentFollow, error) {
	follow := &domain.AgentFollow{}
	err := r.db.Pool.QueryRow(ctx,
		"SELECT id, follower_id, following_id, created_at FROM agent_follows WHERE follower_id = $1 AND following_id = $2",
		followerID, followingID,
	).Scan(&follow.ID, &follow.FollowerID, &follow.FollowingID, &follow.CreatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get follow: %w", err)
	}
	return follow, nil
}

func (r *FollowRepository) ListFollowers(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.AgentFollow, error) {
	query := `
		SELECT f.id, f.follower_id, f.following_id, f.created_at,
			a.id, a.username, a.display_name, a.avatar_url
		FROM agent_follows f
		JOIN agents a ON f.follower_id = a.id
		WHERE f.following_id = $1
		ORDER BY f.created_at DESC LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, agentID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list followers: %w", err)
	}
	defer rows.Close()

	var follows []*domain.AgentFollow
	for rows.Next() {
		f := &domain.AgentFollow{}
		a := &domain.Agent{}
		err := rows.Scan(&f.ID, &f.FollowerID, &f.FollowingID, &f.CreatedAt, &a.ID, &a.Username, &a.DisplayName, &a.AvatarURL)
		if err != nil {
			return nil, fmt.Errorf("failed to scan follower: %w", err)
		}
		f.Follower = a
		follows = append(follows, f)
	}
	return follows, nil
}

func (r *FollowRepository) ListFollowing(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.AgentFollow, error) {
	query := `
		SELECT f.id, f.follower_id, f.following_id, f.created_at,
			a.id, a.username, a.display_name, a.avatar_url
		FROM agent_follows f
		JOIN agents a ON f.following_id = a.id
		WHERE f.follower_id = $1
		ORDER BY f.created_at DESC LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, agentID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list following: %w", err)
	}
	defer rows.Close()

	var follows []*domain.AgentFollow
	for rows.Next() {
		f := &domain.AgentFollow{}
		a := &domain.Agent{}
		err := rows.Scan(&f.ID, &f.FollowerID, &f.FollowingID, &f.CreatedAt, &a.ID, &a.Username, &a.DisplayName, &a.AvatarURL)
		if err != nil {
			return nil, fmt.Errorf("failed to scan following: %w", err)
		}
		f.Following = a
		follows = append(follows, f)
	}
	return follows, nil
}

func (r *FollowRepository) IsFollowing(ctx context.Context, followerID, followingID uuid.UUID) (bool, error) {
	var count int
	err := r.db.Pool.QueryRow(ctx,
		"SELECT COUNT(*) FROM agent_follows WHERE follower_id = $1 AND following_id = $2",
		followerID, followingID,
	).Scan(&count)
	if err != nil {
		return false, fmt.Errorf("failed to check following status: %w", err)
	}
	return count > 0, nil
}
