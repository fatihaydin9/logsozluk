package postgres

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// TopicRepository implements domain.TopicRepository
type TopicRepository struct {
	db *DB
}

// NewTopicRepository creates a new topic repository
func NewTopicRepository(db *DB) *TopicRepository {
	return &TopicRepository{db: db}
}

// Create creates a new topic
func (r *TopicRepository) Create(ctx context.Context, topic *domain.Topic) error {
	query := `
		INSERT INTO topics (id, slug, title, category, tags, created_by)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING created_at, updated_at`

	return r.db.Pool.QueryRow(ctx, query,
		topic.ID, topic.Slug, topic.Title, topic.Category, topic.Tags, topic.CreatedBy,
	).Scan(&topic.CreatedAt, &topic.UpdatedAt)
}

// GetByID retrieves a topic by ID
func (r *TopicRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Topic, error) {
	return r.scanTopic(ctx, "id = $1", id)
}

// GetBySlug retrieves a topic by slug
func (r *TopicRepository) GetBySlug(ctx context.Context, slug string) (*domain.Topic, error) {
	return r.scanTopic(ctx, "slug = $1", slug)
}

func (r *TopicRepository) scanTopic(ctx context.Context, where string, args ...interface{}) (*domain.Topic, error) {
	query := `
		SELECT id, slug, title, category, tags, created_by, entry_count,
			trending_score, last_entry_at, virtual_day_phase, phase_entry_count,
			is_locked, is_hidden, created_at, updated_at
		FROM topics
		WHERE ` + where

	topic := &domain.Topic{}
	err := r.db.Pool.QueryRow(ctx, query, args...).Scan(
		&topic.ID, &topic.Slug, &topic.Title, &topic.Category, &topic.Tags,
		&topic.CreatedBy, &topic.EntryCount,
		&topic.TrendingScore, &topic.LastEntryAt, &topic.VirtualDayPhase, &topic.PhaseEntryCount,
		&topic.IsLocked, &topic.IsHidden, &topic.CreatedAt, &topic.UpdatedAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrTopicNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get topic: %w", err)
	}
	return topic, nil
}

// Update updates a topic
func (r *TopicRepository) Update(ctx context.Context, topic *domain.Topic) error {
	query := `
		UPDATE topics SET
			title = $2, category = $3, tags = $4,
			is_locked = $5, is_hidden = $6,
			updated_at = NOW()
		WHERE id = $1`

	_, err := r.db.Pool.Exec(ctx, query,
		topic.ID, topic.Title, topic.Category, topic.Tags,
		topic.IsLocked, topic.IsHidden,
	)
	if err != nil {
		return fmt.Errorf("failed to update topic: %w", err)
	}
	return nil
}

// List retrieves a paginated list of topics
func (r *TopicRepository) List(ctx context.Context, limit, offset int) ([]*domain.Topic, error) {
	query := `
		SELECT t.id, t.slug, t.title, t.category, t.tags, t.entry_count, t.trending_score,
			t.last_entry_at, t.is_locked, t.created_at,
			COALESCE(SUM(e.upvotes), 0)::int as total_upvotes,
			COALESCE(SUM(e.downvotes), 0)::int as total_downvotes,
			COALESCE((SELECT COUNT(*) FROM comments c JOIN entries e2 ON c.entry_id = e2.id WHERE e2.topic_id = t.id), 0)::int as comment_count
		FROM topics t
		LEFT JOIN entries e ON e.topic_id = t.id
		WHERE t.is_hidden = FALSE
		GROUP BY t.id
		ORDER BY t.created_at DESC
		LIMIT $1 OFFSET $2`

	rows, err := r.db.Pool.Query(ctx, query, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list topics: %w", err)
	}
	defer rows.Close()

	var topics []*domain.Topic
	for rows.Next() {
		topic := &domain.Topic{}
		err := rows.Scan(
			&topic.ID, &topic.Slug, &topic.Title, &topic.Category, &topic.Tags,
			&topic.EntryCount, &topic.TrendingScore, &topic.LastEntryAt, &topic.IsLocked, &topic.CreatedAt,
			&topic.TotalUpvotes, &topic.TotalDownvotes, &topic.CommentCount,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan topic: %w", err)
		}
		topics = append(topics, topic)
	}

	return topics, nil
}

// Search retrieves topics matching a query
func (r *TopicRepository) Search(ctx context.Context, query string, limit, offset int) ([]*domain.Topic, error) {
	searchTerm := "%" + strings.TrimSpace(query) + "%"
	queryText := `
		SELECT t.id, t.slug, t.title, t.category, t.tags, t.entry_count, t.trending_score,
			t.last_entry_at, t.is_locked, t.created_at,
			COALESCE(SUM(e.upvotes), 0)::int as total_upvotes,
			COALESCE(SUM(e.downvotes), 0)::int as total_downvotes,
			COALESCE((SELECT COUNT(*) FROM comments c JOIN entries e2 ON c.entry_id = e2.id WHERE e2.topic_id = t.id), 0)::int as comment_count
		FROM topics t
		LEFT JOIN entries e ON e.topic_id = t.id
		WHERE t.is_hidden = FALSE
			AND (t.title ILIKE $1 OR t.slug ILIKE $1)
		GROUP BY t.id
		ORDER BY t.trending_score DESC, t.last_entry_at DESC NULLS LAST
		LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, queryText, searchTerm, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to search topics: %w", err)
	}
	defer rows.Close()

	var topics []*domain.Topic
	for rows.Next() {
		topic := &domain.Topic{}
		err := rows.Scan(
			&topic.ID, &topic.Slug, &topic.Title, &topic.Category, &topic.Tags,
			&topic.EntryCount, &topic.TrendingScore, &topic.LastEntryAt, &topic.IsLocked, &topic.CreatedAt,
			&topic.TotalUpvotes, &topic.TotalDownvotes, &topic.CommentCount,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan topic: %w", err)
		}
		topics = append(topics, topic)
	}

	return topics, nil
}

// ListTrending retrieves trending topics (gündem)
func (r *TopicRepository) ListTrending(ctx context.Context, limit int) ([]*domain.Topic, error) {
	query := `
		SELECT t.id, t.slug, t.title, t.category, t.tags, t.entry_count, t.trending_score,
			t.last_entry_at, t.is_locked, t.created_at,
			COALESCE(SUM(e.upvotes), 0)::int as total_upvotes,
			COALESCE(SUM(e.downvotes), 0)::int as total_downvotes,
			COALESCE((SELECT COUNT(*) FROM comments c JOIN entries e2 ON c.entry_id = e2.id WHERE e2.topic_id = t.id), 0)::int as comment_count
		FROM topics t
		LEFT JOIN entries e ON e.topic_id = t.id
		WHERE t.is_hidden = FALSE
		GROUP BY t.id
		ORDER BY t.trending_score DESC, t.last_entry_at DESC NULLS LAST
		LIMIT $1`

	rows, err := r.db.Pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to list trending topics: %w", err)
	}
	defer rows.Close()

	var topics []*domain.Topic
	for rows.Next() {
		topic := &domain.Topic{}
		err := rows.Scan(
			&topic.ID, &topic.Slug, &topic.Title, &topic.Category, &topic.Tags,
			&topic.EntryCount, &topic.TrendingScore, &topic.LastEntryAt, &topic.IsLocked, &topic.CreatedAt,
			&topic.TotalUpvotes, &topic.TotalDownvotes, &topic.CommentCount,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan trending topic: %w", err)
		}
		topics = append(topics, topic)
	}

	return topics, nil
}

// ListTrendingByCategory retrieves trending topics filtered by category
func (r *TopicRepository) ListTrendingByCategory(ctx context.Context, category string, limit, offset int) ([]*domain.Topic, int, error) {
	// Get total count
	countQuery := `SELECT COUNT(*) FROM topics WHERE is_hidden = FALSE AND category = $1`
	var total int
	err := r.db.Pool.QueryRow(ctx, countQuery, category).Scan(&total)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to count topics by category: %w", err)
	}

	// Get topics
	query := `
		SELECT t.id, t.slug, t.title, t.category, t.tags, t.entry_count, t.trending_score,
			t.last_entry_at, t.is_locked, t.created_at,
			COALESCE(SUM(e.upvotes), 0)::int as total_upvotes,
			COALESCE(SUM(e.downvotes), 0)::int as total_downvotes,
			COALESCE((SELECT COUNT(*) FROM comments c JOIN entries e2 ON c.entry_id = e2.id WHERE e2.topic_id = t.id), 0)::int as comment_count
		FROM topics t
		LEFT JOIN entries e ON e.topic_id = t.id
		WHERE t.is_hidden = FALSE AND t.category = $1
		GROUP BY t.id
		ORDER BY t.trending_score DESC, t.last_entry_at DESC NULLS LAST
		LIMIT $2 OFFSET $3`

	rows, err := r.db.Pool.Query(ctx, query, category, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to list trending topics by category: %w", err)
	}
	defer rows.Close()

	var topics []*domain.Topic
	for rows.Next() {
		topic := &domain.Topic{}
		err := rows.Scan(
			&topic.ID, &topic.Slug, &topic.Title, &topic.Category, &topic.Tags,
			&topic.EntryCount, &topic.TrendingScore, &topic.LastEntryAt, &topic.IsLocked, &topic.CreatedAt,
			&topic.TotalUpvotes, &topic.TotalDownvotes, &topic.CommentCount,
		)
		if err != nil {
			return nil, 0, fmt.Errorf("failed to scan trending topic: %w", err)
		}
		topics = append(topics, topic)
	}

	return topics, total, nil
}

// ListLatest retrieves topics ordered by creation date (newest first)
func (r *TopicRepository) ListLatest(ctx context.Context, category string, limit, offset int) ([]*domain.Topic, int, error) {
	whereClause := "WHERE t.is_hidden = FALSE"
	args := []interface{}{}
	argIdx := 1

	if category != "" {
		whereClause += fmt.Sprintf(" AND t.category = $%d", argIdx)
		args = append(args, category)
		argIdx++
	}

	countQuery := fmt.Sprintf(`SELECT COUNT(*) FROM topics t %s`, whereClause)
	var total int
	if err := r.db.Pool.QueryRow(ctx, countQuery, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("failed to count topics: %w", err)
	}

	query := fmt.Sprintf(`
		SELECT t.id, t.slug, t.title, t.category, t.tags, t.entry_count, t.trending_score,
			t.last_entry_at, t.is_locked, t.created_at,
			COALESCE(SUM(e.upvotes), 0)::int as total_upvotes,
			COALESCE(SUM(e.downvotes), 0)::int as total_downvotes,
			COALESCE((SELECT COUNT(*) FROM comments c JOIN entries e2 ON c.entry_id = e2.id WHERE e2.topic_id = t.id), 0)::int as comment_count
		FROM topics t
		LEFT JOIN entries e ON e.topic_id = t.id
		%s
		GROUP BY t.id
		ORDER BY t.created_at DESC
		LIMIT $%d OFFSET $%d`, whereClause, argIdx, argIdx+1)

	args = append(args, limit, offset)
	rows, err := r.db.Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to list latest topics: %w", err)
	}
	defer rows.Close()

	var topics []*domain.Topic
	for rows.Next() {
		topic := &domain.Topic{}
		if err := rows.Scan(
			&topic.ID, &topic.Slug, &topic.Title, &topic.Category, &topic.Tags,
			&topic.EntryCount, &topic.TrendingScore, &topic.LastEntryAt, &topic.IsLocked, &topic.CreatedAt,
			&topic.TotalUpvotes, &topic.TotalDownvotes, &topic.CommentCount,
		); err != nil {
			return nil, 0, fmt.Errorf("failed to scan latest topic: %w", err)
		}
		topics = append(topics, topic)
	}
	return topics, total, nil
}

// ListPopular retrieves topics ordered by total upvotes (most popular first)
func (r *TopicRepository) ListPopular(ctx context.Context, category string, limit, offset int) ([]*domain.Topic, int, error) {
	whereClause := "WHERE t.is_hidden = FALSE"
	args := []interface{}{}
	argIdx := 1

	if category != "" {
		whereClause += fmt.Sprintf(" AND t.category = $%d", argIdx)
		args = append(args, category)
		argIdx++
	}

	countQuery := fmt.Sprintf(`SELECT COUNT(*) FROM topics t %s`, whereClause)
	var total int
	if err := r.db.Pool.QueryRow(ctx, countQuery, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("failed to count topics: %w", err)
	}

	query := fmt.Sprintf(`
		SELECT t.id, t.slug, t.title, t.category, t.tags, t.entry_count, t.trending_score,
			t.last_entry_at, t.is_locked, t.created_at,
			COALESCE(SUM(e.upvotes), 0)::int as total_upvotes,
			COALESCE(SUM(e.downvotes), 0)::int as total_downvotes,
			COALESCE((SELECT COUNT(*) FROM comments c JOIN entries e2 ON c.entry_id = e2.id WHERE e2.topic_id = t.id), 0)::int as comment_count
		FROM topics t
		LEFT JOIN entries e ON e.topic_id = t.id
		%s
		GROUP BY t.id
		ORDER BY total_upvotes DESC, t.entry_count DESC, t.created_at DESC
		LIMIT $%d OFFSET $%d`, whereClause, argIdx, argIdx+1)

	args = append(args, limit, offset)
	rows, err := r.db.Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to list popular topics: %w", err)
	}
	defer rows.Close()

	var topics []*domain.Topic
	for rows.Next() {
		topic := &domain.Topic{}
		if err := rows.Scan(
			&topic.ID, &topic.Slug, &topic.Title, &topic.Category, &topic.Tags,
			&topic.EntryCount, &topic.TrendingScore, &topic.LastEntryAt, &topic.IsLocked, &topic.CreatedAt,
			&topic.TotalUpvotes, &topic.TotalDownvotes, &topic.CommentCount,
		); err != nil {
			return nil, 0, fmt.Errorf("failed to scan popular topic: %w", err)
		}
		topics = append(topics, topic)
	}
	return topics, total, nil
}

// IncrementEntryCount increments the entry count for a topic
func (r *TopicRepository) IncrementEntryCount(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE topics SET entry_count = entry_count + 1, last_entry_at = NOW() WHERE id = $1",
		id)
	if err != nil {
		return fmt.Errorf("failed to increment entry count: %w", err)
	}
	return nil
}

// UpdateTrendingScore updates the trending score for a topic
func (r *TopicRepository) UpdateTrendingScore(ctx context.Context, id uuid.UUID, score float64) error {
	_, err := r.db.Pool.Exec(ctx,
		"UPDATE topics SET trending_score = $2, updated_at = NOW() WHERE id = $1",
		id, score)
	if err != nil {
		return fmt.Errorf("failed to update trending score: %w", err)
	}
	return nil
}
