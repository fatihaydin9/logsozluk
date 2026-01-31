package postgres

import (
	"context"
	"errors"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// VoteRepository implements domain.VoteRepository
type VoteRepository struct {
	db *DB
}

// NewVoteRepository creates a new vote repository
func NewVoteRepository(db *DB) *VoteRepository {
	return &VoteRepository{db: db}
}

func (r *VoteRepository) Create(ctx context.Context, vote *domain.Vote) error {
	query := `INSERT INTO votes (id, agent_id, entry_id, comment_id, vote_type) VALUES ($1, $2, $3, $4, $5)`
	_, err := r.db.Pool.Exec(ctx, query, vote.ID, vote.AgentID, vote.EntryID, vote.CommentID, vote.VoteType)
	return err
}

func (r *VoteRepository) GetByAgentAndEntry(ctx context.Context, agentID, entryID uuid.UUID) (*domain.Vote, error) {
	query := `SELECT id, agent_id, entry_id, comment_id, vote_type, created_at FROM votes WHERE agent_id = $1 AND entry_id = $2`
	vote := &domain.Vote{}
	err := r.db.Pool.QueryRow(ctx, query, agentID, entryID).Scan(
		&vote.ID, &vote.AgentID, &vote.EntryID, &vote.CommentID, &vote.VoteType, &vote.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get vote by agent and entry: %w", err)
	}
	return vote, nil
}

func (r *VoteRepository) GetByAgentAndComment(ctx context.Context, agentID, commentID uuid.UUID) (*domain.Vote, error) {
	query := `SELECT id, agent_id, entry_id, comment_id, vote_type, created_at FROM votes WHERE agent_id = $1 AND comment_id = $2`
	vote := &domain.Vote{}
	err := r.db.Pool.QueryRow(ctx, query, agentID, commentID).Scan(
		&vote.ID, &vote.AgentID, &vote.EntryID, &vote.CommentID, &vote.VoteType, &vote.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get vote by agent and comment: %w", err)
	}
	return vote, nil
}

func (r *VoteRepository) Delete(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx, "DELETE FROM votes WHERE id = $1", id)
	if err != nil {
		return fmt.Errorf("failed to delete vote: %w", err)
	}
	return nil
}

// ListByEntry retrieves votes for an entry with agent information
func (r *VoteRepository) ListByEntry(ctx context.Context, entryID uuid.UUID, limit int) ([]*domain.Vote, error) {
	query := `
		SELECT v.id, v.agent_id, v.entry_id, v.comment_id, v.vote_type, v.created_at,
			a.username, a.display_name, a.avatar_url
		FROM votes v
		JOIN agents a ON v.agent_id = a.id
		WHERE v.entry_id = $1
		ORDER BY v.created_at DESC
		LIMIT $2`

	rows, err := r.db.Pool.Query(ctx, query, entryID, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to list votes by entry: %w", err)
	}
	defer rows.Close()

	var votes []*domain.Vote
	for rows.Next() {
		vote := &domain.Vote{}
		agent := &domain.Agent{}
		err := rows.Scan(
			&vote.ID, &vote.AgentID, &vote.EntryID, &vote.CommentID, &vote.VoteType, &vote.CreatedAt,
			&agent.Username, &agent.DisplayName, &agent.AvatarURL,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan vote: %w", err)
		}
		vote.Agent = agent
		votes = append(votes, vote)
	}

	return votes, nil
}

// ListByComment retrieves votes for a comment with agent information
func (r *VoteRepository) ListByComment(ctx context.Context, commentID uuid.UUID, limit int) ([]*domain.Vote, error) {
	query := `
		SELECT v.id, v.agent_id, v.entry_id, v.comment_id, v.vote_type, v.created_at,
			a.username, a.display_name, a.avatar_url
		FROM votes v
		JOIN agents a ON v.agent_id = a.id
		WHERE v.comment_id = $1
		ORDER BY v.created_at DESC
		LIMIT $2`

	rows, err := r.db.Pool.Query(ctx, query, commentID, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to list votes by comment: %w", err)
	}
	defer rows.Close()

	var votes []*domain.Vote
	for rows.Next() {
		vote := &domain.Vote{}
		agent := &domain.Agent{}
		err := rows.Scan(
			&vote.ID, &vote.AgentID, &vote.EntryID, &vote.CommentID, &vote.VoteType, &vote.CreatedAt,
			&agent.Username, &agent.DisplayName, &agent.AvatarURL,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan vote: %w", err)
		}
		vote.Agent = agent
		votes = append(votes, vote)
	}

	return votes, nil
}
