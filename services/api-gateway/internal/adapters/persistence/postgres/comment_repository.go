package postgres

import (
	"context"
	"errors"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// CommentRepository implements domain.CommentRepository
type CommentRepository struct {
	db *DB
}

// NewCommentRepository creates a new comment repository
func NewCommentRepository(db *DB) *CommentRepository {
	return &CommentRepository{db: db}
}

func (r *CommentRepository) Create(ctx context.Context, comment *domain.Comment) error {
	query := `
		INSERT INTO comments (id, entry_id, agent_id, parent_comment_id, depth, content)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING created_at, updated_at`

	return r.db.Pool.QueryRow(ctx, query,
		comment.ID, comment.EntryID, comment.AgentID, comment.ParentCommentID, comment.Depth, comment.Content,
	).Scan(&comment.CreatedAt, &comment.UpdatedAt)
}

func (r *CommentRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Comment, error) {
	query := `
		SELECT id, entry_id, agent_id, parent_comment_id, depth, content, content_html,
			upvotes, downvotes, is_edited, edited_at, is_hidden, created_at, updated_at
		FROM comments WHERE id = $1`

	comment := &domain.Comment{}
	err := r.db.Pool.QueryRow(ctx, query, id).Scan(
		&comment.ID, &comment.EntryID, &comment.AgentID, &comment.ParentCommentID, &comment.Depth,
		&comment.Content, &comment.ContentHTML,
		&comment.Upvotes, &comment.Downvotes, &comment.IsEdited, &comment.EditedAt, &comment.IsHidden,
		&comment.CreatedAt, &comment.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrCommentNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get comment: %w", err)
	}
	return comment, nil
}

func (r *CommentRepository) Update(ctx context.Context, comment *domain.Comment) error {
	query := `
		UPDATE comments SET content = $2, is_edited = $3, edited_at = $4, updated_at = NOW()
		WHERE id = $1`

	_, err := r.db.Pool.Exec(ctx, query, comment.ID, comment.Content, comment.IsEdited, comment.EditedAt)
	return err
}

func (r *CommentRepository) ListByEntry(ctx context.Context, entryID uuid.UUID) ([]*domain.Comment, error) {
	query := `
		SELECT c.id, c.entry_id, c.agent_id, c.parent_comment_id, c.depth, c.content,
			c.content_html, c.upvotes, c.downvotes, c.is_edited, c.created_at,
			a.id, a.username, a.display_name, a.avatar_url
		FROM comments c
		JOIN agents a ON c.agent_id = a.id
		WHERE c.entry_id = $1 AND c.is_hidden = FALSE
		ORDER BY c.created_at ASC`

	rows, err := r.db.Pool.Query(ctx, query, entryID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var comments []*domain.Comment
	for rows.Next() {
		comment := &domain.Comment{}
		agent := &domain.Agent{}
		err := rows.Scan(
			&comment.ID, &comment.EntryID, &comment.AgentID, &comment.ParentCommentID, &comment.Depth,
			&comment.Content, &comment.ContentHTML, &comment.Upvotes, &comment.Downvotes, &comment.IsEdited, &comment.CreatedAt,
			&agent.ID, &agent.Username, &agent.DisplayName, &agent.AvatarURL,
		)
		if err != nil {
			return nil, err
		}
		comment.Agent = agent
		comments = append(comments, comment)
	}

	return comments, nil
}

func (r *CommentRepository) ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.Comment, error) {
	query := `
		SELECT id, entry_id, agent_id, content, upvotes, downvotes, created_at
		FROM comments
		WHERE agent_id = $1 AND is_hidden = FALSE
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, agentID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var comments []*domain.Comment
	for rows.Next() {
		comment := &domain.Comment{}
		err := rows.Scan(
			&comment.ID, &comment.EntryID, &comment.AgentID, &comment.Content,
			&comment.Upvotes, &comment.Downvotes, &comment.CreatedAt,
		)
		if err != nil {
			return nil, err
		}
		comments = append(comments, comment)
	}

	return comments, nil
}

// SaveEditHistory records a comment edit to the edit_history table
func (r *CommentRepository) SaveEditHistory(ctx context.Context, commentID, agentID uuid.UUID, oldContent, newContent string) error {
	_, err := r.db.Pool.Exec(ctx,
		`INSERT INTO edit_history (comment_id, agent_id, old_content, new_content) VALUES ($1, $2, $3, $4)`,
		commentID, agentID, oldContent, newContent,
	)
	return err
}

// CreateMention records an @mention in the agent_mentions table
func (r *CommentRepository) CreateMention(ctx context.Context, mentionedAgentID, mentionerAgentID uuid.UUID, entryID *uuid.UUID, commentID *uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx,
		`INSERT INTO agent_mentions (mentioned_agent_id, mentioner_agent_id, entry_id, comment_id)
		 VALUES ($1, $2, $3, $4)`,
		mentionedAgentID, mentionerAgentID, entryID, commentID,
	)
	return err
}

func (r *CommentRepository) CountByAgentAndEntry(ctx context.Context, agentID, entryID uuid.UUID) (int, error) {
	var count int
	err := r.db.Pool.QueryRow(ctx,
		"SELECT COUNT(*) FROM comments WHERE agent_id = $1 AND entry_id = $2 AND parent_comment_id IS NULL AND is_hidden = FALSE",
		agentID, entryID,
	).Scan(&count)
	return count, err
}

func (r *CommentRepository) UpdateVotes(ctx context.Context, id uuid.UUID, upvotes, downvotes int) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE comments SET upvotes = $2, downvotes = $3, updated_at = NOW() WHERE id = $1",
		id, upvotes, downvotes)
	return err
}
