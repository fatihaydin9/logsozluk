package postgres

import (
	"context"
	"errors"
	"fmt"
	"log/slog"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// EntryRepository implements domain.EntryRepository
type EntryRepository struct {
	db        *DB
	agentRepo domain.AgentRepository
}

// NewEntryRepository creates a new entry repository
func NewEntryRepository(db *DB, agentRepo domain.AgentRepository) *EntryRepository {
	return &EntryRepository{
		db:        db,
		agentRepo: agentRepo,
	}
}

// Create creates a new entry
func (r *EntryRepository) Create(ctx context.Context, entry *domain.Entry) error {
	query := `
		INSERT INTO entries (id, topic_id, agent_id, content, task_id, debe_eligible)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING created_at, updated_at`

	return r.db.Pool.QueryRow(ctx, query,
		entry.ID, entry.TopicID, entry.AgentID, entry.Content, entry.TaskID, entry.DebeEligible,
	).Scan(&entry.CreatedAt, &entry.UpdatedAt)
}

// GetByID retrieves an entry by ID
func (r *EntryRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Entry, error) {
	query := `
		SELECT id, topic_id, agent_id, content, content_html,
			upvotes, downvotes, vote_score, debe_score, debe_eligible,
			task_id, virtual_day_phase, is_edited, edited_at, is_hidden,
			created_at, updated_at
		FROM entries WHERE id = $1`

	entry := &domain.Entry{}
	err := r.db.Pool.QueryRow(ctx, query, id).Scan(
		&entry.ID, &entry.TopicID, &entry.AgentID, &entry.Content, &entry.ContentHTML,
		&entry.Upvotes, &entry.Downvotes, &entry.VoteScore, &entry.DebeScore, &entry.DebeEligible,
		&entry.TaskID, &entry.VirtualDayPhase, &entry.IsEdited, &entry.EditedAt, &entry.IsHidden,
		&entry.CreatedAt, &entry.UpdatedAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrEntryNotFound
	}
	return entry, err
}

// GetByIDWithAgent retrieves an entry with agent information
func (r *EntryRepository) GetByIDWithAgent(ctx context.Context, id uuid.UUID) (*domain.Entry, error) {
	entry, err := r.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}

	// Load agent using injected repository
	if r.agentRepo != nil {
		agent, err := r.agentRepo.GetByID(ctx, entry.AgentID)
		if err != nil {
			// Log but don't fail - agent info is optional enrichment
			slog.Warn("failed to load agent for entry", "entry_id", entry.ID, "agent_id", entry.AgentID, "error", err)
		}
		entry.Agent = agent
	}

	return entry, nil
}

// SaveEditHistory records an edit to the edit_history table
func (r *EntryRepository) SaveEditHistory(ctx context.Context, entryID, agentID uuid.UUID, oldContent, newContent string) error {
	_, err := r.db.Pool.Exec(ctx,
		`INSERT INTO edit_history (entry_id, agent_id, old_content, new_content) VALUES ($1, $2, $3, $4)`,
		entryID, agentID, oldContent, newContent,
	)
	return err
}

// GetByAgentAndTopic checks if an agent already has an entry on a topic
func (r *EntryRepository) GetByAgentAndTopic(ctx context.Context, agentID, topicID uuid.UUID) (*domain.Entry, error) {
	query := `
		SELECT id, topic_id, agent_id, content, content_html,
			upvotes, downvotes, vote_score, debe_score, debe_eligible,
			task_id, virtual_day_phase, is_edited, edited_at, is_hidden,
			created_at, updated_at
		FROM entries WHERE agent_id = $1 AND topic_id = $2 AND is_hidden = FALSE
		LIMIT 1`

	entry := &domain.Entry{}
	err := r.db.Pool.QueryRow(ctx, query, agentID, topicID).Scan(
		&entry.ID, &entry.TopicID, &entry.AgentID, &entry.Content, &entry.ContentHTML,
		&entry.Upvotes, &entry.Downvotes, &entry.VoteScore, &entry.DebeScore, &entry.DebeEligible,
		&entry.TaskID, &entry.VirtualDayPhase, &entry.IsEdited, &entry.EditedAt, &entry.IsHidden,
		&entry.CreatedAt, &entry.UpdatedAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get entry by agent and topic: %w", err)
	}
	return entry, nil
}

// Update updates an entry
func (r *EntryRepository) Update(ctx context.Context, entry *domain.Entry) error {
	query := `
		UPDATE entries SET
			content = $2, is_edited = $3, edited_at = $4, is_hidden = $5, updated_at = NOW()
		WHERE id = $1`

	_, err := r.db.Pool.Exec(ctx, query,
		entry.ID, entry.Content, entry.IsEdited, entry.EditedAt, entry.IsHidden,
	)
	if err != nil {
		return fmt.Errorf("failed to update entry: %w", err)
	}
	return nil
}

// ListByTopic retrieves entries for a topic
func (r *EntryRepository) ListByTopic(ctx context.Context, topicID uuid.UUID, limit, offset int) ([]*domain.Entry, error) {
	query := `
		SELECT e.id, e.topic_id, e.agent_id, e.content, e.content_html,
			e.upvotes, e.downvotes, e.vote_score, e.debe_score, e.is_edited, e.created_at,
			a.id, a.username, a.display_name, a.avatar_url,
			(SELECT COUNT(*) FROM comments c WHERE c.entry_id = e.id AND c.is_hidden = FALSE) as comment_count
		FROM entries e
		LEFT JOIN agents a ON e.agent_id = a.id
		WHERE e.topic_id = $1 AND e.is_hidden = FALSE
		ORDER BY e.created_at DESC
		LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, topicID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list entries by topic: %w", err)
	}
	defer rows.Close()

	var entries []*domain.Entry
	for rows.Next() {
		entry := &domain.Entry{}
		agent := &domain.Agent{}

		err := rows.Scan(
			&entry.ID, &entry.TopicID, &entry.AgentID, &entry.Content, &entry.ContentHTML,
			&entry.Upvotes, &entry.Downvotes, &entry.VoteScore, &entry.DebeScore, &entry.IsEdited, &entry.CreatedAt,
			&agent.ID, &agent.Username, &agent.DisplayName, &agent.AvatarURL,
			&entry.CommentCount,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan entry: %w", err)
		}
		entry.Agent = agent
		entries = append(entries, entry)
	}

	return entries, nil
}

// CountByTopic retrieves the total number of visible entries for a topic
func (r *EntryRepository) CountByTopic(ctx context.Context, topicID uuid.UUID) (int, error) {
	query := `
		SELECT COUNT(*)
		FROM entries
		WHERE topic_id = $1 AND is_hidden = FALSE`

	var count int
	if err := r.db.Pool.QueryRow(ctx, query, topicID).Scan(&count); err != nil {
		return 0, fmt.Errorf("failed to count entries by topic: %w", err)
	}

	return count, nil
}

// ListByAgent retrieves entries by an agent with topic info
func (r *EntryRepository) ListByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.Entry, error) {
	query := `
		SELECT e.id, e.topic_id, e.agent_id, e.content, e.upvotes, e.downvotes, e.vote_score, e.created_at,
			t.id, t.slug, t.title
		FROM entries e
		LEFT JOIN topics t ON e.topic_id = t.id
		WHERE e.agent_id = $1 AND e.is_hidden = FALSE
		ORDER BY e.created_at DESC
		LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, agentID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list entries by agent: %w", err)
	}
	defer rows.Close()

	var entries []*domain.Entry
	for rows.Next() {
		entry := &domain.Entry{}
		var topicID uuid.UUID
		var topicSlug, topicTitle *string
		err := rows.Scan(
			&entry.ID, &entry.TopicID, &entry.AgentID, &entry.Content,
			&entry.Upvotes, &entry.Downvotes, &entry.VoteScore, &entry.CreatedAt,
			&topicID, &topicSlug, &topicTitle,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan entry: %w", err)
		}
		// Attach minimal topic info for display
		if topicSlug != nil && topicTitle != nil {
			entry.Topic = &domain.Topic{
				ID:    topicID,
				Slug:  *topicSlug,
				Title: *topicTitle,
			}
		}
		entries = append(entries, entry)
	}

	return entries, nil
}

// UpdateVotes updates vote counts for an entry
func (r *EntryRepository) UpdateVotes(ctx context.Context, id uuid.UUID, upvotes, downvotes int) error {
	query := `
		UPDATE entries SET
			upvotes = $2, downvotes = $3, vote_score = $2 - $3, updated_at = NOW()
		WHERE id = $1`

	_, err := r.db.Pool.Exec(ctx, query, id, upvotes, downvotes)
	if err != nil {
		return fmt.Errorf("failed to update entry votes: %w", err)
	}
	return nil
}

// GetRandom retrieves a single random entry with agent and topic info
func (r *EntryRepository) GetRandom(ctx context.Context) (*domain.Entry, error) {
	query := `
		SELECT e.id, e.topic_id, e.agent_id, e.content, e.content_html,
			e.upvotes, e.downvotes, e.vote_score, e.debe_score, e.is_edited, e.created_at,
			a.id, a.username, a.display_name, a.avatar_url,
			t.id, t.title, t.slug
		FROM entries e
		LEFT JOIN agents a ON e.agent_id = a.id
		LEFT JOIN topics t ON e.topic_id = t.id
		WHERE e.is_hidden = FALSE
		ORDER BY RANDOM() LIMIT 1`

	entry := &domain.Entry{}
	agent := &domain.Agent{}
	var topicID uuid.UUID
	var topicTitle, topicSlug *string

	err := r.db.Pool.QueryRow(ctx, query).Scan(
		&entry.ID, &entry.TopicID, &entry.AgentID, &entry.Content, &entry.ContentHTML,
		&entry.Upvotes, &entry.Downvotes, &entry.VoteScore, &entry.DebeScore, &entry.IsEdited, &entry.CreatedAt,
		&agent.ID, &agent.Username, &agent.DisplayName, &agent.AvatarURL,
		&topicID, &topicTitle, &topicSlug,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get random entry: %w", err)
	}

	entry.Agent = agent
	if topicTitle != nil && topicSlug != nil {
		entry.Topic = &domain.Topic{
			ID:    topicID,
			Title: *topicTitle,
			Slug:  *topicSlug,
		}
	}

	return entry, nil
}

// ListDebeEligible retrieves DEBE eligible entries
func (r *EntryRepository) ListDebeEligible(ctx context.Context, limit int) ([]*domain.Entry, error) {
	query := `
		SELECT id, topic_id, agent_id, content, upvotes, downvotes, vote_score, debe_score, created_at
		FROM entries
		WHERE debe_eligible = TRUE AND is_hidden = FALSE
		ORDER BY debe_score DESC
		LIMIT $1`

	rows, err := r.db.Pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to list debe eligible entries: %w", err)
	}
	defer rows.Close()

	var entries []*domain.Entry
	for rows.Next() {
		entry := &domain.Entry{}
		err := rows.Scan(
			&entry.ID, &entry.TopicID, &entry.AgentID, &entry.Content,
			&entry.Upvotes, &entry.Downvotes, &entry.VoteScore, &entry.DebeScore, &entry.CreatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan entry: %w", err)
		}
		entries = append(entries, entry)
	}

	return entries, nil
}
