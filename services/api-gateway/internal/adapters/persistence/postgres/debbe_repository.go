package postgres

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// DebbeRepository implements domain.DebbeRepository
type DebbeRepository struct {
	db *DB
}

// NewDebbeRepository creates a new debbe repository
func NewDebbeRepository(db *DB) *DebbeRepository {
	return &DebbeRepository{db: db}
}

// Create inserts a new debbe record
func (r *DebbeRepository) Create(ctx context.Context, debbe *domain.Debbe) error {
	query := `
		INSERT INTO debbe (id, debe_date, entry_id, rank, score_at_selection)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING created_at`

	return r.db.Pool.QueryRow(ctx, query,
		debbe.ID, debbe.DebeDate, debbe.EntryID, debbe.Rank, debbe.ScoreAtSelection,
	).Scan(&debbe.CreatedAt)
}

// GetByDate retrieves debbe entries for a given date
func (r *DebbeRepository) GetByDate(ctx context.Context, date string) ([]*domain.Debbe, error) {
	query := r.baseQuery() + `
		WHERE d.debe_date = $1::date
		ORDER BY d.rank ASC`

	rows, err := r.db.Pool.Query(ctx, query, date)
	if err != nil {
		return nil, fmt.Errorf("failed to list debbe by date: %w", err)
	}
	defer rows.Close()

	return r.scanDebbeRows(rows)
}

// GetLatest retrieves debbe entries for the most recent date
func (r *DebbeRepository) GetLatest(ctx context.Context) ([]*domain.Debbe, error) {
	query := r.baseQuery() + `
		WHERE d.debe_date = (SELECT MAX(debe_date) FROM debbe)
		ORDER BY d.rank ASC`

	rows, err := r.db.Pool.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to list latest debbe: %w", err)
	}
	defer rows.Close()

	return r.scanDebbeRows(rows)
}

func (r *DebbeRepository) baseQuery() string {
	return `
		SELECT d.id, d.debe_date, d.entry_id, d.rank, d.score_at_selection, d.created_at,
			e.id, e.topic_id, e.agent_id, e.content, e.content_html,
			e.upvotes, e.downvotes, e.vote_score, e.debe_score, e.debe_eligible,
			e.task_id, e.virtual_day_phase, e.is_edited, e.edited_at, e.is_hidden,
			e.created_at, e.updated_at,
			t.id, t.slug, t.title, t.category, t.tags, t.entry_count, t.trending_score,
			t.last_entry_at, t.virtual_day_phase, t.is_locked, t.created_at, t.updated_at,
			a.id, a.username, a.display_name, a.bio, a.avatar_url,
			a.total_entries, a.total_comments, a.follower_count, a.following_count,
			a.x_verified, a.created_at
		FROM debbe d
		JOIN entries e ON d.entry_id = e.id
		JOIN topics t ON e.topic_id = t.id
		JOIN agents a ON e.agent_id = a.id`
}

func (r *DebbeRepository) scanDebbeRows(rows pgx.Rows) ([]*domain.Debbe, error) {
	var debbes []*domain.Debbe
	for rows.Next() {
		debbe := &domain.Debbe{}
		entry := &domain.Entry{}
		topic := &domain.Topic{}
		agent := &domain.Agent{}

		err := rows.Scan(
			&debbe.ID, &debbe.DebeDate, &debbe.EntryID, &debbe.Rank, &debbe.ScoreAtSelection, &debbe.CreatedAt,
			&entry.ID, &entry.TopicID, &entry.AgentID, &entry.Content, &entry.ContentHTML,
			&entry.Upvotes, &entry.Downvotes, &entry.VoteScore, &entry.DebeScore, &entry.DebeEligible,
			&entry.TaskID, &entry.VirtualDayPhase, &entry.IsEdited, &entry.EditedAt, &entry.IsHidden,
			&entry.CreatedAt, &entry.UpdatedAt,
			&topic.ID, &topic.Slug, &topic.Title, &topic.Category, &topic.Tags, &topic.EntryCount, &topic.TrendingScore,
			&topic.LastEntryAt, &topic.VirtualDayPhase, &topic.IsLocked, &topic.CreatedAt, &topic.UpdatedAt,
			&agent.ID, &agent.Username, &agent.DisplayName, &agent.Bio, &agent.AvatarURL,
			&agent.TotalEntries, &agent.TotalComments, &agent.FollowerCount, &agent.FollowingCount,
			&agent.XVerified, &agent.CreatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan debbe: %w", err)
		}

		entry.Topic = topic
		entry.Agent = agent
		debbe.Entry = entry
		debbes = append(debbes, debbe)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("failed to read debbe rows: %w", err)
	}

	return debbes, nil
}
