package postgres

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// CommunityPostRepository implements domain.CommunityPostRepository
type CommunityPostRepository struct {
	db *DB
}

// NewCommunityPostRepository creates a new community post repository
func NewCommunityPostRepository(db *DB) *CommunityPostRepository {
	return &CommunityPostRepository{db: db}
}

// Create creates a new community post
func (r *CommunityPostRepository) Create(ctx context.Context, p *domain.CommunityPost) error {
	pollOptionsJSON, _ := json.Marshal(p.PollOptions)
	pollVotesJSON, _ := json.Marshal(p.PollVotes)

	query := `
		INSERT INTO community_posts (id, agent_id, post_type, title, content, safe_html, 
			poll_options, poll_votes, emoji, tags, plus_one_count)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
	`
	_, err := r.db.Pool.Exec(ctx, query,
		p.ID, p.AgentID, p.PostType, p.Title, p.Content, p.SafeHTML,
		pollOptionsJSON, pollVotesJSON, p.Emoji, p.Tags, p.PlusOneCount,
	)
	if err != nil {
		return fmt.Errorf("failed to create community post: %w", err)
	}
	return nil
}

// GetByID retrieves a community post by ID
func (r *CommunityPostRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.CommunityPost, error) {
	query := `
		SELECT p.id, p.agent_id, p.post_type, p.title, p.content, p.safe_html,
			p.poll_options, p.poll_votes, p.emoji, p.tags, p.plus_one_count,
			p.created_at, p.updated_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url
		FROM community_posts p
		LEFT JOIN agents a ON p.agent_id = a.id
		WHERE p.id = $1
	`
	row := r.db.Pool.QueryRow(ctx, query, id)
	return r.scanPost(row)
}

// List lists community posts with optional type filter
func (r *CommunityPostRepository) List(ctx context.Context, postType string, limit, offset int) ([]*domain.CommunityPost, error) {
	var query string
	var args []interface{}

	if postType != "" {
		query = `
			SELECT p.id, p.agent_id, p.post_type, p.title, p.content, p.safe_html,
				p.poll_options, p.poll_votes, p.emoji, p.tags, p.plus_one_count,
				p.created_at, p.updated_at,
				a.id, a.username, a.display_name, a.bio, a.avatar_url
			FROM community_posts p
			LEFT JOIN agents a ON p.agent_id = a.id
			WHERE p.post_type = $1
			ORDER BY p.created_at DESC
			LIMIT $2 OFFSET $3
		`
		args = []interface{}{postType, limit, offset}
	} else {
		query = `
			SELECT p.id, p.agent_id, p.post_type, p.title, p.content, p.safe_html,
				p.poll_options, p.poll_votes, p.emoji, p.tags, p.plus_one_count,
				p.created_at, p.updated_at,
				a.id, a.username, a.display_name, a.bio, a.avatar_url
			FROM community_posts p
			LEFT JOIN agents a ON p.agent_id = a.id
			ORDER BY p.created_at DESC
			LIMIT $1 OFFSET $2
		`
		args = []interface{}{limit, offset}
	}

	rows, err := r.db.Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to list community posts: %w", err)
	}
	defer rows.Close()

	var posts []*domain.CommunityPost
	for rows.Next() {
		p, err := r.scanPostFromRows(rows)
		if err != nil {
			return nil, err
		}
		posts = append(posts, p)
	}
	return posts, nil
}

// PlusOne adds a +1 vote to a community post
func (r *CommunityPostRepository) PlusOne(ctx context.Context, postID, agentID uuid.UUID) error {
	tx, err := r.db.Pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("failed to begin tx: %w", err)
	}
	defer tx.Rollback(ctx)

	// Insert vote (unique constraint prevents duplicates)
	_, err = tx.Exec(ctx,
		`INSERT INTO community_post_votes (post_id, agent_id) VALUES ($1, $2)`,
		postID, agentID,
	)
	if err != nil {
		return fmt.Errorf("already voted or error: %w", err)
	}

	// Increment counter
	_, err = tx.Exec(ctx,
		`UPDATE community_posts SET plus_one_count = plus_one_count + 1 WHERE id = $1`,
		postID,
	)
	if err != nil {
		return fmt.Errorf("failed to increment: %w", err)
	}

	return tx.Commit(ctx)
}

// HasVoted checks if an agent has +1'd a post
func (r *CommunityPostRepository) HasVoted(ctx context.Context, postID, agentID uuid.UUID) (bool, error) {
	var exists bool
	err := r.db.Pool.QueryRow(ctx,
		`SELECT EXISTS(SELECT 1 FROM community_post_votes WHERE post_id = $1 AND agent_id = $2)`,
		postID, agentID,
	).Scan(&exists)
	return exists, err
}

// VotePoll votes on a poll option
func (r *CommunityPostRepository) VotePoll(ctx context.Context, postID, agentID uuid.UUID, optionIndex int) error {
	tx, err := r.db.Pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("failed to begin tx: %w", err)
	}
	defer tx.Rollback(ctx)

	// Insert poll vote (unique constraint prevents duplicates)
	_, err = tx.Exec(ctx,
		`INSERT INTO community_poll_votes (post_id, agent_id, option_index) VALUES ($1, $2, $3)`,
		postID, agentID, optionIndex,
	)
	if err != nil {
		return fmt.Errorf("already voted or error: %w", err)
	}

	// Get the option name to increment in JSONB
	var pollOptions []byte
	err = tx.QueryRow(ctx,
		`SELECT poll_options FROM community_posts WHERE id = $1`,
		postID,
	).Scan(&pollOptions)
	if err != nil {
		return fmt.Errorf("failed to get poll options: %w", err)
	}

	var options []string
	if err := json.Unmarshal(pollOptions, &options); err != nil {
		return fmt.Errorf("failed to parse poll options: %w", err)
	}

	if optionIndex < 0 || optionIndex >= len(options) {
		return fmt.Errorf("invalid option index")
	}

	optionKey := options[optionIndex]
	_, err = tx.Exec(ctx,
		`UPDATE community_posts SET poll_votes = jsonb_set(
			COALESCE(poll_votes, '{}'::jsonb),
			$2,
			(COALESCE((poll_votes->>$3)::int, 0) + 1)::text::jsonb
		) WHERE id = $1`,
		postID, fmt.Sprintf("{%s}", optionKey), optionKey,
	)
	if err != nil {
		return fmt.Errorf("failed to update poll votes: %w", err)
	}

	return tx.Commit(ctx)
}

// scanPost scans a single community post from a QueryRow result
func (r *CommunityPostRepository) scanPost(row pgx.Row) (*domain.CommunityPost, error) {
	var p domain.CommunityPost
	var agent domain.Agent
	var pollOptionsJSON, pollVotesJSON []byte

	err := row.Scan(
		&p.ID, &p.AgentID, &p.PostType, &p.Title, &p.Content, &p.SafeHTML,
		&pollOptionsJSON, &pollVotesJSON, &p.Emoji, &p.Tags, &p.PlusOneCount,
		&p.CreatedAt, &p.UpdatedAt,
		&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to scan community post: %w", err)
	}

	if pollOptionsJSON != nil {
		json.Unmarshal(pollOptionsJSON, &p.PollOptions)
	}
	if pollVotesJSON != nil {
		json.Unmarshal(pollVotesJSON, &p.PollVotes)
	}

	p.Agent = &agent
	return &p, nil
}

// scanPostFromRows scans a community post from a Rows result
func (r *CommunityPostRepository) scanPostFromRows(rows pgx.Rows) (*domain.CommunityPost, error) {
	var p domain.CommunityPost
	var agent domain.Agent
	var pollOptionsJSON, pollVotesJSON []byte

	err := rows.Scan(
		&p.ID, &p.AgentID, &p.PostType, &p.Title, &p.Content, &p.SafeHTML,
		&pollOptionsJSON, &pollVotesJSON, &p.Emoji, &p.Tags, &p.PlusOneCount,
		&p.CreatedAt, &p.UpdatedAt,
		&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to scan community post: %w", err)
	}

	if pollOptionsJSON != nil {
		json.Unmarshal(pollOptionsJSON, &p.PollOptions)
	}
	if pollVotesJSON != nil {
		json.Unmarshal(pollVotesJSON, &p.PollVotes)
	}

	p.Agent = &agent
	return &p, nil
}
